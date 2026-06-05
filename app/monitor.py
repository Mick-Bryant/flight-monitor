import logging
import re
import requests
import statistics
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from config import Config
from app.nearby import get_nearby_airports, get_sample_dates

log = logging.getLogger(__name__)

HISTORIC_LOOKBACK   = 180
HISTORIC_PERCENTILE = 0.20
MAX_OFFERS          = 20


def parse_duration_minutes(iso_duration):
    """Parse ISO-8601 duration string (e.g. 'PT13H40M') to total minutes."""
    if not iso_duration:
        return None
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", iso_duration)
    if not m:
        return None
    hours   = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    return hours * 60 + minutes


def get_app_config_float(key, default):
    """Read a float value from the app_config admin table."""
    try:
        from app.models import AppConfig
        row = AppConfig.query.filter_by(key=key).first()
        if row:
            return float(row.value)
    except Exception:
        pass
    return default


def pick_best_offer(offers, mode, time_val_aud, stop_pen_aud, offer_currency="AUD"):
    """
    Select the single best offer from a list based on optimize mode.

    'cheapest'  — lowest price (offers assumed pre-sorted; returns offers[0])
    'fastest'   — lowest total duration_minutes
    'best_value'— lowest effective cost (price + time value + stop penalty),
                  with AUD coefficients converted to offer_currency

    Returns the selected offer dict. Falls back to offers[0] if selection fails.
    """
    if not offers:
        return None

    if mode == "fastest":
        valid = [o for o in offers if o.get("duration_minutes") is not None]
        if valid:
            return min(valid, key=lambda o: o["duration_minutes"])
        return offers[0]

    if mode == "best_value":
        from app.currency import convert
        time_val = convert(time_val_aud, "AUD", offer_currency)
        stop_pen = convert(stop_pen_aud, "AUD", offer_currency)

        def effective_cost(o):
            dur_hours = (o.get("duration_minutes") or 0) / 60
            stops     = o.get("stops") or 0
            return o["price"] + time_val * dur_hours + stop_pen * stops

        return min(offers, key=effective_cost)

    return offers[0]  # 'cheapest' — list is already price-sorted


def get_historic_data_for_mode(global_route_id, mode, time_val_aud, stop_pen_aud,
                                PriceHistory, MarketSummary, created_at):
    """
    Return (historic_low, historic_median, has_data, days_data) for a route,
    selecting the best offer per historical check based on mode.

    'cheapest' delegates to get_historic_data (reads MarketSummary aggregates).
    'fastest' / 'best_value' reconstruct the series from raw PriceHistory rows,
    picking the mode-optimal offer at each check. Checks where no offer has
    duration data are skipped for 'fastest' mode to avoid poisoning the series
    with pre-migration rows.
    """
    if mode == "cheapest":
        return get_historic_data(global_route_id, MarketSummary, created_at)

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    days_since_created = (datetime.now(timezone.utc) - created_at).days
    lookback_days      = min(days_since_created, HISTORIC_LOOKBACK)
    cutoff             = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    records = (PriceHistory.query
               .filter(
                   PriceHistory.global_route_id == global_route_id,
                   PriceHistory.checked_at      >= cutoff,
               )
               .order_by(PriceHistory.checked_at.asc())
               .all())

    if not records:
        return None, None, False, 0

    offer_currency = records[0].currency

    # Group by exact checked_at — all offers in one Duffel call share the same timestamp
    checks = defaultdict(list)
    for r in records:
        checks[r.checked_at].append(r)

    best_prices = []
    for ts in sorted(checks.keys()):
        check_offers = [
            {
                "price":            r.price,
                "stops":            r.stops,
                "duration_minutes": r.duration_minutes,
            }
            for r in checks[ts]
        ]
        # Skip pre-migration checks for fastest mode (no duration data = unreliable)
        if mode == "fastest":
            if not any(o["duration_minutes"] is not None for o in check_offers):
                continue
        best = pick_best_offer(check_offers, mode, time_val_aud, stop_pen_aud,
                               offer_currency)
        if best:
            best_prices.append(best["price"])

    if len(best_prices) < 2:
        return None, None, False, 0

    sorted_prices   = sorted(best_prices)
    cutoff_idx      = max(1, int(len(sorted_prices) * HISTORIC_PERCENTILE))
    historic_low    = statistics.mean(sorted_prices[:cutoff_idx])
    historic_median = statistics.median(best_prices)

    oldest_ts = min(checks.keys())
    if oldest_ts.tzinfo is None:
        oldest_ts = oldest_ts.replace(tzinfo=timezone.utc)
    days_data = (datetime.now(timezone.utc) - oldest_ts).days

    return historic_low, historic_median, True, days_data


def get_duffel_headers():
    return {
        "Authorization": f"Bearer {Config.DUFFEL_ACCESS_TOKEN}",
        "Duffel-Version": Config.DUFFEL_API_VERSION,
        "Content-Type":   "application/json",
        "Accept":         "application/json",
    }


def fetch_all_offers(origin, destination, departure_date,
                     return_date, adults, cabin_class):
    """Fetch all offers from Duffel for a route."""
    slices = [{
        "origin":         origin,
        "destination":    destination,
        "departure_date": departure_date,
    }]
    if return_date:
        slices.append({
            "origin":         destination,
            "destination":    origin,
            "departure_date": return_date,
        })

    payload = {
        "data": {
            "slices":      slices,
            "passengers":  [{"type": "adult"} for _ in range(adults)],
            "cabin_class": cabin_class,
        }
    }

    try:
        response = requests.post(
            f"{Config.DUFFEL_API_URL}/air/offer_requests"
            f"?return_offers=true&max_connections=2",
            headers=get_duffel_headers(),
            json=payload,
            timeout=15,
        )

        if response.status_code == 429:
            log.warning("Rate limited for %s->%s — retrying after 5s",
                        origin, destination)
            time.sleep(5)
            try:
                response = requests.post(
                    f"{Config.DUFFEL_API_URL}/air/offer_requests"
                    f"?return_offers=true&max_connections=2",
                    headers=get_duffel_headers(),
                    json=payload,
                    timeout=15,
                )
            except Exception:
                return None

        if response.status_code != 201:
            log.error("Duffel error %s for %s->%s: %s",
                      response.status_code, origin, destination,
                      response.text[:200])
            return None

        data   = response.json()
        offers = data.get("data", {}).get("offers", [])

        if not offers:
            return None

        offers = sorted(
            offers, key=lambda o: float(o["total_amount"])
        )[:MAX_OFFERS]

        results = []
        for i, offer in enumerate(offers):
            try:
                airline = (offer["slices"][0]["segments"][0]
                           ["operating_carrier"]["name"])
            except (KeyError, IndexError):
                airline = None
            try:
                stops = sum(
                    len(s["segments"]) - 1
                    for s in offer["slices"]
                )
            except (KeyError, IndexError):
                stops = None
            try:
                duration_minutes = sum(
                    parse_duration_minutes(s.get("duration", "")) or 0
                    for s in offer["slices"]
                ) or None
            except (KeyError, TypeError):
                duration_minutes = None

            results.append({
                "price":            float(offer["total_amount"]),
                "currency":         offer["total_currency"],
                "airline":          airline,
                "stops":            stops,
                "duration_minutes": duration_minutes,
                "is_cheapest":      i == 0,
            })

        time.sleep(0.5)
        return results

    except requests.exceptions.Timeout:
        log.error("Timeout for %s->%s", origin, destination)
        return None
    except Exception as e:
        log.error("Error for %s->%s: %s", origin, destination, e)
        return None


def calculate_market_metrics(offers):
    prices = [o["price"] for o in offers]
    return {
        "market_min":       min(prices),
        "market_median":    statistics.median(prices),
        "market_mean":      statistics.mean(prices),
        "offer_count":      len(prices),
        "cheapest_airline": offers[0]["airline"],
        "currency":         offers[0]["currency"],
    }


def get_historic_data(global_route_id, MarketSummary, created_at):
    """
    Get historic low and median for a global route.
    Uses shared market_summary data — benefits all users
    watching the same route.
    Returns (historic_low, historic_median, has_data, days_of_data)
    """
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    days_since_created = (datetime.now(timezone.utc) - created_at).days
    lookback_days      = min(days_since_created, HISTORIC_LOOKBACK)
    cutoff             = (datetime.now(timezone.utc)
                          - timedelta(days=lookback_days))

    records = MarketSummary.query.filter(
        MarketSummary.global_route_id == global_route_id,
        MarketSummary.checked_at      >= cutoff,
    ).order_by(MarketSummary.checked_at.asc()).all()

    if not records:
        return None, None, False, 0

    mins    = [r.market_min    for r in records]
    medians = [r.market_median for r in records]

    sorted_mins = sorted(mins)
    cutoff_idx  = max(1, int(len(sorted_mins) * HISTORIC_PERCENTILE))
    historic_low    = statistics.mean(sorted_mins[:cutoff_idx])
    historic_median = statistics.mean(medians)

    oldest = records[0].checked_at
    if oldest.tzinfo is None:
        oldest = oldest.replace(tzinfo=timezone.utc)
    days_data = (datetime.now(timezone.utc) - oldest).days

    return historic_low, historic_median, True, days_data


def check_all_routes(app):
    with app.app_context():
        from app.models import (db, GlobalRoute, UserRoute, AlertLog,
                                PriceHistory, MarketSummary)
        from app.email import (send_sudden_sale_alert,
                               send_historic_low_alert)

        log.info("=== Price check started %s UTC ===",
                 datetime.now(timezone.utc).isoformat())

        # Get all active global routes that have active user routes
        global_routes = GlobalRoute.query.filter_by(
            is_active=True
        ).all()

        # Filter to only those with at least one active user route
        active_global = [
            gr for gr in global_routes
            if any(ur.is_active for ur in gr.user_routes)
        ]

        log.info("Checking %d active global route(s)", len(active_global))

        # Fetch admin effective-cost coefficients once per cycle
        time_val_aud = get_app_config_float("time_value_aud_per_hour", 12.0)
        stop_pen_aud = get_app_config_float("stop_penalty_aud", 40.0)

        for gr in active_global:
            log.info("Checking global route %s->%s %s",
                     gr.origin, gr.destination, gr.departure_date)

            # Single Duffel API call for all users watching this route
            offers = fetch_all_offers(
                origin         = gr.origin,
                destination    = gr.destination,
                departure_date = gr.departure_date,
                return_date    = gr.return_date,
                adults         = gr.adults,
                cabin_class    = gr.cabin_class,
            )

            if not offers:
                continue

            metrics  = calculate_market_metrics(offers)
            now      = datetime.now(timezone.utc)
            currency = metrics["currency"]

            # Store market data once — shared by all users
            for offer in offers:
                db.session.add(PriceHistory(
                    global_route_id  = gr.id,
                    price            = offer["price"],
                    currency         = offer["currency"],
                    airline          = offer["airline"],
                    stops            = offer["stops"],
                    duration_minutes = offer["duration_minutes"],
                    is_cheapest      = offer["is_cheapest"],
                    checked_date     = gr.departure_date,
                    checked_at       = now,
                ))

            db.session.add(MarketSummary(
                global_route_id  = gr.id,
                checked_at       = now,
                checked_date     = gr.departure_date,
                market_min       = metrics["market_min"],
                market_median    = metrics["market_median"],
                market_mean      = metrics["market_mean"],
                offer_count      = metrics["offer_count"],
                cheapest_airline = metrics["cheapest_airline"],
                currency         = currency,
            ))

            gr.last_checked = now

            # Now check each user watching this global route
            active_user_routes = [
                ur for ur in gr.user_routes if ur.is_active
            ]

            # Cache historic data per mode — avoids re-querying for users
            # watching the same route with the same optimize_for setting
            mode_historic_cache = {}

            for ur in active_user_routes:
                user = ur.user

                # Skip expired trials
                if not user.trial_active():
                    log.info("Skipping user_route %d — trial expired for %s",
                             ur.id, user.email)
                    continue

                # Skip if not enough time since last check for this tier
                if gr.last_checked:
                    last = gr.last_checked
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone.utc)
                    interval = user.tier_config()["check_interval"]
                    elapsed  = (now - last).seconds // 60
                    if elapsed < interval and elapsed > 0:
                        log.debug(
                            "Skipping %s %s->%s — checked %d min ago",
                            user.email, gr.origin, gr.destination, elapsed
                        )
                        continue

                # Resolve this user's optimize mode and select the best offer
                mode       = ur.effective_optimize_for()
                best_offer = pick_best_offer(
                    offers, mode, time_val_aud, stop_pen_aud, currency
                )
                current_price   = best_offer["price"]
                current_airline = best_offer["airline"]

                # Set baseline on first check for this user route
                if ur.baseline_price is None:
                    ur.baseline_price = current_price
                    log.info(
                        "Baseline set for %s %s->%s [%s]: %s %.2f",
                        user.email, gr.origin, gr.destination,
                        mode, currency, current_price
                    )
                    continue

                drop = ur.baseline_price - current_price

                log.info(
                    "%s %s->%s [%s] | baseline %.2f | best %.2f | "
                    "median %.2f | drop %.2f",
                    user.email, gr.origin, gr.destination, mode,
                    ur.baseline_price, current_price,
                    metrics["market_median"], drop
                )

                # Get historic data for this mode (cached per mode per route)
                if mode not in mode_historic_cache:
                    mode_historic_cache[mode] = get_historic_data_for_mode(
                        gr.id, mode, time_val_aud, stop_pen_aud,
                        PriceHistory, MarketSummary, gr.created_at,
                    )
                historic_low, historic_median, has_data, days_data = \
                    mode_historic_cache[mode]

                alert_sent = False
                alert_type = None

                # Trigger 1 — Historic low
                if has_data and historic_low and current_price < historic_low:
                    log.info(
                        "HISTORIC LOW %s->%s for %s [%s]: %.2f < %.2f",
                        gr.origin, gr.destination, user.email,
                        mode, current_price, historic_low,
                    )
                    alert_sent = send_historic_low_alert(
                        user            = user,
                        route           = gr,
                        baseline_price  = ur.baseline_price,
                        current_price   = current_price,
                        drop            = drop,
                        currency        = currency,
                        airline         = current_airline,
                        historic_avg    = historic_low,
                        historic_median = historic_median,
                        top_offers      = offers[:5],
                    )
                    alert_type = "historic_low"

                # Trigger 2 — Flash sale vs median
                # Only fire if price dropped from baseline (not rose)
                elif (has_data and historic_median and
                      historic_median - current_price >= ur.threshold_usd and
                      drop > 0):
                    log.info(
                        "FLASH SALE %s->%s for %s [%s]: %.2f below median %.2f",
                        gr.origin, gr.destination, user.email,
                        mode, current_price, historic_median,
                    )
                    alert_sent = send_sudden_sale_alert(
                        user            = user,
                        route           = gr,
                        baseline_price  = ur.baseline_price,
                        current_price   = current_price,
                        drop            = drop,
                        currency        = currency,
                        airline         = current_airline,
                        historic_median = historic_median,
                        top_offers      = offers[:5],
                    )
                    alert_type = "sudden_sale"

                # Fallback — no historic data yet, price must have dropped
                elif not has_data and drop >= ur.threshold_usd and drop > 0:
                    alert_sent = send_sudden_sale_alert(
                        user            = user,
                        route           = gr,
                        baseline_price  = ur.baseline_price,
                        current_price   = current_price,
                        drop            = drop,
                        currency        = currency,
                        airline         = current_airline,
                        historic_median = None,
                        top_offers      = offers[:5],
                    )
                    alert_type = "sudden_sale"

                if alert_sent and alert_type:
                    db.session.add(AlertLog(
                        user_route_id  = ur.id,
                        baseline_price = ur.baseline_price,
                        alerted_price  = current_price,
                        drop_amount    = drop,
                        currency       = currency,
                        airline        = current_airline,
                        alert_type     = alert_type,
                        historic_avg   = historic_low,
                    ))
                    ur.baseline_price = current_price
                elif current_price > ur.baseline_price:
                    ur.baseline_price = current_price

            db.session.commit()

            # --- Nearby airport checks (per user route, Option B) ---
            for ur in active_user_routes:
                if not ur.nearby_airports:
                    continue
                user   = ur.user
                nearby = get_nearby_airports(gr.origin)
                if not nearby:
                    continue

                log.info("Nearby check for %s %s->%s: %s",
                         user.email, gr.origin, gr.destination,
                         [a.iata_code for a in nearby])

                for nearby_airport in nearby:
                    nearby_offers = fetch_all_offers(
                        origin         = nearby_airport.iata_code,
                        destination    = gr.destination,
                        departure_date = gr.departure_date,
                        return_date    = gr.return_date,
                        adults         = gr.adults,
                        cabin_class    = gr.cabin_class,
                    )
                    if not nearby_offers:
                        continue

                    nearby_min    = nearby_offers[0]["price"]
                    nearby_airline = nearby_offers[0]["airline"]
                    current_min   = metrics["market_min"]
                    saving        = current_min - nearby_min

                    log.info("Nearby %s->%s: %.2f (saving %.2f)",
                             nearby_airport.iata_code, gr.destination,
                             nearby_min, saving)

                    if saving >= ur.nearby_min_saving:
                        from app.email import send_nearby_alert
                        send_nearby_alert(
                            user            = user,
                            route           = gr,
                            nearby_iata     = nearby_airport.iata_code,
                            nearby_city     = nearby_airport.city,
                            nearby_price    = nearby_min,
                            nearby_airline  = nearby_airline,
                            entered_price   = current_min,
                            entered_airline = metrics["cheapest_airline"],
                            saving          = saving,
                            currency        = currency,
                            top_offers      = nearby_offers[:5],
                        )

            # --- Flexible date checks (per user route, Option B) ---
            for ur in active_user_routes:
                if not ur.flexible_dates:
                    continue
                user = ur.user
                import datetime as dt_module

                dep_date      = dt_module.date.fromisoformat(gr.departure_date)
                flex_days_val = ur.flex_days()
                dep_samples   = get_sample_dates(
                    dep_date, flex_days_val, is_nearby=False
                )
                # Remove the base date — already checked above
                dep_samples = [
                    d for d in dep_samples
                    if d.isoformat() != gr.departure_date
                ]

                if ur.flex_duration and gr.return_date:
                    base_return   = dt_module.date.fromisoformat(gr.return_date)
                    base_duration = (base_return - dep_date).days
                    dur_variance  = ur.flex_duration_days or 7
                    dur_samples   = [
                        max(1, base_duration - dur_variance),
                        base_duration + dur_variance,
                    ]
                else:
                    dur_samples = [None]

                best_offers = None
                best_dep    = gr.departure_date

                for dep_sample in dep_samples:
                    for dur in dur_samples:
                        ret_sample = None
                        if gr.return_date and dur:
                            ret_dt     = dep_sample + dt_module.timedelta(
                                days=dur
                            )
                            ret_sample = ret_dt.isoformat()

                        sample_offers = fetch_all_offers(
                            origin         = gr.origin,
                            destination    = gr.destination,
                            departure_date = dep_sample.isoformat(),
                            return_date    = ret_sample,
                            adults         = gr.adults,
                            cabin_class    = gr.cabin_class,
                        )
                        if not sample_offers:
                            continue

                        if (best_offers is None or
                                sample_offers[0]["price"] <
                                best_offers[0]["price"]):
                            best_offers = sample_offers
                            best_dep    = dep_sample.isoformat()

                if best_offers and best_offers[0]["price"] < metrics["market_min"]:
                    flex_saving = metrics["market_min"] - best_offers[0]["price"]
                    log.info(
                        "Flexible date for %s %s->%s: "
                        "cheapest on %s saves %.2f",
                        user.email, gr.origin, gr.destination,
                        best_dep, flex_saving
                    )
                    # Alert if saving exceeds threshold
                    if flex_saving >= ur.threshold_usd:
                        from app.email import send_sudden_sale_alert
                        send_sudden_sale_alert(
                            user            = user,
                            route           = gr,
                            baseline_price  = ur.baseline_price or metrics["market_min"],
                            current_price   = best_offers[0]["price"],
                            drop            = flex_saving,
                            currency        = currency,
                            airline         = best_offers[0]["airline"],
                            historic_median = historic_median,
                            top_offers      = best_offers[:5],
                        )

        log.info("=== Price check complete ===\n")


def check_rtw_itineraries(app):
    """Check prices for all active RTW itineraries."""
    with app.app_context():
        from app.models import db, RTWItinerary
        from app.email import send_rtw_alert

        itineraries = RTWItinerary.query.filter_by(is_active=True).all()
        if not itineraries:
            return

        log.info("Checking %d RTW itinerary/itineraries",
                 len(itineraries))

        for itin in itineraries:
            user      = itin.user

            # Skip expired trials
            if not user.trial_active():
                continue

            legs      = itin.legs
            total     = 0.0
            currency  = "AUD"
            all_found = True
            leg_summaries = []

            for leg in legs:
                # is_surface_segment means ground travel precedes
                # this leg — the leg itself is still a flight to price
                offers = fetch_all_offers(
                    origin         = leg.origin,
                    destination    = leg.destination,
                    departure_date = leg.departure_date,
                    return_date    = None,
                    adults         = leg.adults,
                    cabin_class    = leg.cabin_class,
                )
                if not offers:
                    log.info("No offer for RTW leg %d: %s->%s",
                             leg.leg_order, leg.origin, leg.destination)
                    all_found = False
                    break
                cheapest          = offers[0]
                leg.last_price    = cheapest["price"]
                leg.last_currency = cheapest["currency"]
                leg.last_airline  = cheapest["airline"]
                total    += cheapest["price"]
                currency  = cheapest["currency"]
                leg_summaries.append({
                    "order":       leg.leg_order,
                    "origin":      leg.origin,
                    "destination": leg.destination,
                    "date":        leg.departure_date,
                    "price":       cheapest["price"],
                    "currency":    cheapest["currency"],
                    "airline":     cheapest["airline"] or "Unknown",
                    "is_surface":  leg.is_surface_segment,
                })

            if not all_found:
                db.session.commit()
                continue

            log.info("RTW '%s' total: %s %.2f",
                     itin.name, currency, total)

            if itin.baseline_total is None:
                itin.baseline_total = total
                itin.last_total     = total
                itin.last_currency  = currency
                itin.last_checked   = datetime.now(timezone.utc)
                db.session.commit()
                continue

            drop = itin.baseline_total - total

            if drop >= itin.threshold_usd:
                send_rtw_alert(
                    user          = user,
                    itinerary     = itin,
                    baseline      = itin.baseline_total,
                    current_total = total,
                    drop          = drop,
                    currency      = currency,
                    legs          = leg_summaries,
                )
                itin.baseline_total = total
            elif total > itin.baseline_total:
                itin.baseline_total = total

            itin.last_total    = total
            itin.last_currency = currency
            itin.last_checked  = datetime.now(timezone.utc)
            db.session.commit()


def send_weekly_summaries(app):
    """
    Send weekly summary emails to all active users.
    Runs every Monday at 9am AEST.
    """
    with app.app_context():
        from app.models import db, User, UserRoute, GlobalRoute
        from app.models import MarketSummary, AlertLog
        from app.email import send_weekly_summary
        from datetime import datetime, timezone, timedelta
        from app.currency import convert

        now       = datetime.now(timezone.utc)
        week_ago  = now - timedelta(days=7)
        week_end  = now.strftime("%d %B %Y")

        users = User.query.filter_by(is_active=True).all()
        log.info("Sending weekly summaries to %d users", len(users))

        for user in users:
            # Skip deactivated accounts
            if not user.trial_active():
                continue

            currency     = user.preferred_currency
            user_routes  = UserRoute.query.filter_by(
                user_id=user.id, is_active=True
            ).all()

            if not user_routes:
                continue

            is_traveller = (user.subscription_tier == "traveller"
                            or user.is_admin)
            route_data   = []
            best_movement = None

            for ur in user_routes:
                gr = ur.global_route

                # Get market summaries for this week
                week_summaries = MarketSummary.query.filter(
                    MarketSummary.global_route_id == gr.id,
                    MarketSummary.checked_at      >= week_ago,
                ).order_by(MarketSummary.checked_at.asc()).all()

                if not week_summaries:
                    continue

                # Current price — latest summary
                latest       = week_summaries[-1]
                current_min  = latest.market_min
                curr_currency = latest.currency

                # Price vs last week
                last_week_summaries = MarketSummary.query.filter(
                    MarketSummary.global_route_id == gr.id,
                    MarketSummary.checked_at      >= week_ago - timedelta(days=7),
                    MarketSummary.checked_at      <  week_ago,
                ).order_by(MarketSummary.checked_at.desc()).first()

                trend = 0
                if last_week_summaries:
                    trend = (current_min -
                             last_week_summaries.market_min)

                # Alerts this week
                alerts_this_week = AlertLog.query.filter(
                    AlertLog.user_route_id == ur.id,
                    AlertLog.sent_at       >= week_ago,
                ).count()

                # Historic avg low (Traveller)
                historic_avg_low = None
                if is_traveller:
                    all_summaries = MarketSummary.query.filter(
                        MarketSummary.global_route_id == gr.id,
                    ).all()
                    if len(all_summaries) >= 30:
                        mins       = sorted([s.market_min for s in all_summaries])
                        cutoff_idx = max(1, int(len(mins) * 0.20))
                        historic_avg_low = statistics.mean(mins[:cutoff_idx])

                # Top carriers (Traveller)
                top_carriers = []
                if is_traveller and week_summaries:
                    carrier_counts = {}
                    for s in week_summaries:
                        if s.cheapest_airline:
                            carrier_counts[s.cheapest_airline] = (
                                carrier_counts.get(s.cheapest_airline, 0) + 1
                            )
                    top_carriers = sorted(
                        carrier_counts, key=carrier_counts.get, reverse=True
                    )[:3]

                # Threshold recommendation (Traveller, 30+ days)
                recommendation = None
                if is_traveller and len(week_summaries) >= 5:
                    all_sums = MarketSummary.query.filter(
                        MarketSummary.global_route_id == gr.id
                    ).all()
                    if len(all_sums) >= 30:
                        drops = [
                            s.market_median - s.market_min
                            for s in week_summaries
                            if s.market_median and s.market_min
                        ]
                        if drops:
                            max_drop = max(drops)
                            if ur.threshold_usd > max_drop and max_drop > 0:
                                suggested = (
                                    round(max_drop * 0.8 / 25) * 25
                                )
                                alerts_would_fire = sum(
                                    1 for d in drops if d >= suggested
                                )
                                recommendation = (
                                    f"The largest drop was "
                                    f"{curr_currency} {max_drop:,.0f} "
                                    f"below median. Your threshold requires "
                                    f"{curr_currency} {ur.threshold_usd:,.0f}. "
                                    f"Setting to "
                                    f"{curr_currency} {suggested:,.0f} "
                                    f"would have sent "
                                    f"{alerts_would_fire} alert"
                                    f"{'s' if alerts_would_fire != 1 else ''} "
                                    f"this week."
                                )

                # Convert to user currency
                current_display = convert(current_min, curr_currency, currency)
                trend_display   = convert(trend, curr_currency, currency)

                route_info = {
                    "origin":          gr.origin,
                    "destination":     gr.destination,
                    "current_price":   current_display,
                    "trend":           trend_display,
                    "currency":        currency,
                    "alerts_this_week": alerts_this_week,
                    "historic_avg_low": (
                        convert(historic_avg_low, curr_currency, currency)
                        if historic_avg_low else None
                    ),
                    "top_carriers":    top_carriers,
                    "recommendation":  recommendation,
                }
                route_data.append(route_info)

                # Track best movement
                if trend < 0:
                    drop = abs(trend_display)
                    if (best_movement is None or
                            drop > best_movement["drop"]):
                        best_movement = {
                            "origin":      gr.origin,
                            "destination": gr.destination,
                            "drop":        drop,
                            "currency":    currency,
                            "alerted":     alerts_this_week > 0,
                        }

            if not route_data:
                continue

            summary_data = {
                "routes":       route_data,
                "routes_count": len(route_data),
                "total_alerts": sum(r["alerts_this_week"]
                                    for r in route_data),
                "best_movement": best_movement,
                "week_ending":  week_end,
            }

            log.info("Sending weekly summary to %s — %d routes",
                     user.email, len(route_data))
            send_weekly_summary(user, summary_data)


def send_trial_reminders(app):
    """Send trial expiry reminder emails."""
    with app.app_context():
        from app.models import User
        from app.email import send_trial_reminder

        now   = datetime.now(timezone.utc)
        users = User.query.filter_by(
            subscription_tier="trial",
            is_active=True
        ).all()

        for user in users:
            if not user.trial_expires_at:
                continue
            expires = user.trial_expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            days_remaining = (expires - now).days
            if days_remaining in (4, 1):
                log.info("Trial reminder → %s (%d days left)",
                         user.email, days_remaining)
                send_trial_reminder(user, days_remaining)


def nightly_scrub(app):
    """Remove price history and market summary older than 6 months."""
    with app.app_context():
        from app.models import db, PriceHistory, MarketSummary

        cutoff = datetime.now(timezone.utc) - timedelta(days=180)

        ph = PriceHistory.query.filter(
            PriceHistory.checked_at < cutoff
        ).count()
        PriceHistory.query.filter(
            PriceHistory.checked_at < cutoff
        ).delete(synchronize_session=False)

        ms = MarketSummary.query.filter(
            MarketSummary.checked_at < cutoff
        ).count()
        MarketSummary.query.filter(
            MarketSummary.checked_at < cutoff
        ).delete(synchronize_session=False)

        db.session.commit()
        log.info("Nightly scrub — removed %d price history, "
                 "%d market summary records", ph, ms)


def start_scheduler(app):
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        func=check_all_routes, args=[app],
        trigger="interval", minutes=Config.CHECK_INTERVAL_MINUTES,
        id="price_check", name="Check flight prices",
        replace_existing=True,
    )
    scheduler.add_job(
        func=check_rtw_itineraries, args=[app],
        trigger="interval", minutes=Config.CHECK_INTERVAL_MINUTES,
        id="rtw_check", name="Check RTW itinerary prices",
        replace_existing=True,
    )
    scheduler.add_job(
        func=nightly_scrub, args=[app],
        trigger="cron", hour=16, minute=0,
        id="nightly_scrub", name="Nightly data scrub",
        replace_existing=True,
    )
    scheduler.add_job(
        func=send_trial_reminders, args=[app],
        trigger="cron", hour=23, minute=0,
        id="trial_reminders", name="Trial expiry reminders",
        replace_existing=True,
    )


    # Weekly summary — every Monday 9am AEST = Sunday 11pm UTC
    scheduler.add_job(
        func=send_weekly_summaries, args=[app],
        trigger="cron", day_of_week="sun", hour=23, minute=0,
        id="weekly_summary", name="Weekly summary emails",
        replace_existing=True,
    )
    scheduler.start()
    log.info("Scheduler started — checking every %d minute(s)",
             Config.CHECK_INTERVAL_MINUTES)
