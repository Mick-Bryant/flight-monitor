from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import (db, GlobalRoute, UserRoute, AlertLog, Airport,
                        RTWItinerary, RTWLeg, MarketSummary, PriceHistory,
                        detect_route_type, find_or_create_global_route, TIERS)
from app.currency import get_supported_currencies, convert, format_price
SUPPORTED_CURRENCIES = get_supported_currencies()
from config import Config

main_bp = Blueprint("main", __name__)

# ---------------------------------------------------------------------------
# Country name lookup for airport search
# ---------------------------------------------------------------------------

COUNTRY_NAMES = {
    "AF": "Afghanistan", "AL": "Albania", "DZ": "Algeria",
    "AD": "Andorra", "AO": "Angola", "AG": "Antigua and Barbuda",
    "AR": "Argentina", "AM": "Armenia", "AU": "Australia",
    "AT": "Austria", "AZ": "Azerbaijan", "BS": "Bahamas",
    "BH": "Bahrain", "BD": "Bangladesh", "BB": "Barbados",
    "BY": "Belarus", "BE": "Belgium", "BZ": "Belize",
    "BJ": "Benin", "BT": "Bhutan", "BO": "Bolivia",
    "BA": "Bosnia and Herzegovina", "BW": "Botswana", "BR": "Brazil",
    "BN": "Brunei", "BG": "Bulgaria", "BF": "Burkina Faso",
    "BI": "Burundi", "CV": "Cape Verde", "KH": "Cambodia",
    "CM": "Cameroon", "CA": "Canada", "CF": "Central African Republic",
    "TD": "Chad", "CL": "Chile", "CN": "China", "CO": "Colombia",
    "KM": "Comoros", "CG": "Congo", "CD": "Congo (DRC)",
    "CK": "Cook Islands", "CR": "Costa Rica", "HR": "Croatia",
    "CU": "Cuba", "CW": "Curacao", "CY": "Cyprus",
    "CZ": "Czech Republic", "DK": "Denmark", "DJ": "Djibouti",
    "DM": "Dominica", "DO": "Dominican Republic", "EC": "Ecuador",
    "EG": "Egypt", "SV": "El Salvador", "GQ": "Equatorial Guinea",
    "ER": "Eritrea", "EE": "Estonia", "SZ": "Eswatini",
    "ET": "Ethiopia", "FK": "Falkland Islands", "FO": "Faroe Islands",
    "FJ": "Fiji", "FI": "Finland", "FR": "France",
    "GF": "French Guiana", "PF": "French Polynesia", "GA": "Gabon",
    "GM": "Gambia", "GE": "Georgia", "DE": "Germany", "GH": "Ghana",
    "GI": "Gibraltar", "GR": "Greece", "GL": "Greenland",
    "GD": "Grenada", "GP": "Guadeloupe", "GU": "Guam",
    "GT": "Guatemala", "GG": "Guernsey", "GN": "Guinea",
    "GW": "Guinea-Bissau", "GY": "Guyana", "HT": "Haiti",
    "HN": "Honduras", "HK": "Hong Kong", "HU": "Hungary",
    "IS": "Iceland", "IN": "India", "ID": "Indonesia",
    "IR": "Iran", "IQ": "Iraq", "IE": "Ireland",
    "IM": "Isle of Man", "IL": "Israel", "IT": "Italy",
    "JM": "Jamaica", "JP": "Japan", "JE": "Jersey", "JO": "Jordan",
    "KZ": "Kazakhstan", "KE": "Kenya", "KI": "Kiribati",
    "KP": "North Korea", "KR": "South Korea", "KW": "Kuwait",
    "KG": "Kyrgyzstan", "LA": "Laos", "LV": "Latvia",
    "LB": "Lebanon", "LS": "Lesotho", "LR": "Liberia",
    "LY": "Libya", "LI": "Liechtenstein", "LT": "Lithuania",
    "LU": "Luxembourg", "MO": "Macao", "MG": "Madagascar",
    "MW": "Malawi", "MY": "Malaysia", "MV": "Maldives",
    "ML": "Mali", "MT": "Malta", "MH": "Marshall Islands",
    "MQ": "Martinique", "MR": "Mauritania", "MU": "Mauritius",
    "MX": "Mexico", "FM": "Micronesia", "MD": "Moldova",
    "MC": "Monaco", "MN": "Mongolia", "ME": "Montenegro",
    "MS": "Montserrat", "MA": "Morocco", "MZ": "Mozambique",
    "MM": "Myanmar", "NA": "Namibia", "NR": "Nauru", "NP": "Nepal",
    "NL": "Netherlands", "NC": "New Caledonia", "NZ": "New Zealand",
    "NI": "Nicaragua", "NE": "Niger", "NG": "Nigeria", "NU": "Niue",
    "NF": "Norfolk Island", "MP": "Northern Mariana Islands",
    "NO": "Norway", "OM": "Oman", "PK": "Pakistan", "PW": "Palau",
    "PA": "Panama", "PG": "Papua New Guinea", "PY": "Paraguay",
    "PE": "Peru", "PH": "Philippines", "PL": "Poland",
    "PT": "Portugal", "PR": "Puerto Rico", "QA": "Qatar",
    "RE": "Reunion", "RO": "Romania", "RU": "Russia", "RW": "Rwanda",
    "KN": "Saint Kitts and Nevis", "LC": "Saint Lucia",
    "VC": "Saint Vincent and the Grenadines", "WS": "Samoa",
    "SM": "San Marino", "ST": "Sao Tome and Principe",
    "SA": "Saudi Arabia", "SN": "Senegal", "RS": "Serbia",
    "SC": "Seychelles", "SL": "Sierra Leone", "SG": "Singapore",
    "SX": "Sint Maarten", "SK": "Slovakia", "SI": "Slovenia",
    "SB": "Solomon Islands", "SO": "Somalia", "ZA": "South Africa",
    "SS": "South Sudan", "ES": "Spain", "LK": "Sri Lanka",
    "SD": "Sudan", "SR": "Suriname", "SE": "Sweden",
    "CH": "Switzerland", "SY": "Syria", "TW": "Taiwan",
    "TJ": "Tajikistan", "TZ": "Tanzania", "TH": "Thailand",
    "TL": "Timor-Leste", "TG": "Togo", "TO": "Tonga",
    "TT": "Trinidad and Tobago", "TN": "Tunisia", "TR": "Turkey",
    "TM": "Turkmenistan", "TC": "Turks and Caicos Islands",
    "TV": "Tuvalu", "UG": "Uganda", "UA": "Ukraine",
    "AE": "United Arab Emirates", "GB": "United Kingdom",
    "US": "United States", "UY": "Uruguay", "UZ": "Uzbekistan",
    "VU": "Vanuatu", "VE": "Venezuela", "VN": "Vietnam",
    "VG": "British Virgin Islands", "VI": "US Virgin Islands",
    "WF": "Wallis and Futuna", "YE": "Yemen", "ZM": "Zambia",
    "ZW": "Zimbabwe", "XK": "Kosovo", "BQ": "Caribbean Netherlands",
    "CC": "Cocos Islands", "CX": "Christmas Island",
    "IO": "British Indian Ocean Territory", "MF": "Saint Martin",
    "BL": "Saint Barthelemy", "PM": "Saint Pierre and Miquelon",
    "YT": "Mayotte", "UM": "US Minor Outlying Islands",
}


# ---------------------------------------------------------------------------
# Public landing page
# ---------------------------------------------------------------------------

@main_bp.route("/")
def landing():
    """Public landing page — shown to logged-out visitors."""
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("landing.html")


FAQ = [
    {
        "section": "Getting Started",
        "questions": [
            {
                "q": "How does the free trial work?",
                "a": "Your trial runs for 14 days from the moment you register. During the trial you get full access to all alert types, up to 3 routes and 1 RTW itinerary, and price checks every 2 hours. No credit card is required to start. At the end of the trial you can upgrade to Explorer or Traveller to keep monitoring.",
            },
            {
                "q": "Do I need a credit card to sign up?",
                "a": "No. The 14-day trial is completely free with no credit card required. You only need to provide payment details when you choose to upgrade to a paid plan.",
            },
            {
                "q": "How do I get access? Is it open to everyone?",
                "a": "Flight Monitor is currently invite-only during its early beta phase. Registration requires an invitation link from an existing member or the Flight Monitor team. This lets us maintain quality and grow responsibly before opening publicly.",
            },
        ],
    },
    {
        "section": "How Alerts Work",
        "questions": [
            {
                "q": "What's the difference between a Flash Sale and Historic Low alert?",
                "a": "<strong>Flash Sale</strong> alerts fire when the current market price drops by your threshold amount compared to recent prices — a sudden movement that signals a limited-time sale.<br><br><strong>Historic Low</strong> alerts fire when the current price is lower than the average of the cheapest 20% of prices recorded for that route over time — meaning it's genuinely the cheapest this route has been, not just temporarily cheaper. Both alert types are active from day one.",
            },
            {
                "q": "How often are prices checked?",
                "a": "Trial and Explorer users get price checks every 2 hours. Traveller users get checks every hour. Prices are pulled from the live Duffel flight API, giving you real market data across all carriers — not cached or delayed results.",
            },
            {
                "q": "What is my alert threshold and how do I set it?",
                "a": "Your threshold is the minimum price drop (in your preferred currency) that triggers a Flash Sale alert. Flight Monitor sets smart regional defaults — for example, international long-haul routes have a higher default threshold than short domestic ones. You can override the threshold per route, or set a global default in your profile. Traveller users also receive threshold recommendations based on observed price movements for each route.",
            },
            {
                "q": "Will I get false alerts when prices temporarily dip?",
                "a": "Flight Monitor includes a false alert guard — if the price has risen since the last alert was sent, no new alert fires. Your baseline price also automatically resets when prices rise or after an alert, so the system always compares against a meaningful reference point rather than an outdated one.",
            },
        ],
    },
    {
        "section": "Features",
        "questions": [
            {
                "q": "What are Cheapest, Fastest and Best Value alert modes?",
                "a": "Traveller users can choose which offer drives their alerts — not just the cheapest one available:<br><br><strong>Cheapest</strong> (default) — alerts on the lowest-price offer, the standard behaviour.<br><br><strong>Fastest</strong> — alerts on the shortest total journey time. Useful if you value your time over the last dollar saved.<br><br><strong>Best Value</strong> — alerts on the offer with the lowest effective cost, which combines price with the time cost of a longer journey and the inconvenience of extra stops. The weighting coefficients are configurable.<br><br>The mode is set as a default in your profile and can be overridden per route. Explorer and Trial users always use Cheapest mode.",
            },
            {
                "q": "What are RTW itineraries?",
                "a": "RTW (Around The World) itineraries let you monitor multi-leg journeys as a single combined price. Add each leg of your trip and Flight Monitor tracks the total cost across all legs, alerting you when the combined price drops below your threshold. Each alert includes a per-leg breakdown so you can see exactly where the savings came from. Surface segments (ground travel between legs) are flagged in the breakdown.",
            },
            {
                "q": "What is the Nearby Airports feature?",
                "a": "When you enable Nearby Airports on a route, Flight Monitor also checks major airports within 100km of your origin for cheaper departure options. If a nearby airport has a significantly cheaper fare, you'll receive a separate alert showing the saving — along with a reminder to factor in the cost of getting to that airport.",
            },
            {
                "q": "What is Flexible Date searching?",
                "a": "Instead of monitoring a single departure date, Flexible Date search monitors a window of dates around your target. Flight Monitor samples approximately 9 dates across the window regardless of how wide it is, finding the cheapest day to fly. You can also set a flexible trip duration (±3, 7, or 14 days from your base duration) to catch deals on slightly shorter or longer trips.",
            },
            {
                "q": "Which airlines and carriers does Flight Monitor cover?",
                "a": "Flight Monitor sources prices from Duffel, which covers NDC (New Distribution Capability) airlines — including Qantas, Emirates, Singapore Airlines, British Airways, Lufthansa, and most major full-service international carriers.<br><br>Low-cost carriers that sell direct only — such as Jetstar, Ryanair, and AirAsia — are not currently included. For routes where LCCs are the dominant option, Flight Monitor works best as a complement to a quick direct check on those airlines' own sites.",
            },
            {
                "q": "What is the Weekly Summary email?",
                "a": "Every Monday morning (9am AEST) you receive a summary of all your monitored routes — current prices, weekly price movement, trend direction, and any alerts fired during the week. Traveller users also get historic average low comparisons, top carriers per route, and personalised threshold recommendations based on observed price data (available after 30 days of data).",
            },
            {
                "q": "Which currencies are supported?",
                "a": "Flight Monitor supports 166 currencies. You can set your preferred currency in your profile and all prices — on the dashboard, in alerts, and in weekly summaries — will be shown in that currency. Exchange rates are refreshed every hour.",
            },
        ],
    },
    {
        "section": "Pricing & Billing",
        "questions": [
            {
                "q": "What's the difference between Explorer and Traveller?",
                "a": "<strong>Explorer</strong> (AUD $8/month or $80/year) suits occasional to regular travellers monitoring a handful of routes. 5 routes, 2 RTW itineraries, 1 alert recipient, checks every 2 hours.<br><br><strong>Traveller</strong> (AUD $20/month or $192/year) is for frequent flyers and power users who want the full toolkit: 20 routes, 20 RTW itineraries, up to 4 alert recipients, hourly checks, and Cheapest / Fastest / Best Value optimization modes. The full weekly summary with threshold recommendations is also Traveller-only. The annual plan typically pays for itself on the first deal it catches.",
            },
            {
                "q": "Is there a discount for paying annually?",
                "a": "Yes — both plans include 2 months free on the annual option. Explorer annual is AUD $80 (vs $96 monthly). Traveller annual is AUD $192 (vs $240 monthly). Annual plans are billed upfront.",
            },
            {
                "q": "How does cancellation work?",
                "a": "You can cancel at any time from your Profile page. Monthly plans run to the end of the current billing month before deactivating. Annual plans run to the end of the current annual period. Trial cancellations take effect immediately. Your data is retained for 12 months after deactivation in case you choose to reactivate.",
            },
            {
                "q": "Can I reactivate my account after cancelling?",
                "a": "Yes. You can reactivate from the login page and choose a monthly or annual plan. A new billing period starts from reactivation. Previous trial users who cancelled must subscribe to a paid plan — a new free trial is not available on reactivation.",
            },
        ],
    },
    {
        "section": "Data & Privacy",
        "questions": [
            {
                "q": "Where do the flight prices come from?",
                "a": "Prices are sourced from the Duffel flight API, which aggregates real-time fares from airlines and global distribution systems. Each price check fetches up to 20 live offers per route. Prices are indicative — always verify the current fare on the airline or booking site before purchasing.",
            },
            {
                "q": "Do you sell my data or show ads?",
                "a": "No. Flight Monitor is a subscription product. We do not sell your data, show ads, or share your route information with third parties. Your route and travel preferences are used solely to power your price alerts.",
            },
            {
                "q": "How long is my price history kept?",
                "a": "Price history and market summaries are retained for 6 months. Older data is automatically removed nightly. Your alert history is kept permanently so you have a record of every deal you were notified about. Account data is retained for 12 months after deactivation.",
            },
        ],
    },
]


@main_bp.route("/faq")
def faq():
    return render_template("faq.html", faq=FAQ)


@main_bp.route("/terms")
def terms():
    return render_template("terms.html")


@main_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ---------------------------------------------------------------------------
# Guides (SEO content pages)
# ---------------------------------------------------------------------------

GUIDES = [
    {
        "slug": "cheapest-flights-from-sydney",
        "title": "Cheapest Flights from Sydney",
        "description": "Best times to book, top routes, price ranges, and how to know when a Sydney fare is genuinely cheap.",
        "tag": "Sydney",
    },
    {
        "slug": "cheapest-flights-from-melbourne",
        "title": "Cheapest Flights from Melbourne",
        "description": "Route guide for MEL — when fares are genuinely low, which routes swing most, and how to catch the real deals.",
        "tag": "Melbourne",
    },
    {
        "slug": "cheapest-flights-from-brisbane",
        "title": "Cheapest Flights from Brisbane",
        "description": "Route guide for BNE — Pacific, Asian, and European routes with price ranges and booking timing tips.",
        "tag": "Brisbane",
    },
    {
        "slug": "cheapest-flights-from-perth",
        "title": "Cheapest Flights from Perth",
        "description": "Route guide for PER including the direct London flight, Bali fares, and how to catch flash sales.",
        "tag": "Perth",
    },
    {
        "slug": "how-to-find-cheap-flights",
        "title": "How to Find Cheap Flights from Australia",
        "description": "Why most price alerts are noise, what 'actually cheap' means, and how to stop guessing and start knowing.",
        "tag": "Guide",
    },
]


@main_bp.route("/guides")
def guides_index():
    return render_template("guides/index.html", articles=GUIDES)


@main_bp.route("/guides/<slug>")
def guide_article(slug):
    slugs = [g["slug"] for g in GUIDES]
    if slug not in slugs:
        from flask import abort
        abort(404)
    return render_template(f"guides/{slug}.html", all_articles=GUIDES)


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

@main_bp.route("/welcome")
@login_required
def onboarding():
    """Onboarding page — shown to new users on first login."""
    if current_user.onboarding_complete:
        return redirect(url_for("main.dashboard"))
    return render_template("onboarding.html")


@main_bp.route("/welcome/save", methods=["POST"])
@login_required
def onboarding_save():
    """Save the first route added during onboarding."""
    if not current_user.can_add_route():
        flash("Route limit reached.", "warning")
        return redirect(url_for("main.upgrade"))

    origin         = request.form.get("origin",         "").strip().upper()
    destination    = request.form.get("destination",    "").strip().upper()
    departure_date = request.form.get("departure_date", "").strip()
    return_date    = request.form.get("return_date",    "").strip() or None
    adults         = int(request.form.get("adults", 1))
    cabin_class    = request.form.get("cabin_class", "economy")
    threshold      = float(request.form.get("threshold_usd", 400))

    if not origin or not destination or not departure_date:
        flash("Please select airports and a departure date.", "danger")
        return render_template("onboarding.html")

    origin_airport = Airport.query.filter_by(iata_code=origin).first()
    dest_airport   = Airport.query.filter_by(iata_code=destination).first()
    route_type, _  = detect_route_type(origin_airport, dest_airport)

    global_route = find_or_create_global_route(
        origin, destination, departure_date, return_date,
        adults, cabin_class
    )

    db.session.add(UserRoute(
        user_id         = current_user.id,
        global_route_id = global_route.id,
        route_type      = route_type,
        threshold_usd   = threshold,
    ))

    current_user.onboarding_complete = True
    db.session.commit()

    flash(
        f"✈️ Now monitoring {origin} → {destination}. "
        f"We'll alert you when the price drops.",
        "success"
    )
    return redirect(url_for("main.onboarding_complete"))


@main_bp.route("/welcome/skip")
@login_required
def onboarding_skip():
    """User skips onboarding — mark complete and go to dashboard."""
    current_user.onboarding_complete = True
    db.session.commit()
    return redirect(url_for("main.dashboard"))


@main_bp.route("/welcome/done")
@login_required
def onboarding_complete():
    """Onboarding completion screen."""
    return render_template("onboarding_complete.html")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@main_bp.route("/dashboard")
@login_required
def dashboard():
    # Redirect new users to onboarding
    if not current_user.onboarding_complete and not current_user.is_admin:
        return redirect(url_for("main.onboarding"))

    user_routes = UserRoute.query.filter_by(
        user_id=current_user.id
    ).order_by(UserRoute.created_at.desc()).all()
    currency = current_user.preferred_currency
    return render_template(
        "dashboard.html",
        user_routes  = user_routes,
        currency     = currency,
        convert      = convert,
        format_price = format_price,
    )


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    from app.email import MAJOR_AIRLINES
    import json
    if request.method == "POST":
        name               = request.form.get("name",              "").strip()
        alert_email        = request.form.get("alert_email",       "").strip().lower()
        preferred_currency = request.form.get("preferred_currency","AUD").strip()
        memberships        = request.form.getlist("memberships")

        if not name:
            flash("Name cannot be blank.", "danger")
            return render_template("profile.html",
                                   currencies=SUPPORTED_CURRENCIES,
                                   airlines=MAJOR_AIRLINES)

        current_user.name                = name
        current_user.alert_email         = alert_email if alert_email else None
        current_user.preferred_currency  = preferred_currency
        current_user.airline_memberships = json.dumps(memberships)
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("main.profile"))

    return render_template("profile.html",
                           currencies=SUPPORTED_CURRENCIES,
                           airlines=MAJOR_AIRLINES)


@main_bp.route("/profile/thresholds", methods=["POST"])
@login_required
def save_thresholds():
    try:
        current_user.threshold_domestic      = float(request.form.get("threshold_domestic",      150))
        current_user.threshold_oceania       = float(request.form.get("threshold_oceania",       200))
        current_user.threshold_asia          = float(request.form.get("threshold_asia",          300))
        current_user.threshold_middle_east   = float(request.form.get("threshold_middle_east",   350))
        current_user.threshold_europe        = float(request.form.get("threshold_europe",        500))
        current_user.threshold_africa        = float(request.form.get("threshold_africa",        400))
        current_user.threshold_north_america = float(request.form.get("threshold_north_america", 550))
        current_user.threshold_south_america = float(request.form.get("threshold_south_america", 500))
        current_user.threshold_international = float(request.form.get("threshold_international", 400))
        db.session.commit()
        flash("Alert thresholds saved.", "success")
    except Exception:
        flash("Error saving thresholds.", "danger")
    return redirect(url_for("main.profile"))


@main_bp.route("/profile/optimize", methods=["POST"])
@login_required
def save_optimize():
    if not current_user.can_optimize():
        flash("Fastest and Best Value modes require a Traveller subscription.", "warning")
        return redirect(url_for("main.profile"))
    mode = request.form.get("optimize_for", "cheapest")
    if mode not in ("cheapest", "fastest", "best_value"):
        mode = "cheapest"
    current_user.optimize_for = mode
    db.session.commit()
    flash("Alert optimization preference saved.", "success")
    return redirect(url_for("main.profile"))


@main_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    from app import bcrypt
    current_pw = request.form.get("current_password", "").strip()
    new_pw     = request.form.get("new_password",     "").strip()
    confirm_pw = request.form.get("confirm_password", "").strip()
    if not bcrypt.check_password_hash(current_user.password, current_pw):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("main.profile"))
    if len(new_pw) < 8:
        flash("New password must be at least 8 characters.", "danger")
        return redirect(url_for("main.profile"))
    if new_pw != confirm_pw:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("main.profile"))
    current_user.password = bcrypt.generate_password_hash(
        new_pw
    ).decode("utf-8")
    db.session.commit()
    flash("Password updated successfully.", "success")
    return redirect(url_for("main.profile"))


# ---------------------------------------------------------------------------
# Routes (user_routes + global_routes)
# ---------------------------------------------------------------------------

@main_bp.route("/routes/add", methods=["GET", "POST"])
@login_required
def add_route():
    if not current_user.can_add_route():
        tier  = current_user.tier_config()
        flash(
            f"You have reached the {tier['max_routes']}-route limit "
            f"on your {tier['name']} plan. Upgrade to add more routes.",
            "warning"
        )
        return redirect(url_for("main.upgrade"))

    if request.method == "POST":
        if not current_user.can_add_route():
            flash("Route limit reached.", "warning")
            return redirect(url_for("main.upgrade"))

        origin         = request.form.get("origin",         "").strip().upper()
        destination    = request.form.get("destination",    "").strip().upper()
        departure_date = request.form.get("departure_date", "").strip()
        return_date    = request.form.get("return_date",    "").strip() or None
        adults         = int(request.form.get("adults", 1))
        cabin_class    = request.form.get("cabin_class", "economy")

        if not origin or not destination or not departure_date:
            flash("Origin, destination and departure date are required.", "danger")
            return render_template("add_route.html")
        if origin == destination:
            flash("Origin and destination cannot be the same.", "danger")
            return render_template("add_route.html")

        # Detect route type
        origin_airport = Airport.query.filter_by(iata_code=origin).first()
        dest_airport   = Airport.query.filter_by(iata_code=destination).first()
        route_type, threshold_key = detect_route_type(
            origin_airport, dest_airport
        )

        # Threshold
        threshold_override = request.form.get("threshold_usd", "").strip()
        threshold = (float(threshold_override) if threshold_override
                     else current_user.get_threshold(threshold_key))

        # Nearby airports
        nearby        = request.form.get("nearby_airports") == "on"
        nearby_saving = float(request.form.get("nearby_min_saving", 200))

        # Flexible dates
        flexible_dates     = request.form.get("flexible_dates") == "on"
        flex_period_type   = request.form.get("flex_period_type", "weeks")
        flex_period_value  = int(request.form.get("flex_period_value", 2))
        flex_duration      = request.form.get("flex_duration") == "on"
        flex_duration_days = int(request.form.get("flex_duration_days", 7))

        if flex_period_type == "days":
            flex_period_value = max(1, min(30, flex_period_value))
        else:
            flex_period_value = max(1, min(4,  flex_period_value))
        if str(flex_duration_days) not in ["3", "7", "14"]:
            flex_duration_days = 7

        # Optimize mode — Traveller only; NULL means inherit from user profile
        optimize_raw = request.form.get("optimize_for", "").strip()
        if optimize_raw in ("fastest", "best_value") and current_user.can_optimize():
            route_optimize_for = optimize_raw
        elif optimize_raw == "cheapest":
            route_optimize_for = "cheapest"
        else:
            route_optimize_for = None

        # Find or create global route
        global_route = find_or_create_global_route(
            origin, destination, departure_date, return_date,
            adults, cabin_class
        )

        # Create user route
        user_route = UserRoute(
            user_id            = current_user.id,
            global_route_id    = global_route.id,
            route_type         = route_type,
            optimize_for       = route_optimize_for,
            threshold_usd      = threshold,
            nearby_airports    = nearby,
            nearby_min_saving  = nearby_saving,
            flexible_dates     = flexible_dates,
            flex_period_type   = flex_period_type,
            flex_period_value  = flex_period_value,
            flex_duration      = flex_duration,
            flex_duration_days = flex_duration_days,
        )
        db.session.add(user_route)
        db.session.commit()

        flash(
            f"Now monitoring {origin} → {destination} "
            f"({route_type}, threshold AUD {threshold:,.0f}).",
            "success"
        )
        return redirect(url_for("main.dashboard"))

    return render_template("add_route.html")


@main_bp.route("/routes/<int:user_route_id>/toggle", methods=["POST"])
@login_required
def toggle_route(user_route_id):
    ur = UserRoute.query.filter_by(
        id=user_route_id, user_id=current_user.id
    ).first_or_404()
    ur.is_active = not ur.is_active

    # Deactivate global route if no more active user routes
    if not ur.is_active:
        other_active = UserRoute.query.filter(
            UserRoute.global_route_id == ur.global_route_id,
            UserRoute.is_active       == True,
            UserRoute.id              != ur.id,
        ).count()
        if other_active == 0:
            ur.global_route.is_active = False

    db.session.commit()
    gr     = ur.global_route
    status = "resumed" if ur.is_active else "paused"
    flash(f"Route {gr.origin}→{gr.destination} {status}.", "info")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/routes/<int:user_route_id>/delete", methods=["POST"])
@login_required
def delete_route(user_route_id):
    ur = UserRoute.query.filter_by(
        id=user_route_id, user_id=current_user.id
    ).first_or_404()

    gr          = ur.global_route
    route_label = f"{gr.origin}→{gr.destination}"
    alert_count = AlertLog.query.filter_by(user_route_id=ur.id).count()

    # Delete user route and its alerts
    AlertLog.query.filter_by(user_route_id=ur.id).delete()
    db.session.delete(ur)

    # Check if global route still has active users
    remaining = UserRoute.query.filter(
        UserRoute.global_route_id == gr.id,
        UserRoute.id              != ur.id,
    ).count()

    if remaining == 0:
        # No other users — deactivate global route
        # Keep price history and market summary (scrubbed by nightly job)
        gr.is_active = False

    db.session.commit()
    flash(
        f"Route {route_label} deleted — "
        f"{alert_count} alert records removed.",
        "info"
    )
    return redirect(url_for("main.dashboard"))


@main_bp.route("/routes/<int:user_route_id>/history")
@login_required
def route_history(user_route_id):
    ur = UserRoute.query.filter_by(
        id=user_route_id, user_id=current_user.id
    ).first_or_404()

    gr     = ur.global_route
    alerts = AlertLog.query.filter_by(
        user_route_id=ur.id
    ).order_by(AlertLog.sent_at.desc()).all()

    latest = MarketSummary.query.filter_by(
        global_route_id=gr.id
    ).order_by(MarketSummary.checked_at.desc()).first()
    latest_median = latest.market_median if latest else None

    oldest = MarketSummary.query.filter_by(
        global_route_id=gr.id
    ).order_by(MarketSummary.checked_at.asc()).first()
    days_of_data = 0
    if oldest:
        from datetime import datetime, timezone
        oldest_dt = oldest.checked_at
        if oldest_dt.tzinfo is None:
            oldest_dt = oldest_dt.replace(tzinfo=timezone.utc)
        days_of_data = (datetime.now(timezone.utc) - oldest_dt).days

    return render_template(
        "history.html",
        user_route    = ur,
        route         = gr,
        alerts        = alerts,
        latest_median = latest_median,
        days_of_data  = days_of_data,
        convert       = convert,
        format_price  = format_price,
    )


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@main_bp.route("/api/routes/<int:user_route_id>/history")
@login_required
def route_history_data(user_route_id):
    from flask import jsonify
    ur = UserRoute.query.filter_by(
        id=user_route_id, user_id=current_user.id
    ).first_or_404()

    history  = MarketSummary.query.filter_by(
        global_route_id=ur.global_route_id
    ).order_by(MarketSummary.checked_at.asc()).all()
    currency = current_user.preferred_currency

    return jsonify({
        "labels":   [h.checked_at.strftime("%d %b %H:%M") for h in history],
        "prices":   [convert(h.market_min,    h.currency, currency)
                     for h in history],
        "medians":  [convert(h.market_median, h.currency, currency)
                     for h in history],
        "currency": currency,
    })


@main_bp.route("/api/airports")
@login_required
def airport_search():
    from flask import jsonify
    term = request.args.get("q", "").strip()
    if len(term) < 2:
        return jsonify([])

    term_lower = term.lower()

    matching_iso = [
        iso for iso, name in COUNTRY_NAMES.items()
        if term_lower in name.lower()
    ]

    CITY_ALIASES = {
        "bali":    "Kuta",      "bombay":   "Mumbai",
        "calcutta":"Kolkata",   "madras":   "Chennai",
        "peking":  "Beijing",   "canton":   "Guangzhou",
        "rangoon": "Yangon",    "saigon":   "Ho Chi Minh City",
        "prague":  "Praha",     "warsaw":   "Warszawa",
        "moscow":  "Moskva",    "florence": "Firenze",
        "venice":  "Venezia",   "naples":   "Napoli",
        "milan":   "Milano",    "rome":     "Roma",
        "cologne": "Koeln",     "munich":   "Muenchen",
        "zurich":  "Zuerich",
    }
    alias = CITY_ALIASES.get(term_lower)

    filters = [
        Airport.iata_code.ilike(f"{term}%"),
        Airport.city.ilike(f"%{term}%"),
        Airport.name.ilike(f"%{term}%"),
        Airport.municipality.ilike(f"%{term}%"),
    ]
    if alias:
        filters.append(Airport.city.ilike(f"%{alias}%"))
        filters.append(Airport.municipality.ilike(f"%{alias}%"))
    if matching_iso:
        filters.append(Airport.iso_country.in_(matching_iso))

    from sqlalchemy import case
    type_order = case(
        (Airport.airport_type == "large_airport",  1),
        (Airport.airport_type == "medium_airport", 2),
        else_=3
    )

    results = Airport.query.filter(
        Airport.is_active == True,
        db.or_(*filters)
    ).order_by(type_order, Airport.city).limit(20).all()

    return jsonify([{
        "iata":    a.iata_code,
        "display": (f"{a.municipality or a.city} ({a.iata_code}) "
                    f"\u2014 {a.name}, "
                    f"{COUNTRY_NAMES.get(a.iso_country, a.iso_country or '')}"),
        "city":    a.municipality or a.city,
        "country": COUNTRY_NAMES.get(a.iso_country, a.iso_country or ""),
        "region":  a.region or "",
    } for a in results])


@main_bp.route("/api/routes/threshold")
@login_required
def get_route_threshold():
    from flask import jsonify
    origin      = request.args.get("origin",      "").upper()
    destination = request.args.get("destination", "").upper()

    origin_airport = Airport.query.filter_by(iata_code=origin).first()
    dest_airport   = Airport.query.filter_by(iata_code=destination).first()
    route_type, threshold_key = detect_route_type(
        origin_airport, dest_airport
    )
    threshold = current_user.get_threshold(threshold_key)

    region_labels = {
        "domestic":      "Domestic",
        "oceania":       "Australia / Oceania",
        "asia":          "Asia",
        "middle_east":   "Middle East",
        "europe":        "Europe",
        "africa":        "Africa",
        "north_america": "North America",
        "south_america": "South America",
        "international": "International",
    }
    region_label = region_labels.get(threshold_key, "International")

    return jsonify({
        "route_type":    route_type,
        "threshold":     threshold,
        "currency":      current_user.preferred_currency,
        "threshold_key": threshold_key,
        "region_label":  region_label,
    })


@main_bp.route("/api/rtw/check_connection")
@login_required
def rtw_check_connection():
    from flask import jsonify
    from app.models import check_leg_connection, same_city
    prev_dest   = request.args.get("prev_dest",   "").upper()
    next_origin = request.args.get("next_origin", "").upper()
    if not prev_dest or not next_origin:
        return jsonify({"status": "unknown"})
    connected, is_same_city, needs_warning = check_leg_connection(
        prev_dest, next_origin
    )
    if connected:
        return jsonify({
            "status":  "connected",
            "message": f"{prev_dest} → {next_origin} connects directly.",
        })
    elif is_same_city:
        return jsonify({
            "status":  "same_city",
            "message": (f"{prev_dest} and {next_origin} are in the "
                        f"same city. This connection is fine."),
        })
    else:
        return jsonify({
            "status":  "gap",
            "message": (f"Leg arrives at {prev_dest} but next leg "
                        f"departs from {next_origin}. If you plan to "
                        f"travel between them by ground, tick the "
                        f"surface segment checkbox below."),
        })


# ---------------------------------------------------------------------------
# Cancellation & Reactivation
# ---------------------------------------------------------------------------

@main_bp.route("/cancel")
@login_required
def cancel_confirm():
    """Show cancellation confirmation page."""
    if current_user.subscription_status == "deactivated":
        return redirect(url_for("main.reactivate"))
    return render_template("cancel_confirm.html")


@main_bp.route("/cancel/confirm", methods=["POST"])
@login_required
def cancel_subscription():
    """Process cancellation."""
    from datetime import datetime, timezone

    if current_user.is_trial():
        # Trial — deactivate immediately
        current_user.deactivate()
        db.session.commit()
        flash(
            "Your trial has been cancelled. "
            "Your data will be kept for 12 months.",
            "info"
        )
        return redirect(url_for("auth.logout"))

    elif current_user.account_type == "invited":
        # Invited — deactivate immediately
        current_user.deactivate()
        db.session.commit()
        flash(
            "Your account has been deactivated. "
            "Your data will be kept for 12 months.",
            "info"
        )
        return redirect(url_for("auth.logout"))

    else:
        # Paid subscriber — cancel at period end
        current_user.cancel_subscription()
        db.session.commit()
        period_end = (
            current_user.subscription_period_end.strftime("%d %B %Y")
            if current_user.subscription_period_end
            else "the end of your billing period"
        )
        flash(
            f"Your subscription has been cancelled. "
            f"You have full access until {period_end}.",
            "info"
        )
        return redirect(url_for("main.profile"))


@main_bp.route("/reactivate")
@login_required
def reactivate():
    """Show reactivation page."""
    eligible_for_trial = False  # No second trials
    return render_template(
        "reactivate.html",
        eligible_for_trial=eligible_for_trial,
    )


@main_bp.route("/reactivate/confirm", methods=["POST"])
@login_required
def reactivate_account():
    """Process reactivation — without Stripe, just updates tier."""
    tier    = request.form.get("tier",    "explorer")
    billing = request.form.get("billing", "monthly")

    if tier not in ("explorer", "traveller"):
        flash("Invalid plan selected.", "danger")
        return redirect(url_for("main.reactivate"))

    current_user.upgrade(tier, billing)
    current_user.is_active = True
    db.session.commit()

    flash(
        f"Welcome back! Your {current_user.tier_config()['name']} "
        f"plan is now active.",
        "success"
    )
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------------------------------
# Subscription & Upgrade
# ---------------------------------------------------------------------------

@main_bp.route("/upgrade")
@login_required
def upgrade():
    return render_template(
        "upgrade.html",
        tiers        = TIERS,
        current_tier = current_user.subscription_tier,
        days_left    = current_user.trial_days_remaining(),
    )


@main_bp.route("/upgrade/skip-trial", methods=["POST"])
@login_required
def skip_trial():
    tier = request.form.get("tier", "explorer")
    if tier not in ("explorer", "traveller"):
        flash("Invalid tier selected.", "danger")
        return redirect(url_for("main.upgrade"))
    current_user.skip_trial(tier)
    db.session.commit()
    flash(
        f"Welcome to {current_user.tier_config()['name']}! "
        f"Your subscription is now active.",
        "success"
    )
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------------------------------
# Admin Data Scrub
# ---------------------------------------------------------------------------

@main_bp.route("/admin/send_weekly_summary", methods=["POST"])
@login_required
def admin_send_weekly_summary():
    """Admin trigger to send weekly summary immediately for testing."""
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    from app.monitor import send_weekly_summaries
    from flask import current_app
    send_weekly_summaries(current_app._get_current_object())
    flash("Weekly summary emails sent.", "success")
    return redirect(url_for("main.admin"))


@main_bp.route("/admin/scrub", methods=["POST"])
@login_required
def admin_scrub():
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))

    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=180)

    # Orphaned alert logs
    orphaned_alerts = AlertLog.query.filter(
        AlertLog.user_route_id.notin_(
            db.session.query(UserRoute.id)
        )
    ).count()
    AlertLog.query.filter(
        AlertLog.user_route_id.notin_(
            db.session.query(UserRoute.id)
        )
    ).delete(synchronize_session=False)

    # Aged price history
    aged_ph = PriceHistory.query.filter(
        PriceHistory.checked_at < cutoff
    ).count()
    PriceHistory.query.filter(
        PriceHistory.checked_at < cutoff
    ).delete(synchronize_session=False)

    # Aged market summary
    aged_ms = MarketSummary.query.filter(
        MarketSummary.checked_at < cutoff
    ).count()
    MarketSummary.query.filter(
        MarketSummary.checked_at < cutoff
    ).delete(synchronize_session=False)

    db.session.commit()
    flash(
        f"Scrub complete — {orphaned_alerts} orphaned alerts, "
        f"{aged_ph} price records, {aged_ms} market summaries removed.",
        "success"
    )
    return redirect(url_for("main.admin"))


# ---------------------------------------------------------------------------
# RTW
# ---------------------------------------------------------------------------

@main_bp.route("/rtw")
@login_required
def rtw_list():
    itineraries = RTWItinerary.query.filter_by(
        user_id=current_user.id
    ).order_by(RTWItinerary.created_at.desc()).all()
    currency = current_user.preferred_currency
    return render_template("rtw_list.html",
                           itineraries=itineraries,
                           currency=currency,
                           convert=convert,
                           format_price=format_price)


@main_bp.route("/rtw/add", methods=["GET", "POST"])
@login_required
def rtw_add():
    if not current_user.can_add_rtw():
        tier  = current_user.tier_config()
        flash(
            f"You have reached the {tier['max_rtw']}-itinerary limit "
            f"on your {tier['name']} plan.",
            "warning"
        )
        return redirect(url_for("main.upgrade"))

    if request.method == "POST":
        name      = request.form.get("name", "").strip()
        threshold = float(request.form.get(
            "threshold_usd",
            current_user.threshold_international or 600
        ))

        if not name:
            flash("Please give your itinerary a name.", "danger")
            return render_template("rtw_add.html")

        legs = []
        i    = 1
        while True:
            origin = request.form.get(f"leg_origin_{i}",      "").strip().upper()
            dest   = request.form.get(f"leg_destination_{i}", "").strip().upper()
            date   = request.form.get(f"leg_date_{i}",        "").strip()
            cabin  = request.form.get(f"leg_cabin_{i}",       "economy")
            adults = int(request.form.get(f"leg_adults_{i}",  1))
            if not origin or not dest or not date:
                break
            surface = request.form.get(f"leg_surface_{i}") == "on"
            legs.append({
                "order": i, "origin": origin, "destination": dest,
                "date": date, "cabin": cabin, "adults": adults,
                "surface_segment": surface,
            })
            i += 1

        if len(legs) < 2:
            flash("An RTW itinerary needs at least 2 legs.", "danger")
            return render_template("rtw_add.html")

        from app.models import check_leg_connection
        for idx in range(len(legs) - 1):
            prev_dest   = legs[idx]["destination"]
            next_origin = legs[idx + 1]["origin"]
            connected, is_same_city, needs_warning = check_leg_connection(
                prev_dest, next_origin
            )
            if needs_warning and not legs[idx + 1].get("surface_segment"):
                flash(
                    f"Leg {idx + 2} departs from {next_origin} but "
                    f"Leg {idx + 1} arrives at {prev_dest}. "
                    f"If travelling between these by ground, "
                    f"tick the surface segment box on Leg {idx + 2}.",
                    "warning"
                )
                return render_template("rtw_add.html")

        itinerary = RTWItinerary(
            user_id=current_user.id,
            name=name,
            threshold_usd=threshold,
        )
        db.session.add(itinerary)
        db.session.flush()

        for leg in legs:
            db.session.add(RTWLeg(
                itinerary_id       = itinerary.id,
                leg_order          = leg["order"],
                origin             = leg["origin"],
                destination        = leg["destination"],
                departure_date     = leg["date"],
                cabin_class        = leg["cabin"],
                adults             = leg["adults"],
                is_surface_segment = leg.get("surface_segment", False),
            ))

        db.session.commit()
        flash(
            f"RTW itinerary '{name}' created with {len(legs)} legs.",
            "success"
        )
        return redirect(url_for("main.rtw_list"))

    return render_template("rtw_add.html")


@main_bp.route("/rtw/<int:itinerary_id>")
@login_required
def rtw_detail(itinerary_id):
    itinerary = RTWItinerary.query.filter_by(
        id=itinerary_id, user_id=current_user.id
    ).first_or_404()
    currency = current_user.preferred_currency
    return render_template("rtw_detail.html",
                           itinerary=itinerary,
                           currency=currency,
                           convert=convert,
                           format_price=format_price)


@main_bp.route("/rtw/<int:itinerary_id>/toggle", methods=["POST"])
@login_required
def rtw_toggle(itinerary_id):
    itinerary = RTWItinerary.query.filter_by(
        id=itinerary_id, user_id=current_user.id
    ).first_or_404()
    itinerary.is_active = not itinerary.is_active
    db.session.commit()
    status = "resumed" if itinerary.is_active else "paused"
    flash(f"Itinerary '{itinerary.name}' {status}.", "info")
    return redirect(url_for("main.rtw_list"))


@main_bp.route("/rtw/<int:itinerary_id>/delete", methods=["POST"])
@login_required
def rtw_delete(itinerary_id):
    itinerary = RTWItinerary.query.filter_by(
        id=itinerary_id, user_id=current_user.id
    ).first_or_404()
    name      = itinerary.name
    leg_count = RTWLeg.query.filter_by(
        itinerary_id=itinerary.id
    ).count()
    RTWLeg.query.filter_by(itinerary_id=itinerary.id).delete()
    db.session.delete(itinerary)
    db.session.commit()
    flash(
        f"Itinerary '{name}' deleted — {leg_count} legs removed.",
        "info"
    )
    return redirect(url_for("main.rtw_list"))


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@main_bp.route("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    from app.models import User, AppConfig
    users         = User.query.order_by(User.created_at.desc()).all()
    global_routes = GlobalRoute.query.order_by(
        GlobalRoute.created_at.desc()
    ).all()
    user_routes   = UserRoute.query.order_by(
        UserRoute.created_at.desc()
    ).all()
    alert_count   = AlertLog.query.count()
    active_gr     = GlobalRoute.query.filter_by(is_active=True).count()
    app_config    = {r.key: r.value for r in AppConfig.query.all()}
    return render_template(
        "admin.html",
        users         = users,
        global_routes = global_routes,
        user_routes   = user_routes,
        alert_count   = alert_count,
        active_gr     = active_gr,
        app_config    = app_config,
    )


@main_bp.route("/admin/config", methods=["POST"])
@login_required
def admin_save_config():
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    from app.models import AppConfig
    params = {
        "time_value_aud_per_hour": request.form.get("time_value_aud_per_hour", ""),
        "stop_penalty_aud":        request.form.get("stop_penalty_aud", ""),
    }
    for key, raw in params.items():
        try:
            value = str(float(raw))
        except ValueError:
            flash(f"Invalid value for {key}.", "danger")
            return redirect(url_for("main.admin"))
        row = AppConfig.query.filter_by(key=key).first()
        if row:
            row.value = value
        else:
            db.session.add(AppConfig(key=key, value=value))
    db.session.commit()
    flash("Optimization parameters saved.", "success")
    return redirect(url_for("main.admin"))


@main_bp.route("/admin/reactivate_invited/<int:user_id>", methods=["POST"])
@login_required
def admin_reactivate_invited(user_id):
    """Reactivate a deactivated invited account back to free Explorer."""
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    from app.models import User
    user = User.query.get_or_404(user_id)
    user.activate_as_invited()
    user.is_active = True
    db.session.commit()
    flash(
        f"{user.email} reactivated as complimentary Explorer.",
        "success"
    )
    return redirect(url_for("main.admin"))


@main_bp.route("/admin/toggle_user/<int:user_id>", methods=["POST"])
@login_required
def admin_toggle_user(user_id):
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    from app.models import User
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot disable your own account.", "warning")
        return redirect(url_for("main.admin"))
    user.is_active = not user.is_active
    if not user.is_active:
        user.subscription_status = "disabled"
    else:
        user.subscription_status = "active"
    db.session.commit()
    status = "enabled" if user.is_active else "disabled"
    flash(f"User {user.email} {status}.", "info")
    return redirect(url_for("main.admin"))


@main_bp.route("/admin/make_admin/<int:user_id>", methods=["POST"])
@login_required
def admin_make_admin(user_id):
    """Promote a user to admin — max 2 admins enforced."""
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    from app.models import User
    admin_count = User.query.filter_by(is_admin=True).count()
    if admin_count >= 2:
        flash(
            "Maximum of 2 admin accounts allowed. "
            "Remove an existing admin first.",
            "danger"
        )
        return redirect(url_for("main.admin"))
    user = User.query.get_or_404(user_id)
    user.is_admin    = True
    user.account_type = "admin"
    db.session.commit()
    flash(f"{user.email} promoted to admin.", "success")
    return redirect(url_for("main.admin"))


@main_bp.route("/admin/remove_admin/<int:user_id>", methods=["POST"])
@login_required
def admin_remove_admin(user_id):
    """Remove admin rights from a user."""
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    from app.models import User
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot remove your own admin rights.", "warning")
        return redirect(url_for("main.admin"))
    user.is_admin     = False
    user.account_type = "self_registered"
    db.session.commit()
    flash(f"Admin rights removed from {user.email}.", "info")
    return redirect(url_for("main.admin"))


@main_bp.route("/admin/reset_password/<int:user_id>", methods=["POST"])
@login_required
def admin_reset_password(user_id):
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    from app import bcrypt
    from app.models import User
    user   = User.query.get_or_404(user_id)
    new_pw = request.form.get("new_password", "").strip()
    if len(new_pw) < 8:
        flash("Password must be at least 8 characters.", "danger")
        return redirect(url_for("main.admin"))
    user.password = bcrypt.generate_password_hash(new_pw).decode("utf-8")
    db.session.commit()
    flash(f"Password reset for {user.email}.", "success")
    return redirect(url_for("main.admin"))


@main_bp.route("/admin/airports")
@login_required
def admin_airports():
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    airports = Airport.query.order_by(
        Airport.region, Airport.country, Airport.city
    ).all()
    return render_template(
        "admin_airports.html",
        airports=airports,
        regions=[
            "Australia / Oceania", "Asia", "Middle East",
            "Europe", "Africa", "North America", "South America",
        ]
    )


@main_bp.route("/admin/airports/add", methods=["POST"])
@login_required
def admin_add_airport():
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    iata    = request.form.get("iata_code", "").strip().upper()
    name    = request.form.get("name",      "").strip()
    city    = request.form.get("city",      "").strip()
    country = request.form.get("country",   "").strip()
    region  = request.form.get("region",    "").strip()
    if not all([iata, name, city, country, region]):
        flash("All fields are required.", "danger")
        return redirect(url_for("main.admin_airports"))
    if len(iata) != 3:
        flash("IATA code must be 3 letters.", "danger")
        return redirect(url_for("main.admin_airports"))
    if Airport.query.filter_by(iata_code=iata).first():
        flash(f"Airport {iata} already exists.", "warning")
        return redirect(url_for("main.admin_airports"))
    db.session.add(Airport(
        iata_code=iata, name=name, city=city,
        country=country, region=region
    ))
    db.session.commit()
    flash(f"Airport {iata} — {city} added.", "success")
    return redirect(url_for("main.admin_airports"))


@main_bp.route("/admin/airports/<int:airport_id>/toggle", methods=["POST"])
@login_required
def admin_toggle_airport(airport_id):
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    airport = Airport.query.get_or_404(airport_id)
    airport.is_active = not airport.is_active
    db.session.commit()
    status = "enabled" if airport.is_active else "disabled"
    flash(f"{airport.iata_code} — {airport.city} {status}.", "info")
    return redirect(url_for("main.admin_airports"))


@main_bp.route("/admin/invites")
@login_required
def admin_invites():
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    from app.models import Invite
    invites = Invite.query.order_by(Invite.created_at.desc()).all()
    return render_template("admin_invites.html", invites=invites)


@main_bp.route("/admin/invites/create", methods=["POST"])
@login_required
def admin_create_invite():
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    from app.models import Invite
    from app.email import send_invite_email
    email     = request.form.get("email", "").strip().lower() or None
    days      = int(request.form.get("days_valid", 7))
    send_mail = request.form.get("send_email") == "on"
    invite    = Invite.generate(current_user.id, email=email, days_valid=days)
    db.session.add(invite)
    db.session.commit()
    invite_url = url_for(
        "auth.register_with_token", token=invite.token, _external=True
    )
    if send_mail and email:
        send_invite_email(email, invite_url, days, current_user.name)
        flash(f"Invite created and sent to {email}.", "success")
    else:
        flash(f"Invite created. Link: {invite_url}", "success")
    return redirect(url_for("main.admin_invites"))


@main_bp.route("/admin/invites/<int:invite_id>/cancel", methods=["POST"])
@login_required
def admin_cancel_invite(invite_id):
    if not current_user.is_admin:
        flash("Permission denied.", "danger")
        return redirect(url_for("main.dashboard"))
    from app.models import Invite
    invite = Invite.query.get_or_404(invite_id)
    if invite.used_at:
        flash("Cannot cancel a used invite.", "warning")
    else:
        invite.is_active = False
        db.session.commit()
        flash("Invite cancelled.", "info")
    return redirect(url_for("main.admin_invites"))
