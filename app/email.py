from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from config import Config
import logging

log = logging.getLogger(__name__)

APP_NAME = Config.APP_NAME


# Major airlines available for membership selection on profile page
MAJOR_AIRLINES = [
    # Australian / Oceania
    "Qantas",
    "Jetstar",
    "Virgin Australia",
    "Rex Airlines",
    "Air New Zealand",
    # Asia
    "Singapore Airlines",
    "Cathay Pacific",
    "Japan Airlines",
    "ANA",
    "Korean Air",
    "Asiana Airlines",
    "Thai Airways",
    "Malaysia Airlines",
    "Garuda Indonesia",
    "Philippine Airlines",
    "Vietnam Airlines",
    "Air Asia",
    "China Southern",
    "China Eastern",
    "Air China",
    "Hainan Airlines",
    # Middle East
    "Emirates",
    "Qatar Airways",
    "Etihad",
    "Turkish Airlines",
    "flydubai",
    # Europe
    "British Airways",
    "Lufthansa",
    "Air France",
    "KLM",
    "Swiss",
    "Austrian Airlines",
    "Scandinavian Airlines",
    "Finnair",
    "Iberia",
    "TAP Air Portugal",
    "Alitalia",
    "Ryanair",
    "easyJet",
    # North America
    "United Airlines",
    "American Airlines",
    "Delta",
    "Air Canada",
    "WestJet",
    "Southwest Airlines",
    "Alaska Airlines",
    "JetBlue",
    # Africa / Other
    "South African Airways",
    "Kenya Airways",
    "Ethiopian Airlines",
    "EgyptAir",
]


# Airline website lookup — used to generate direct booking links in alerts
AIRLINE_URLS = {
    "Qantas":                "https://www.qantas.com",
    "Emirates":              "https://www.emirates.com",
    "Singapore Airlines":    "https://www.singaporeair.com",
    "British Airways":       "https://www.britishairways.com",
    "Cathay Pacific":        "https://www.cathaypacific.com",
    "Air New Zealand":       "https://www.airnewzealand.com.au",
    "Jetstar":               "https://www.jetstar.com",
    "Virgin Australia":      "https://www.virginaustralia.com",
    "Thai Airways":          "https://www.thaiairways.com",
    "Malaysia Airlines":     "https://www.malaysiaairlines.com",
    "Air Asia":              "https://www.airasia.com",
    "Korean Air":            "https://www.koreanair.com",
    "Japan Airlines":        "https://www.jal.com",
    "ANA":                   "https://www.ana.co.jp/en",
    "China Southern":        "https://www.csair.com/en",
    "Air China":             "https://www.airchina.com.au",
    "Etihad":                "https://www.etihad.com",
    "Qatar Airways":         "https://www.qatarairways.com",
    "Turkish Airlines":      "https://www.turkishairlines.com",
    "Lufthansa":             "https://www.lufthansa.com",
    "Air France":            "https://www.airfrance.com.au",
    "KLM":                   "https://www.klm.com",
    "Swiss":                 "https://www.swiss.com",
    "United Airlines":       "https://www.united.com",
    "American Airlines":     "https://www.aa.com",
    "Delta":                 "https://www.delta.com",
    "Air Canada":            "https://www.aircanada.com",
    "South African Airways": "https://www.flysaa.com",
    "Kenya Airways":         "https://www.kenya-airways.com",
    "Ethiopian Airlines":    "https://www.ethiopianairlines.com",
}


def google_flights_url(origin, destination, departure_date, return_date=None):
    """Generate a Google Flights deep link for a route."""
    base = "https://www.google.com/flights"
    params = f"?q=Flights+from+{origin}+to+{destination}"
    return base + params


def airline_url(airline_name):
    """Return the direct booking URL for a known airline, or None."""
    if not airline_name:
        return None
    for name, url in AIRLINE_URLS.items():
        if name.lower() in airline_name.lower():
            return url
    return None


def booking_buttons(origin, destination, departure_date,
                    return_date, airline_name):
    """Generate HTML booking buttons for an alert email."""
    gf_url      = google_flights_url(origin, destination, departure_date)
    airline_link = airline_url(airline_name)

    buttons = f"""
    <div style="text-align:center;margin:30px 0">
      <a href="{gf_url}"
         style="background:#1a73e8;color:white;padding:12px 24px;
                text-decoration:none;border-radius:6px;font-weight:bold;
                margin:4px;display:inline-block">
        Search Google Flights →
      </a>"""

    if airline_link:
        buttons += f"""
      <a href="{airline_link}"
         style="background:#188038;color:white;padding:12px 24px;
                text-decoration:none;border-radius:6px;font-weight:bold;
                margin:4px;display:inline-block">
        Go to {airline_name} →
      </a>"""

    buttons += """
    </div>"""
    return buttons


def _send(to_email, subject, html):
    """Internal helper — sends a single email via SendGrid."""
    if not Config.SENDGRID_API_KEY:
        log.warning("SENDGRID_API_KEY not set — email not sent to %s", to_email)
        return False
    message = Mail(
        from_email   = Config.ALERT_FROM_EMAIL,
        to_emails    = to_email,
        subject      = subject,
        html_content = html,
    )
    try:
        sg = SendGridAPIClient(Config.SENDGRID_API_KEY)
        sg.send(message)
        log.info("Email sent to %s — %s", to_email, subject)
        return True
    except Exception as e:
        log.error("SendGrid error for %s: %s", to_email, e)
        return False


def _base_table(route, offer_price, currency, airline,
                baseline_price, drop, extra_rows=""):
    """Shared HTML price table used in both alert templates."""
    trip_type = (
        f"Round trip — return {route.return_date}"
        if route.return_date else "One-way"
    )
    return f"""
    <table style="width:100%;border-collapse:collapse;margin:20px 0">
      <tr style="background:#f8f9fa">
        <td style="padding:10px;border:1px solid #dee2e6;width:40%"><b>Route</b></td>
        <td style="padding:10px;border:1px solid #dee2e6">
          {route.origin} → {route.destination}
        </td>
      </tr>
      <tr>
        <td style="padding:10px;border:1px solid #dee2e6"><b>Trip type</b></td>
        <td style="padding:10px;border:1px solid #dee2e6">{trip_type}</td>
      </tr>
      <tr style="background:#f8f9fa">
        <td style="padding:10px;border:1px solid #dee2e6"><b>Departure</b></td>
        <td style="padding:10px;border:1px solid #dee2e6">{route.departure_date}</td>
      </tr>
      <tr>
        <td style="padding:10px;border:1px solid #dee2e6"><b>Airline</b></td>
        <td style="padding:10px;border:1px solid #dee2e6">
          {airline or "See booking site"}
        </td>
      </tr>
      <tr style="background:#f8f9fa">
        <td style="padding:10px;border:1px solid #dee2e6"><b>Previous price</b></td>
        <td style="padding:10px;border:1px solid #dee2e6">
          {currency} {baseline_price:,.2f}
        </td>
      </tr>
      <tr>
        <td style="padding:10px;border:1px solid #dee2e6"><b>Current price</b></td>
        <td style="padding:10px;border:1px solid #dee2e6;color:#188038">
          <b>{currency} {offer_price:,.2f}</b>
        </td>
      </tr>
      <tr style="background:#e6f4ea">
        <td style="padding:10px;border:1px solid #dee2e6"><b>You save</b></td>
        <td style="padding:10px;border:1px solid #dee2e6;color:#188038">
          <b>↓ {currency} {drop:,.2f}</b>
        </td>
      </tr>
      {extra_rows}
    </table>
    """


def _footer():
    return f"""
    <div style="text-align:center;margin:30px 0">
      <a href="https://www.google.com/flights"
         style="background:#1a73e8;color:white;padding:12px 30px;
                text-decoration:none;border-radius:6px;font-weight:bold">
        Search on Google Flights →
      </a>
    </div>
    <p style="color:#999;font-size:12px;margin-top:30px">
      Prices are indicative and sourced from the Duffel API.
      Always confirm the final price before booking.<br><br>
      Log in to {APP_NAME} to pause or manage your alerts.
    </p>
    """


def _top_offers_table(top_offers, currency, user=None):
    """
    Generate HTML table of top offers for alert emails.
    Member airlines are highlighted with a star badge.
    """
    if not top_offers:
        return ""

    memberships = user.get_memberships() if user else []
    rows        = ""

    for i, offer in enumerate(top_offers):
        bg        = "#f8f9fa" if i % 2 == 0 else "#ffffff"
        airline   = offer.get("airline") or "Unknown"
        price     = offer.get("price", 0)
        stops     = offer.get("stops")
        stop_str  = ("Direct" if stops == 0
                     else f"{stops} stop{'s' if stops and stops > 1 else ''}"
                     if stops is not None else "—")

        is_cheapest = i == 0
        is_member   = user and user.is_member(airline)

        cheapest_badge = "★ " if is_cheapest else ""
        member_badge   = (
            ' <span style="background:#1a73e8;color:white;'
            'padding:1px 6px;border-radius:3px;font-size:11px">'
            'Member</span>'
            if is_member else ""
        )

        price_color = "#188038" if is_cheapest else (
            "#1a73e8" if is_member else "inherit"
        )

        rows += f"""
        <tr style="background:{bg}">
          <td style="padding:8px;border:1px solid #dee2e6">
            {cheapest_badge}{airline}{member_badge}
          </td>
          <td style="padding:8px;border:1px solid #dee2e6">{stop_str}</td>
          <td style="padding:8px;border:1px solid #dee2e6;color:{price_color}">
            <b>{currency} {price:,.2f}</b>
          </td>
        </tr>"""

    has_members = any(user and user.is_member(o.get("airline", ""))
                      for o in top_offers) if user else False
    legend = '<p style="font-size:12px;color:#666">★ Cheapest option'
    if has_members:
        legend += (' &nbsp;|&nbsp; '
                   '<span style="background:#1a73e8;color:white;'
                   'padding:1px 6px;border-radius:3px;font-size:11px">'
                   'Member</span> Your airline')
    legend += '</p>'

    return f"""
    <h4 style="margin-top:20px">Top options right now</h4>
    <table style="width:100%;border-collapse:collapse;margin:8px 0">
      <thead>
        <tr style="background:#1a73e8;color:white">
          <th style="padding:8px;border:1px solid #1a73e8">Airline</th>
          <th style="padding:8px;border:1px solid #1a73e8">Stops</th>
          <th style="padding:8px;border:1px solid #1a73e8">Price</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    {legend}"""


def send_sudden_sale_alert(user, route, baseline_price, current_price,
                           drop, currency, airline,
                           historic_median=None, top_offers=None):
    """
    Mode 1 — Sudden Sale alert.
    Fires when price drops by more than the user's threshold
    from the baseline but is NOT a historic low.
    """
    subject = (
        f"🔥 Flash Sale: {route.origin}→{route.destination} "
        f"down {currency} {drop:,.2f}!"
    )

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;
                 max-width:600px;margin:0 auto">
      <div style="background:#e8710a;padding:24px;
                  border-radius:12px 12px 0 0">
        <h2 style="color:white;margin:0">🔥 Flash Sale Detected!</h2>
        <p style="color:#ffe8cc;margin:8px 0 0">
          A sudden price drop on one of your monitored routes
        </p>
      </div>
      <div style="background:white;padding:24px;
                  border:1px solid #e0e0e0">
        <p>Hi {user.name},</p>
        <p>The price on one of your watched routes has dropped
           significantly since we last checked.</p>
        {_base_table(route, current_price, currency, airline,
                     baseline_price, drop)}
        <p style="color:#e8710a;font-weight:bold">
          ⚡ This looks like a short-term sale — prices like this
          don't always last long.
        </p>
        {f'<p><strong>Market median price:</strong> {currency} {historic_median:,.2f} — current price is {currency} {(historic_median - current_price):,.2f} below the market median.</p>' if historic_median else ''}
        {_top_offers_table(top_offers or [], currency, user)}
        {booking_buttons(route.origin, route.destination,
                        route.departure_date, route.return_date, airline)}
        <p style="color:#999;font-size:12px;margin-top:20px">
          Prices are indicative and sourced from the Duffel API.
          Always confirm the final price before booking.
        </p>
      </div>
      <div style="background:#f8f9fa;padding:16px;
                  border-radius:0 0 12px 12px;
                  text-align:center;color:#999;font-size:12px">
        {APP_NAME} — 🔥 Flash Sale Alert
      </div>
    </body>
    </html>
    """

    return _send(user.get_alert_email(), subject, html)


def send_historic_low_alert(user, route, baseline_price, current_price,
                            drop, currency, airline, historic_avg,
                            historic_median=None, top_offers=None):
    """
    Mode 2 — Historic Low alert.
    Fires when price is below the 6-month average low.
    This IS a great deal by definition — threshold is irrelevant.
    Includes sudden sale context if the drop also exceeds threshold.
    """
    saving_vs_avg = historic_avg - current_price

    subject = (
        f"🔥📉 Historic Low: {route.origin}→{route.destination} "
        f"— best price in 6 months!"
    )

    extra_rows = f"""
      <tr style="background:#e6f4ea">
        <td style="padding:10px;border:1px solid #dee2e6">
          <b>6-month average low</b>
        </td>
        <td style="padding:10px;border:1px solid #dee2e6;color:#188038">
          <b>{currency} {historic_avg:,.2f}</b>
        </td>
      </tr>
      <tr>
        <td style="padding:10px;border:1px solid #dee2e6">
          <b>Saving vs average low</b>
        </td>
        <td style="padding:10px;border:1px solid #dee2e6;color:#188038">
          <b>↓ {currency} {saving_vs_avg:,.2f} below typical low</b>
        </td>
      </tr>
    """

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;
                 max-width:600px;margin:0 auto">
      <div style="background:linear-gradient(135deg,#e8710a,#1a73e8);
                  padding:24px;border-radius:12px 12px 0 0">
        <h2 style="color:white;margin:0">🔥📉 Historic Low Price!</h2>
        <p style="color:#e8f0fe;margin:8px 0 0">
          This is the cheapest this flight has been in 6 months
        </p>
      </div>
      <div style="background:white;padding:24px;
                  border:1px solid #e0e0e0">
        <p>Hi {user.name},</p>
        <p>This is not just a price drop — this price is
           <strong>below the 6-month average low</strong> for this route.
           This is genuinely one of the cheapest prices we have recorded.</p>
        {_base_table(route, current_price, currency, airline,
                     baseline_price, drop, extra_rows)}
        <p style="color:#188038;font-weight:bold">
          📉 Our data shows this price is {currency} {saving_vs_avg:,.2f}
          below what we typically see as the lowest price for this route.
          This is an exceptional deal.
        </p>
        {_top_offers_table(top_offers or [], currency, user)}
        {booking_buttons(route.origin, route.destination,
                        route.departure_date, route.return_date, airline)}
        <p style="color:#999;font-size:12px;margin-top:20px">
          Prices are indicative and sourced from the Duffel API.
          Always confirm the final price before booking.
        </p>
      </div>
      <div style="background:#f8f9fa;padding:16px;
                  border-radius:0 0 12px 12px;
                  text-align:center;color:#999;font-size:12px">
        {APP_NAME} — 🔥📉 Historic Low Alert
      </div>
    </body>
    </html>
    """

    return _send(user.get_alert_email(), subject, html)


def send_reset_email(user, reset_url):
    """Send a password reset link to the user."""
    subject = f"{APP_NAME} — Password Reset Request"
    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;
                 max-width:600px;margin:0 auto">
      <div style="background:#1a73e8;padding:24px;
                  border-radius:12px 12px 0 0">
        <h2 style="color:white;margin:0">✈️ {APP_NAME}</h2>
      </div>
      <div style="background:white;padding:24px;border:1px solid #e0e0e0">
        <p>Hi {user.name},</p>
        <p>We received a request to reset your password.
           Click the button below to choose a new one.</p>
        <div style="text-align:center;margin:30px 0">
          <a href="{reset_url}"
             style="background:#1a73e8;color:white;padding:12px 30px;
                    text-decoration:none;border-radius:6px;
                    font-weight:bold">
            Reset My Password →
          </a>
        </div>
        <p>This link expires in <strong>1 hour</strong>.</p>
        <p>If you did not request a password reset you can safely
           ignore this email.</p>
        <p style="color:#999;font-size:12px;margin-top:30px">
          If the button above doesn't work, copy and paste this link:<br>
          <a href="{reset_url}">{reset_url}</a>
        </p>
      </div>
    </body>
    </html>
    """
    return _send(user.email, subject, html)


def send_invite_email(to_email, invite_url, days_valid, invited_by):
    """Send an invitation email with the registration link."""
    subject = f"You've been invited to {APP_NAME}"
    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;
                 max-width:600px;margin:0 auto">
      <div style="background:#1a73e8;padding:24px;
                  border-radius:12px 12px 0 0">
        <h2 style="color:white;margin:0">✈️ {APP_NAME}</h2>
      </div>
      <div style="background:white;padding:24px;border:1px solid #e0e0e0">
        <p>Hi there,</p>
        <p><strong>{invited_by}</strong> has invited you to join
           {APP_NAME} — a private tool that tracks flight prices
           and alerts you when they drop.</p>
        <div style="text-align:center;margin:30px 0">
          <a href="{invite_url}"
             style="background:#1a73e8;color:white;padding:14px 36px;
                    text-decoration:none;border-radius:6px;
                    font-weight:bold;font-size:16px">
            Accept Invitation →
          </a>
        </div>
        <p>This invitation expires in <strong>{days_valid} days</strong>
           and can only be used once.</p>
        <p>If you were not expecting this invitation you can safely
           ignore this email.</p>
        <p style="color:#999;font-size:12px;margin-top:30px">
          If the button above does not work, copy and paste this link:<br>
          <a href="{invite_url}">{invite_url}</a>
        </p>
      </div>
    </body>
    </html>
    """
    return _send(to_email, subject, html)


def send_rtw_alert(user, itinerary, baseline, current_total,
                   drop, currency, legs):
    """
    RTW price drop alert — shows total price and per-leg breakdown.
    """
    subject = (
        f"✈️ RTW Price Drop: {itinerary.name} "
        f"down {currency} {drop:,.2f}!"
    )

    # Build legs table rows
    legs_rows = ""
    for leg in legs:
        legs_rows += f"""
        <tr>
          <td style="padding:8px;border:1px solid #dee2e6;text-align:center">
            {leg['order']}
          </td>
          <td style="padding:8px;border:1px solid #dee2e6">
            {leg['origin']} → {leg['destination']}
          </td>
          <td style="padding:8px;border:1px solid #dee2e6">{leg['date']}</td>
          <td style="padding:8px;border:1px solid #dee2e6">{leg['airline']}</td>
          <td style="padding:8px;border:1px solid #dee2e6;color:#188038">
            <b>{leg['currency']} {leg['price']:,.2f}</b>
          </td>
        </tr>"""

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;
                 max-width:600px;margin:0 auto">
      <div style="background:linear-gradient(135deg,#1a73e8,#0d47a1);
                  padding:24px;border-radius:12px 12px 0 0">
        <h2 style="color:white;margin:0">✈️ RTW Price Drop!</h2>
        <p style="color:#cce0ff;margin:8px 0 0">
          {itinerary.name}
        </p>
      </div>
      <div style="background:white;padding:24px;border:1px solid #e0e0e0">
        <p>Hi {user.name},</p>
        <p>The combined price of your Around The World itinerary has dropped
           significantly.</p>

        <table style="width:100%;border-collapse:collapse;margin:16px 0">
          <tr style="background:#f8f9fa">
            <td style="padding:10px;border:1px solid #dee2e6"><b>Previous total</b></td>
            <td style="padding:10px;border:1px solid #dee2e6">
              {currency} {baseline:,.2f}
            </td>
          </tr>
          <tr>
            <td style="padding:10px;border:1px solid #dee2e6"><b>Current total</b></td>
            <td style="padding:10px;border:1px solid #dee2e6;color:#188038">
              <b>{currency} {current_total:,.2f}</b>
            </td>
          </tr>
          <tr style="background:#e6f4ea">
            <td style="padding:10px;border:1px solid #dee2e6"><b>You save</b></td>
            <td style="padding:10px;border:1px solid #dee2e6;color:#188038">
              <b>↓ {currency} {drop:,.2f}</b>
            </td>
          </tr>
        </table>

        <h4 style="margin-top:24px">Per-leg breakdown</h4>
        <table style="width:100%;border-collapse:collapse;margin:12px 0">
          <thead>
            <tr style="background:#1a73e8;color:white">
              <th style="padding:8px;border:1px solid #1a73e8">#</th>
              <th style="padding:8px;border:1px solid #1a73e8">Route</th>
              <th style="padding:8px;border:1px solid #1a73e8">Date</th>
              <th style="padding:8px;border:1px solid #1a73e8">Airline</th>
              <th style="padding:8px;border:1px solid #1a73e8">Price</th>
            </tr>
          </thead>
          <tbody>
            {legs_rows}
          </tbody>
        </table>

        <div style="text-align:center;margin:30px 0">
          <a href="https://www.google.com/flights"
             style="background:#1a73e8;color:white;padding:12px 30px;
                    text-decoration:none;border-radius:6px;font-weight:bold">
            Search on Google Flights →
          </a>
        </div>
        <p style="color:#999;font-size:12px;margin-top:20px">
          Prices are indicative and sourced from the Duffel API.
          Each leg is priced independently — confirm all legs before booking.
        </p>
      </div>
      <div style="background:#f8f9fa;padding:16px;
                  border-radius:0 0 12px 12px;
                  text-align:center;color:#999;font-size:12px">
        {APP_NAME} — ✈️ RTW Alert
      </div>
    </body>
    </html>
    """

    return _send(user.get_alert_email(), subject, html)


def send_nearby_alert(user, route, nearby_iata, nearby_city,
                      nearby_price, nearby_airline, entered_price,
                      entered_airline, saving, currency, top_offers=None):
    """
    Nearby airport alert — a cheaper flight was found departing
    from a nearby airport within 100km of the user's chosen origin.
    """
    subject = (
        f"✈️ Cheaper from {nearby_city} ({nearby_iata}): "
        f"{nearby_iata}→{route.destination} "
        f"saves {currency} {saving:,.2f}!"
    )

    trip_type = (
        f"Round trip (return {route.return_date})"
        if route.return_date else "One-way"
    )

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;
                 max-width:600px;margin:0 auto">
      <div style="background:#188038;padding:24px;
                  border-radius:12px 12px 0 0">
        <h2 style="color:white;margin:0">
          ✈️ Cheaper Flight Nearby!
        </h2>
        <p style="color:#c8e6c9;margin:8px 0 0">
          A nearby airport has a significantly cheaper fare
        </p>
      </div>
      <div style="background:white;padding:24px;
                  border:1px solid #e0e0e0">
        <p>Hi {user.name},</p>
        <p>We found a cheaper flight departing from
           <strong>{nearby_city} ({nearby_iata})</strong>
           — within 100km of your chosen departure airport
           {route.origin}.</p>

        <table style="width:100%;border-collapse:collapse;margin:16px 0">
          <tr style="background:#f8f9fa">
            <td style="padding:10px;border:1px solid #dee2e6">
              <b>Your route</b>
            </td>
            <td style="padding:10px;border:1px solid #dee2e6">
              {route.origin} → {route.destination}
            </td>
          </tr>
          <tr>
            <td style="padding:10px;border:1px solid #dee2e6">
              <b>Your price</b>
            </td>
            <td style="padding:10px;border:1px solid #dee2e6">
              {currency} {entered_price:,.2f}
              ({entered_airline or "Unknown"})
            </td>
          </tr>
          <tr style="background:#f8f9fa">
            <td style="padding:10px;border:1px solid #dee2e6">
              <b>Nearby route</b>
            </td>
            <td style="padding:10px;border:1px solid #dee2e6">
              {nearby_iata} → {route.destination}
            </td>
          </tr>
          <tr style="background:#e6f4ea">
            <td style="padding:10px;border:1px solid #dee2e6">
              <b>Nearby price</b>
            </td>
            <td style="padding:10px;border:1px solid #dee2e6;
                       color:#188038">
              <b>{currency} {nearby_price:,.2f}
              ({nearby_airline or "Unknown"})</b>
            </td>
          </tr>
          <tr style="background:#e6f4ea">
            <td style="padding:10px;border:1px solid #dee2e6">
              <b>You save</b>
            </td>
            <td style="padding:10px;border:1px solid #dee2e6;
                       color:#188038">
              <b>↓ {currency} {saving:,.2f} by departing from
              {nearby_city}</b>
            </td>
          </tr>
          <tr>
            <td style="padding:10px;border:1px solid #dee2e6">
              <b>Trip type</b>
            </td>
            <td style="padding:10px;border:1px solid #dee2e6">
              {trip_type}
            </td>
          </tr>
          <tr style="background:#f8f9fa">
            <td style="padding:10px;border:1px solid #dee2e6">
              <b>Departure date</b>
            </td>
            <td style="padding:10px;border:1px solid #dee2e6">
              {route.departure_date}
            </td>
          </tr>
        </table>

        {_top_offers_table(top_offers or [], currency, user)}

        {booking_buttons(nearby_iata, route.destination,
                        route.departure_date, route.return_date,
                        nearby_airline)}

        <p style="color:#666;font-size:13px;margin-top:16px">
          <i>Note: travelling from {nearby_city} instead of
          {route.origin} requires getting to {nearby_city} first.
          Factor in any additional travel costs before booking.</i>
        </p>
        <p style="color:#999;font-size:12px;margin-top:16px">
          Prices are indicative and sourced from the Duffel API.
          Always confirm the final price before booking.
        </p>
      </div>
      <div style="background:#f8f9fa;padding:16px;
                  border-radius:0 0 12px 12px;
                  text-align:center;color:#999;font-size:12px">
        {APP_NAME} — ✈️ Nearby Airport Alert
      </div>
    </body>
    </html>
    """

    return _send(user.get_alert_email(), subject, html)


def send_trial_reminder(user, days_remaining):
    """
    Trial reminder email — sent at Day 10 (4 days left)
    and Day 13 (1 day left).
    """
    if days_remaining <= 1:
        urgency    = "expires tomorrow"
        color      = "#d93025"
        action     = "Subscribe now to keep your monitoring active."
    else:
        urgency    = f"expires in {days_remaining} days"
        color      = "#e8710a"
        action     = "Upgrade before your trial ends to avoid interruption."

    subject = f"⏰ Your {APP_NAME} trial {urgency}"

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;
                 max-width:600px;margin:0 auto">
      <div style="background:{color};padding:24px;
                  border-radius:12px 12px 0 0">
        <h2 style="color:white;margin:0">⏰ Trial {urgency.title()}</h2>
      </div>
      <div style="background:white;padding:24px;
                  border:1px solid #e0e0e0">
        <p>Hi {user.name},</p>
        <p>Your {APP_NAME} free trial <strong>{urgency}</strong>.</p>
        <p>{action}</p>

        <table style="width:100%;border-collapse:collapse;margin:20px 0">
          <tr style="background:#1a73e8;color:white">
            <th style="padding:10px;border:1px solid #1a73e8">Plan</th>
            <th style="padding:10px;border:1px solid #1a73e8">Price</th>
            <th style="padding:10px;border:1px solid #1a73e8">Routes</th>
            <th style="padding:10px;border:1px solid #1a73e8">Checks</th>
          </tr>
          <tr>
            <td style="padding:10px;border:1px solid #dee2e6">Explorer</td>
            <td style="padding:10px;border:1px solid #dee2e6">USD $8/mo</td>
            <td style="padding:10px;border:1px solid #dee2e6">5 routes</td>
            <td style="padding:10px;border:1px solid #dee2e6">Every 2 hours</td>
          </tr>
          <tr style="background:#f8f9fa">
            <td style="padding:10px;border:1px solid #dee2e6">
              <strong>Traveller</strong>
            </td>
            <td style="padding:10px;border:1px solid #dee2e6">
              <strong>USD $20/mo</strong>
            </td>
            <td style="padding:10px;border:1px solid #dee2e6">
              <strong>20 routes</strong>
            </td>
            <td style="padding:10px;border:1px solid #dee2e6">
              <strong>Every hour</strong>
            </td>
          </tr>
        </table>

        <div style="text-align:center;margin:30px 0">
          href="https://66.226.145.35/upgrade"
             style="background:#1a73e8;color:white;padding:14px 32px;
                    text-decoration:none;border-radius:6px;
                    font-weight:bold;font-size:16px">
            View Plans & Upgrade →
          </a>
        </div>

        <p style="color:#999;font-size:12px">
          If you choose not to upgrade, your monitoring will pause
          when the trial ends. Your routes and history are saved
          and will resume if you subscribe later.
        </p>
      </div>
      <div style="background:#f8f9fa;padding:16px;
                  border-radius:0 0 12px 12px;
                  text-align:center;color:#999;font-size:12px">
        {APP_NAME} — Trial Reminder
        &nbsp;·&nbsp;
        <a href="https://66.226.145.35/profile"
           style="color:#999">Manage Subscription</a>
      </div>
    </body>
    </html>
    """
    return _send(user.get_alert_email(), subject, html)


def send_weekly_summary(user, summary_data):
    """
    Weekly summary email — sent every Monday morning.
    Basic summary for all tiers, enhanced for Traveller.
    """
    from app.models import TIERS
    is_traveller = user.subscription_tier == "traveller" or user.is_admin

    subject = f"✈️ Your {APP_NAME} Weekly Summary"

    # Build per-route rows
    route_rows = ""
    for r in summary_data["routes"]:
        trend_icon  = "↓" if r["trend"] < 0 else "↑" if r["trend"] > 0 else "→"
        trend_color = "#188038" if r["trend"] < 0 else "#d93025" if r["trend"] > 0 else "#666"
        trend_text  = (f"{trend_icon} {r['currency']} {abs(r['trend']):,.0f}"
                       if r["trend"] != 0 else "→ No change")

        # Threshold recommendation (Traveller only, 30+ days data)
        recommendation = ""
        if is_traveller and r.get("recommendation"):
            rec = r["recommendation"]
            recommendation = f"""
            <tr style="background:#fff8e1">
              <td colspan="4" style="padding:8px 12px;border:1px solid #dee2e6;
                                     font-size:12px;color:#666">
                💡 <em>{rec}</em>
              </td>
            </tr>"""

        # Historic avg low comparison (Traveller only)
        historic_row = ""
        if is_traveller and r.get("historic_avg_low"):
            pct_above = ((r["current_price"] - r["historic_avg_low"])
                         / r["historic_avg_low"] * 100)
            historic_row = f"""
            <tr style="background:#f8f9fa">
              <td colspan="2" style="padding:6px 12px;border:1px solid #dee2e6;
                                     font-size:12px;color:#666">
                Historic avg low: {r['currency']} {r['historic_avg_low']:,.0f}
              </td>
              <td colspan="2" style="padding:6px 12px;border:1px solid #dee2e6;
                                     font-size:12px;color:#666">
                {'↑ ' + str(round(pct_above)) + '% above historic low'
                 if pct_above > 0
                 else '↓ Below historic low — good price!'}
              </td>
            </tr>"""

        # Top carriers (Traveller only)
        carriers_row = ""
        if is_traveller and r.get("top_carriers"):
            carriers = ", ".join(r["top_carriers"][:3])
            carriers_row = f"""
            <tr style="background:#f8f9fa">
              <td colspan="4" style="padding:6px 12px;border:1px solid #dee2e6;
                                     font-size:12px;color:#666">
                Top carriers this week: {carriers}
              </td>
            </tr>"""

        route_rows += f"""
        <tr style="background:#ffffff">
          <td style="padding:10px 12px;border:1px solid #dee2e6;font-weight:bold">
            {r['origin']} → {r['destination']}
          </td>
          <td style="padding:10px 12px;border:1px solid #dee2e6">
            {r['currency']} {r['current_price']:,.0f}
          </td>
          <td style="padding:10px 12px;border:1px solid #dee2e6;
                     color:{trend_color}">
            {trend_text}
          </td>
          <td style="padding:10px 12px;border:1px solid #dee2e6">
            {r['alerts_this_week']} alert{'s' if r['alerts_this_week'] != 1 else ''}
          </td>
        </tr>
        {historic_row}
        {carriers_row}
        {recommendation}"""

    # Best movement this week
    best_movement = ""
    if summary_data.get("best_movement"):
        bm = summary_data["best_movement"]
        best_movement = f"""
        <div style="background:#e6f4ea;border:1px solid #c3e6cb;
                    border-radius:8px;padding:16px;margin:20px 0">
          <h4 style="margin:0 0 8px;color:#188038">
            🏆 Best price movement this week
          </h4>
          <p style="margin:0">
            <strong>{bm['origin']} → {bm['destination']}</strong>
            dropped {bm['currency']} {bm['drop']:,.0f}
            {'— alert sent!' if bm['alerted'] else '— below your threshold'}
          </p>
        </div>"""

    # No alerts note
    no_alerts_note = ""
    if summary_data["total_alerts"] == 0:
        no_alerts_note = """
        <p style="color:#666;font-size:13px;font-style:italic">
          No alerts fired this week — prices stayed within your thresholds.
          {APP_NAME} checked your routes every
          """ + ("hour" if is_traveller else "2 hours") + """
          and will alert you the moment a significant deal appears.
        </p>"""

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;
                 max-width:600px;margin:0 auto">
      <div style="background:linear-gradient(135deg,#1a73e8,#0d47a1);
                  padding:24px;border-radius:12px 12px 0 0">
        <h2 style="color:white;margin:0">✈️ Weekly Flight Summary</h2>
        <p style="color:#cce0ff;margin:8px 0 0">
          Week ending {summary_data['week_ending']}
        </p>
      </div>
      <div style="background:white;padding:24px;border:1px solid #e0e0e0">
        <p>Hi {user.name},</p>
        <p>Here's what {APP_NAME} found for you this week.</p>

        <table style="width:100%;border-collapse:collapse;margin:8px 0 4px">
          <tr style="background:#f0f4ff">
            <td style="padding:10px 12px;border:1px solid #dee2e6">
              <strong>Routes monitored</strong>
            </td>
            <td style="padding:10px 12px;border:1px solid #dee2e6">
              {summary_data['routes_count']}
            </td>
            <td style="padding:10px 12px;border:1px solid #dee2e6">
              <strong>Alerts sent</strong>
            </td>
            <td style="padding:10px 12px;border:1px solid #dee2e6">
              {summary_data['total_alerts']}
            </td>
          </tr>
        </table>

        {no_alerts_note}
        {best_movement}

        <h4 style="margin-top:24px">Your routes this week</h4>
        <table style="width:100%;border-collapse:collapse;margin:8px 0">
          <thead>
            <tr style="background:#1a73e8;color:white">
              <th style="padding:8px 12px;border:1px solid #1a73e8;
                         text-align:left">Route</th>
              <th style="padding:8px 12px;border:1px solid #1a73e8;
                         text-align:left">Current</th>
              <th style="padding:8px 12px;border:1px solid #1a73e8;
                         text-align:left">vs Last Week</th>
              <th style="padding:8px 12px;border:1px solid #1a73e8;
                         text-align:left">Alerts</th>
            </tr>
          </thead>
          <tbody>
            {route_rows}
          </tbody>
        </table>

        <div style="text-align:center;margin:30px 0">
          <a href="https://66.226.145.35/dashboard"
             style="background:#1a73e8;color:white;padding:12px 30px;
                    text-decoration:none;border-radius:6px;font-weight:bold">
            View Dashboard →
          </a>
        </div>

        <p style="color:#999;font-size:12px;margin-top:20px">
          Prices are indicative and sourced from the Duffel API.
          Always confirm before booking.
        </p>
      </div>
      <div style="background:#f8f9fa;padding:16px;
                  border-radius:0 0 12px 12px;
                  text-align:center;color:#999;font-size:12px">
        {APP_NAME} — Weekly Summary
        &nbsp;·&nbsp;
        {'Traveller' if is_traveller else 'Explorer'} Plan
        &nbsp;·&nbsp;
        <a href="https://66.226.145.35/profile"
           style="color:#999">Manage Subscription</a>
      </div>
    </body>
    </html>
    """

    return _send(user.get_alert_email(), subject, html)


def send_confirmation_email(user, confirm_url):
    """Send email address confirmation email to new user."""
    subject = f"✈️ Confirm your {APP_NAME} email address"

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;
                 max-width:600px;margin:0 auto">
      <div style="background:linear-gradient(135deg,#1a73e8,#0d47a1);
                  padding:24px;border-radius:12px 12px 0 0">
        <h2 style="color:white;margin:0">✈️ Confirm your email</h2>
      </div>
      <div style="background:white;padding:24px;border:1px solid #e0e0e0">
        <p>Hi {user.name},</p>
        <p>Thanks for registering with {APP_NAME}. Please confirm
           your email address to activate your account.</p>
        <div style="text-align:center;margin:30px 0">
          <a href="{confirm_url}"
             style="background:#1a73e8;color:white;padding:14px 32px;
                    text-decoration:none;border-radius:6px;
                    font-weight:bold;font-size:16px">
            Confirm Email Address →
          </a>
        </div>
        <p style="color:#666;font-size:13px">
          This link expires in 24 hours. If you did not register with
          {APP_NAME}, you can ignore this email.
        </p>
      </div>
      <div style="background:#f8f9fa;padding:16px;
                  border-radius:0 0 12px 12px;
                  text-align:center;color:#999;font-size:12px">
        {APP_NAME} — Email Confirmation
      </div>
    </body>
    </html>
    """
    return _send(user.email, subject, html)
