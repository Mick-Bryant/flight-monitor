# Flight Monitor — Product Design & Specification
**Version 5.0 | June 2026 | Michael Bryant**

---

## Product Status Summary

Core platform built and deployed · Public marketing site, guides & onboarding live · Production server in Sydney
Three-tier subscription model finalised · Flight-time optimization modes (Traveller) shipped · Git repository initialised
Monetisation (Stripe), production data key & legal pages pending external prerequisites

---

## 1. Executive Summary

Flight Monitor is a private, invite-only, subscription-based web application that monitors flight prices around the clock and sends intelligent email alerts when prices drop. Built for travellers who are tired of free tools that cry wolf, it alerts only when a fare is genuinely cheap — using real market data across multiple carriers rather than a single airline feed.

Where free tools alert on any price drop, Flight Monitor competes on **judgment**: it combines flash-sale and historic-low detection with configurable per-region thresholds and Around The World itinerary monitoring — a combination no single competitor offers — and rounds this out with multi-currency, nearby-airport and flexible-date search. Its edge is alert quality, not feature count.

The core platform is built, tested, and running in production on a Sydney cloud server, now including the public marketing site, FAQ, SEO guide pages, and a guided onboarding flow. The remaining path to monetisation — subscription payments, the production flight-data key, and legal pages — is scoped and gated only on external prerequisites (company registration and Duffel production approval).

---

## 2. Product Vision & Positioning

### 2.1 The Problem

Travellers waste money on flights by booking at the wrong time. Existing free alert tools are basic — they notify on any price drop, with no intelligence about whether a drop is genuinely significant or historically unusual. Users are overwhelmed with irrelevant alerts and miss the ones that matter.

### 2.2 The Solution

Flight Monitor runs two distinct alert modes simultaneously against market-wide data:

| Alert Mode | What it Detects | Why it Matters |
|---|---|---|
| Flash Sale | Market minimum drops below the historic market median by more than the user's threshold | Catches sudden promotional sales — often lasting only 24–48 hours |
| Historic Low | Market minimum falls below the average of the lowest 20% of historical prices for the route | Confirms a price is genuinely cheap by historical standards — not a minor fluctuation |

### 2.3 Positioning & Messaging

**Tagline:** "Know when it's actually cheap."

**Core statement:** Flight Monitor tells you when a flight is genuinely cheap — not just cheaper.

**Positioning statement:** For frequent and serious travellers tired of alerts that cry wolf, Flight Monitor is a private flight-price watchdog that alerts only when a fare is genuinely low by its own historical standards. Unlike free tools that ping on every minor dip and earn from ads and booking commissions, Flight Monitor works only for the subscriber: no ads, no data selling, no noise.

**Three pillars, in priority order:**
1. **Intelligence (primary)** — historic-low and market-median logic produce fewer, higher-confidence alerts rather than more noise.
2. **Capability free tools lack (proof)** — RTW with surface segments and configurable per-region thresholds demonstrate genuine depth.
3. **Aligned incentives (trust)** — the subscriber is the customer, not the product: private, ad-free, invite-only.

### 2.4 Differentiators — Genuine vs Table Stakes

**Genuine differentiators**
- Intelligent alerting — dual-mode flash-sale plus historic-low detection that fires only on genuinely low prices. The core of the product.
- Configurable thresholds by route type — domestic plus seven regions, overridable per route; uncommon, and aimed at frequent travellers.
- Flight-time optimization modes (Traveller) — alerts can track the cheapest, fastest, or best-value offer rather than always the market minimum; per-user default with per-route override.
- Around The World monitoring with surface segments — genuinely unique; no major competitor tracks a combined multi-leg total.
- Aligned incentives — private, ad-free, subscription-funded and invite-only; structurally cannot profit from engagement-driven noise.

**Supporting features (table stakes — not sold as USPs)**
Market-wide pricing across carriers, multi-currency (166), nearby-airport comparison, flexible-date search, price-history charts, and direct booking links. Useful and expected, but free tools offer equivalents — so they reassure rather than persuade.

### 2.5 Known Limitation — Carrier Coverage

Flight data comes from Duffel (NDC), which does not cover most low-cost carriers — including Jetstar, a major share of Australian domestic and short-haul leisure flying. On those routes a free search may surface fares Flight Monitor cannot price, so the "market-wide" claim is scoped to NDC carriers.

This is handled two ways: messaging sells judgment rather than total coverage and positions the product as a complement to a quick LCC check; and a near-term task evaluates an LCC-inclusive data source (Travelpayouts or Kiwi) as a lighter alternative to the scraper roadmap. Closing the gap via scraping remains a revenue-funded, post-launch step (Section 11).

---

## 3. Design System

### 3.1 Colour Palette

| Role | Hex |
|---|---|
| Primary — navbar, buttons | `#1a73e8` |
| Primary hover | `#1558b0` |
| Page background | `#f8f9fa` |
| Price drop (bold green) | `#188038` |
| Price rise (red) | `#d93025` |
| Dark footer | `#1a1a2e` |

Email headers: Flash Sale alerts use an orange gradient header; Historic Low alerts use a blue gradient header — giving each alert type an instantly recognisable visual identity.

### 3.2 Components & Conventions

- **Cards:** Borderless, 12px border-radius, soft shadow (`box-shadow: 0 2px 8px rgba(0,0,0,0.08)`)
- **Tier badges (navbar):** Admin — `bg-danger`; Trial — `bg-info` with dark text plus days remaining; Explorer — `bg-primary`; Traveller — `bg-success`
- **Pricing language:** Annual savings are always expressed as "2 months free," never as a percentage discount
- **Frontend toolkit:** Bootstrap 5.3 with Bootstrap Icons 1.11; Chart.js for dual-line price history charts

### 3.3 Configurable App Name

The product name is not hard-coded. It is stored in `Config.APP_NAME` (set via the `APP_NAME` environment variable) and injected into every template as the `{{ app_name }}` Jinja2 global. A full rebrand requires changing a single configuration value.

---

## 4. Current Build Status

| Area | Feature | Status |
|---|---|---|
| Foundation | Flask app, SQLite/SQLAlchemy, auth (login/register/logout) | ✅ Complete |
| Foundation | Invite-only registration with expiring tokens | ✅ Complete |
| Foundation | Forgot/reset password, email confirmation, admin password reset | ✅ Complete |
| Foundation | Per-user alert email address; CSRF protection (Flask-WTF) | ✅ Complete |
| Routes | Multi-route monitoring; 4,563-airport live search | ✅ Complete |
| Routes | 7-region route-type detection; tiered + per-route thresholds | ✅ Complete |
| Routes | Flexible dates (window search); nearby airports (opt-in) | ✅ Complete |
| Routes | Pause/resume/delete; dual-line price history chart; alert log | ✅ Complete |
| Monitor | Duffel v2 market-wide pricing (up to 20 offers/check) | ✅ Complete |
| Monitor | Market summary (min/median/mean); flash-sale & historic-low alerts | ✅ Complete |
| Monitor | Nearby + flexible-date sampling; rate-limit protection; baseline reset | ✅ Complete |
| Monitor | Journey duration parsing (ISO-8601) from Duffel slice data | ✅ Complete |
| Optimize | Cheapest / Fastest / Best Value modes (Traveller); per-user + per-route | ✅ Complete |
| Optimize | Effective-cost ranking (price + time value + stop penalty); AUD coefficients admin-editable | ✅ Complete |
| Optimize | Mode-aware historic series from PriceHistory; MarketSummary unchanged for shared data | ✅ Complete |
| Currency | Multi-currency preference; live conversion (166); dashboard/email display | ✅ Complete |
| RTW | Multi-leg itineraries; same-city groups; surface segments; combined alerts | ✅ Complete |
| Email | All alert templates, weekly summary, trial reminders, reset/invite/confirm | ✅ Complete |
| Admin | User, airport & invite management; manual scrub; weekly-summary trigger | ✅ Complete |
| Admin | Alert optimization parameter editor (time value + stop penalty AUD) | ✅ Complete |
| Public site | Landing page, FAQ, guides index + Sydney/Perth guides | ✅ Complete |
| UX | Guided onboarding (/welcome); cancellation & reactivation flows | ✅ Complete |
| UX | Departure date min = today; return date min follows departure | ✅ Complete |
| Infra | BinaryLane Sydney VPS, Nginx + Let's Encrypt HTTPS, Gunicorn, systemd, nightly scrub | ✅ Complete |
| Infra | Git repository initialised; deployment via rsync + systemctl | ✅ Complete |
| Payments | Stripe subscriptions, trial enforcement, tier enforcement | ⏳ Planned |
| Legal | Terms of Service, Privacy Policy, .com.au domain | ⏳ Planned |
| Data | Duffel production API key | ⏳ Planned |
| Growth | Referral system, additional SEO guides | ⏳ Pending |

---

## 5. System Architecture

### 5.1 Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Framework | Flask 3.1.3 | Web requests, rendering, sessions |
| Database | SQLite (`flight_monitor.db`) | Single-file; migrate to PostgreSQL at scale |
| ORM | SQLAlchemy 2.0 / Flask-SQLAlchemy 3.1 | Database-agnostic data layer |
| Auth | Flask-Login + Flask-Bcrypt | Sessions and password hashing |
| Forms / CSRF | Flask-WTF + WTForms | Form handling and CSRF protection |
| Background jobs | APScheduler 3.11 | Price checks, RTW checks, scrub, reminders, summary |
| Flight data | Duffel API v2 | Real-time market pricing via NDC |
| Email | SendGrid 6.12 | Transactional and summary email |
| Currency | ExchangeRate-API | 166 currencies, free tier, 1-hour cache |
| Distance | Haversine (app/nearby.py) | Nearby-airport discovery within 100km |
| Frontend | Bootstrap 5.3 + Bootstrap Icons 1.11 + Chart.js | Responsive UI, price history charts |
| Web server | Nginx + HTTPS (Let's Encrypt) | Reverse proxy, TLS termination |
| App server | Gunicorn — 1 worker | Single worker for SQLite write safety |
| Process manager | systemd | Auto-restart, survives reboots |
| Host | BinaryLane Sydney VPS | Ubuntu 24.04 LTS |
| Payments | Stripe (planned) | Subscriptions, portal, webhooks |

### 5.2 Data Models

A key architectural decision is the separation of the shared, immutable trip definition (`GlobalRoute`) from each user's personal monitoring preferences (`UserRoute`). This lets a single Duffel API call serve every user watching the same route, reducing cost and rate-limit pressure.

| Model | Purpose / Key Fields |
|---|---|
| User | Auth (email, password_hash, email_confirmed, tokens); identity (name, account_type); subscription (tier, status, trial_start/end, billing_period, Stripe IDs); preferences (preferred_currency, airline_memberships, alert_email, price_thresholds per region, **optimize_for**); flags (is_admin, is_active) |
| GlobalRoute | Immutable trip: origin, destination, departure_date, return_date, adults, cabin_class. Deduplication key — one shared Duffel call across all watchers. last_checked drives per-tier rate limiting |
| UserRoute | Links User → GlobalRoute. Personal threshold_usd, baseline_price, is_active; options nearby_airports, flexible_dates, flex_days, flex_duration_days; **optimize_for** (nullable — NULL inherits from User) |
| PriceHistory | Per offer per check: price, currency, airline, stops, **duration_minutes**, is_cheapest. Linked to GlobalRoute; retained 6 months |
| MarketSummary | Per check per route: market_min, market_median, market_mean, offer_count, cheapest_airline. Shared across all users; never filtered per user |
| AlertLog | Permanent record: alert_type (sudden_sale / historic_low), baseline_price, alerted_price, drop_amount, airline. All fields reflect the mode-selected offer, not necessarily the market minimum |
| AppConfig | Admin-editable key/value store. Current keys: time_value_aud_per_hour (default 12.0), stop_penalty_aud (default 40.0). Used by Best Value effective-cost ranking |
| RTWItinerary + RTWLeg | Multi-leg itinerary with combined price monitoring; surface_segment flag on legs; 30 same-city airport groups for connection validation |
| Airport | 4,563 airports: iata_code, icao_code, city, country, region, coordinates, airport_type, is_active |
| Invite | Token-based registration: token, email, expires_at, used_at, used_by, is_active |

### 5.3 Region Model

Routes are classified into eight types using a seven-region geographic model. Each airport is assigned a region and country; route type is detected automatically when a route is added.

| Region | Default Threshold | Route Type |
|---|---|---|
| Domestic (same country as origin) | AUD 150 | Domestic |
| Australia / Oceania | AUD 200 | Regional |
| Asia | AUD 300 | Regional / Intl |
| Middle East | AUD 350 | Regional / Intl |
| Europe | AUD 500 | International |
| Africa | AUD 400 | International |
| North America | AUD 550 | International |
| South America | AUD 500 | International |
| International fallback | AUD 400 | International |

---

## 6. Alert Intelligence System

### 6.1 Dual-Mode Logic

Every price check runs two independent analyses against market-wide data across all carriers. Both modes are active from day one.

| | Flash Sale | Historic Low |
|---|---|---|
| Trigger | Market minimum drops below the historic market median by more than the route threshold | Market minimum below the average of the lowest 20% of historical prices |
| Threshold | Route threshold (profile default, overridable per route) | None — any price below the historic average low triggers |
| Priority | Fires when Historic Low does not apply | Takes priority when both would trigger |
| Email | Orange header, top offers, member highlighting | Blue header, historic-low comparison, saving shown |

### 6.2 Guards & Baseline

- **False-alert guard** — no alert fires if the price has risen since the last alert
- **Baseline auto-reset** — the baseline resets on a price rise and after any alert, preventing repeat alerts on the same drop

### 6.3 Market-Wide Pricing

Each check fetches up to 20 offers from Duffel across all available carriers. Every offer is stored in PriceHistory; aggregated min/median/mean are stored in MarketSummary. The historic average low is the average of the lowest 20% of market_min values over `min(days since route created, 180 days)`.

### 6.4 Nearby Airports & Flexible Dates

- **Nearby airports** — Haversine distance, 100km radius, large airports only, max 3 per origin, opt-in per route; alert reminds the user to factor in surface travel cost
- **Flexible dates** — window search producing ~9 sample points; optional flexible duration (±3/7/14 days); cheapest combination used for alerts and baseline; opt-in per route

### 6.5 Flight-Time Optimization Modes (Traveller)

Traveller-tier users can choose which offer drives their alerts, rather than always the market minimum. The mode is set as a user-level default (profile page) with an optional per-route override (add-route form). Explorer and Trial users are silently downgraded to Cheapest; the model enforces this in `UserRoute.effective_optimize_for()`.

| Mode | Offer Selected | How |
|---|---|---|
| **Cheapest** (default) | Lowest price — market minimum | Existing behaviour; no change to any other user |
| **Fastest** | Shortest total journey duration | `min(duration_minutes)` across all offers with duration data; falls back to cheapest if no duration available |
| **Best Value** | Lowest effective cost | `price + (time_value_aud/hr × hours) + (stop_penalty_aud × stops)`, with AUD coefficients converted to offer currency via the live exchange rate |

**Historic series:** For Cheapest mode, the existing MarketSummary aggregates are used unchanged. For Fastest and Best Value, the historic series is reconstructed at alert time from raw PriceHistory rows — the mode-optimal offer is selected per historical check, and historic low / median are computed from that series. Pre-migration rows (no `duration_minutes`) are skipped for Fastest mode to prevent the legacy cheapest price from contaminating the duration-based series. Results are cached per mode per route within each check cycle.

**Effective-cost coefficients** are stored in the `AppConfig` table and editable by admins on the admin page. Default values (AUD 12/hr, AUD 40/stop) represent a balanced weighting; AUD 35/hr and AUD 90/stop represent a strong time-saver preference.

**Baseline tracking:** `UserRoute.baseline_price` tracks the mode-selected offer's price, not always the market minimum. This ensures drop calculations and alert guards remain coherent for each user's chosen mode.

### 6.6 RTW Monitoring

Around The World itineraries are priced per air leg (cheapest offer per leg) and summed; the combined total is compared against the baseline total and alerts when it drops by the configured threshold. Optimization modes do not apply to RTW legs — cheapest per leg is always used. Surface segments are flagged for connection validation against a 30-city same-city airport group database, with the leg still priced where applicable.

---

## 7. Subscription Model

### 7.1 Pricing Tiers

The model was consolidated to three tiers. A Family tier and an unlimited tier were both rejected — the former because families monitoring identical routes gain nothing from multiple accounts, the latter to protect infrastructure from commercial over-use. A guiding rule is that trial conditions never exceed the minimum paid tier in any dimension.

| | Trial | Explorer | Traveller |
|---|---|---|---|
| **Price** | Free | AUD $8/mo · $80/yr | AUD $20/mo · $192/yr |
| **Duration** | 14 days | Ongoing | Ongoing |
| **Routes** | 3 | 5 | 20 |
| **RTW itineraries** | 1 | 2 | 20 |
| **Alert recipients** | 1 | 1 | 4 |
| **Check interval** | 120 min | 120 min | 60 min |
| **Weekly summary** | Basic | Basic | Full + recommendations |
| **Optimization modes** | Cheapest only | Cheapest only | Cheapest / Fastest / Best Value |

Annual prices use the "2 months free" framing and sit deliberately below psychological thresholds: Explorer's $80/yr stays under $100, Traveller's $192/yr under $200. AUD is the base currency; Stripe handles conversion at checkout, with approximate local-currency equivalents shown on the marketing page.

Price is framed against value, not feature count: a single caught international fare typically saves more than a full year's subscription.

### 7.2 Account Types

- **admin** — maximum of 2; bypasses all tier limits; no payment required
- **invited** — free Explorer tier ongoing; no trial and no payment until they choose Traveller
- **self_registered** — 14-day trial then paid; invited users become self_registered when they subscribe

### 7.3 Trial Strategy

New self-registered users receive a 14-day trial with no credit card required. A countdown banner changes colour at ≤10 days (warning) and ≤3 days (danger). Reminder emails are sent on Day 10 and Day 13. A trial-bypass mechanic lets users skip straight to a paid plan, either during onboarding or on hitting the 3-route trial ceiling.

### 7.4 Revenue Projections

| Scale | Paying Users | Gross Revenue | Net After Infra |
|---|---|---|---|
| Early | 50 | AUD $500/mo | AUD $443/mo |
| Growth | 200 | AUD $2,000/mo | AUD $1,855/mo |
| Scale 1 | 500 | AUD $5,000/mo | AUD $4,823/mo |
| Scale 2 | 2,000 | AUD $20,000/mo | AUD $19,255/mo |
| Scale 3 | 5,000+ | AUD $50,000/mo | AUD $47,860/mo |

~AUD $10 blended average revenue per paying user assumed. GST registration required only once annual turnover exceeds AUD $75,000.

### 7.5 Infrastructure Scaling

| Scale | Architecture | Database | Est. Cost/mo |
|---|---|---|---|
| 0–500 users | Single BinaryLane VPS 2GB | SQLite (current) | AUD ~$10 |
| 500–2,000 | Single VPS 4GB + Redis | PostgreSQL on same server | AUD ~$40 |
| 2,000–5,000 | 2× app servers + load balancer | Dedicated PostgreSQL | AUD ~$130 |
| 5,000+ | Auto-scaling cluster | Managed PostgreSQL (RDS) | AUD $400+ |

Migration from SQLite to PostgreSQL requires changing one line in `config.py`; all application code is database-agnostic through SQLAlchemy. The current Gunicorn single-worker constraint is a deliberate SQLite write-safety measure and is removed on the move to PostgreSQL.

---

## 8. Application Map

### 8.1 Public Pages

| URL | Template |
|---|---|
| `/` | `landing.html` — hero, how it works, features, pricing, value prop, footer |
| `/faq` | `faq.html` |
| `/guides` | `guides/index.html` |
| `/guides/cheapest-flights-from-sydney` | `guides/cheapest-flights-from-sydney.html` |
| `/guides/cheapest-flights-from-perth` | `guides/cheapest-flights-from-perth.html` |
| `/login` | `login.html` |
| `/register/<token>` | `register.html` |
| `/forgot-password` | `forgot_password.html` |

### 8.2 Authenticated App Pages

| URL | Description |
|---|---|
| `/dashboard` | All monitored routes, prices, trial banner |
| `/welcome` | 3-step onboarding (add first route) |
| `/routes/add` | Add new route |
| `/routes/<id>/toggle` | Pause / resume |
| `/routes/<id>/delete` | Delete route |
| `/routes/<id>/history` | Price history chart + alert log |
| `/rtw` | RTW itinerary list |
| `/rtw/add` | Add RTW itinerary |
| `/rtw/<id>` | RTW detail |
| `/profile` | Name, email, currency, airline memberships |
| `/profile/thresholds` | Per-region alert thresholds |
| `/profile/optimize` | Alert optimization mode (Traveller — Cheapest / Fastest / Best Value) |
| `/upgrade` | Plan comparison + upgrade |
| `/cancel` + `/cancel/confirm` | Cancellation flow |
| `/reactivate` + `/reactivate/confirm` | Reactivation flow |

### 8.3 Admin Panel

| URL | Description |
|---|---|
| `/admin` | User list with account-type/tier/status badges; enable/disable, reset password, promote/demote admin (max 2), restore invited users |
| `/admin/airports` | Add / enable / disable airports |
| `/admin/invites` | Create, cancel, track invite usage |
| `/admin/config` | Edit alert optimization coefficients (time_value_aud_per_hour, stop_penalty_aud) |
| `/admin/send_weekly_summary` | Trigger weekly summary immediately (test) |
| `/admin/scrub` | Manual data scrub |

### 8.4 API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/airports?q=` | Live airport search (city, name, country, alias) |
| `GET /api/routes/threshold?origin=&destination=` | Recommended threshold for a route |
| `GET /api/routes/<id>/history` | JSON time-series price data for charts |
| `GET /api/rtw/check_connection` | Validate an RTW leg airport connection |

---

## 9. Scheduled Jobs (APScheduler)

| Job | Schedule | Description |
|---|---|---|
| Price check | Every 60 min | Checks all active global routes; respects per-tier intervals |
| RTW check | Every 60 min | Checks all active RTW itineraries |
| Nightly scrub | 4pm UTC daily | Removes price history + market summaries older than 6 months |
| Trial reminders | 11pm UTC daily | Sends reminders on Day 10 and Day 13 of trial |
| Weekly summary | Sun 11pm UTC (Mon 9am AEST) | Sends weekly summary to all active users |

---

## 10. Email System

Provider: SendGrid. Sender configured via `ALERT_FROM_EMAIL` environment variable.

| Email | Trigger |
|---|---|
| Flash Sale alert | Price drop ≥ threshold |
| Historic Low alert | Price below the historic average low |
| Nearby Airport alert | Nearby airport cheaper by the configured threshold |
| RTW alert | Combined leg total drops by threshold |
| Weekly Summary | Monday 9am AEST |
| Trial reminder | Day 10 and Day 13 of trial |
| Password reset | User request (1-hour token) |
| Invitation | Admin generates invite link |
| Email confirmation | On registration (24-hour token) |

All emails include a Manage Subscription link and the price-data disclaimer footer. All alert emails include a top-offers table, airline membership badges, and Google Flights plus airline-direct booking links.

Weekly Summary adds Traveller-only extras: historic average-low comparison, top carriers, and a threshold recommendation (after 30 days of data; recommendation = 80% of the maximum observed drop, rounded to the nearest $25).

---

## 11. Build Roadmap

### 11.1 Blockers (external prerequisites)

| Item | Blocker | Notes |
|---|---|---|
| Stripe integration | Holding + operating Pty Ltd company registration | ASIC registration → ABN → bank account |
| Public registration | Stripe | Depends on company registration |
| Duffel production key | Awaiting Duffel approval | Application submitted |
| .com.au domain + SSL | ABN required | Let's Encrypt already live on current host |
| Legal pages (ToS + Privacy Policy) | Required before public launch | Australian Privacy Act compliant |

### 11.2 Pending (no blockers)

- Referral system — unique referral links, one free month per paying referral, tracking + dashboard
- Additional SEO guide pages — Melbourne and Brisbane departures; general "how to find cheap flights" article
- Near-term data: evaluate Travelpayouts or Kiwi as LCC-inclusive data source

### 11.3 Future Roadmap (post-launch, revenue funded)

**Data Independence**
- Phase 1 (100 users): Playwright scrapers for Qantas, Jetstar, Virgin Australia
- Phase 2 (200 users): cross-validate Duffel against scraped data — legal review required first
- Phase 3 (200 users): independent historic baseline from owned scraped data
- Phase 4 (500 users): LCC expansion (AirAsia, Ryanair)

**Mobile:** PWA first (push notifications), React Native later.

**Additional Features:** SMS alerts via Twilio (premium tier); price calendar view; price-prediction indicator; minimum-price (absolute) alerts; developer API access tier.

**Business / Enterprise tier** — 50–200 routes, multi-user, AUD $100–200/mo.

**Formal Data Partnerships (500+ users):** Travelpayouts affiliate API; airline direct partnerships; OAG or Cirium enterprise licensing.

---

## 12. Production Configuration

| Setting | Value |
|---|---|
| Provider | BinaryLane (Sydney, NextDC S1) |
| Operating system | Ubuntu 24.04 LTS |
| App user / directory | flightmonitor · `/home/flightmonitor` |
| Database | `/home/flightmonitor/instance/flight_monitor.db` |
| Service | `flightmonitor` (systemd) |
| Web | Nginx reverse proxy → Gunicorn (1 worker) → Flask |
| TLS | Let's Encrypt HTTPS |
| Check interval | Every 60 minutes |
| Nightly scrub | 4pm UTC (2am AEST) daily |

**Key environment variables:** `SECRET_KEY`, `DUFFEL_ACCESS_TOKEN`, `SENDGRID_API_KEY`, `ALERT_FROM_EMAIL`, `APP_NAME`, `CHECK_INTERVAL_MINUTES` (60 prod / 2 local), `SERVER_NAME`, `PREFERRED_URL_SCHEME`

---

## 13. Security Architecture

- All passwords hashed with bcrypt — never stored in plain text
- `SECRET_KEY` signs all session cookies; CSRF protection on all forms via Flask-WTF
- SSH access by key only — password authentication disabled on the server
- Gunicorn bound to localhost; Nginx handles all external traffic on 80/443
- `.env` excluded from version control — never committed to Git
- Password reset tokens expire after 1 hour and are single-use; email confirmation tokens last 24 hours
- Forgot-password page reveals nothing about registered emails — prevents enumeration
- Admin pages verify `is_admin` on every request — no client-side trust
- Invite-only registration — no public sign-up surface to attack until launch
- HTTPS on all connections (Let's Encrypt); timezone-aware datetime handling throughout

---

## 14. Competitive Analysis

| Feature | Flight Monitor | Google Flights | Skyscanner | Hopper | Going.com |
|---|---|---|---|---|---|
| Historic low alerts | Yes | No | No | Partial | No |
| Market-wide pricing | NDC carriers | Yes | Yes | Limited | No |
| Configurable thresholds | By region | No | No | No | No |
| RTW monitoring | Yes | No | No | No | No |
| Nearby airports | 100km | No | No | No | No |
| Membership highlighting | Yes | No | No | No | No |
| No ads | Yes | No | No | No | Paid only |
| Private / invite only | Yes | No | No | No | No |
| Cost | AUD $8–20/mo | Free | Free | Free/paid | USD $25–50/mo |

Flight Monitor competes on judgment, not coverage. Its defensible edge is intelligent historic-low alerting, configurable regional thresholds, and unique RTW monitoring — a combination no single competitor offers — backed by aligned, ad-free incentives.

---

## 15. Go-to-Market Strategy

- **Phase 1 — Validate (current):** Run free for 10–30 invited family and friends; gather feedback on alert quality and usability.
- **Phase 2 — Soft launch:** Complete company registration, add Stripe, open the 14-day trial publicly, begin content marketing on X and Facebook with AI-assisted production.
- **Phase 3 — Growth:** Add the referral program; build SEO guide pages targeting flight-search queries; convert savers into advocates.

**Channels:** X (deal posts, proof screenshots), Facebook travel groups, SEO guides, word of mouth, and the referral incentive.

---

## 16. Legal & Compliance

- **Business structure:** Holding Pty Ltd + operating Pty Ltd (ASIC registration required before ABN, Stripe, and .com.au domain)
- **GST registration:** Only required above AUD $75,000 turnover
- **Required pages:** Terms of Service (subscription terms, refunds, price disclaimer) and Privacy Policy (Australian Privacy Act compliant, data use and deletion rights)
- **Price-data disclaimer:** All prices are sourced from Duffel and indicative only; users must verify on the airline or booking platform before purchasing. Shown in all alert emails and on the site.

---

## 17. Glossary

| Term | Definition |
|---|---|
| Baseline price | The price of the mode-selected offer recorded when a route is first checked; alert calculations measure from this point. Resets after an alert or on a price rise |
| Flash Sale alert | Fires when the mode-selected offer's price drops below the historic median of that offer series by more than the route threshold |
| Historic Low alert | Fires when the mode-selected offer's price falls below the average of the lowest 20% of that offer's historical prices. Active from day 1 |
| Market minimum / median | Lowest / middle price across all carriers at a check; stored in MarketSummary and shared across all users. Independent of any user's optimization mode |
| Optimize mode | The rule used to select which offer drives alerts for a route: Cheapest (default), Fastest (min duration), or Best Value (min effective cost). Traveller-tier only |
| Effective cost | `price + (time_value_aud/hr × journey_hours) + (stop_penalty_aud × stops)`, converted to offer currency. Used by Best Value mode to rank offers |
| duration_minutes | Total journey duration in minutes across all slices of an offer, parsed from Duffel's ISO-8601 slice duration field |
| AppConfig | Admin-editable key/value table for system parameters. Currently stores time_value_aud_per_hour and stop_penalty_aud for Best Value mode |
| Lookback window | `min(days since route created, 180 days)` — grows as the route ages, capped at 6 months |
| GlobalRoute / UserRoute | Shared immutable trip definition / a user's personal monitoring link and preferences for that trip |
| Surface segment | Ground travel between two airports in an RTW itinerary, flagged for connection validation |
| Same-city group | A set of airports serving one city (e.g. LHR, LGW, STN for London) |
| Account type | admin, invited, or self_registered — governs trial, payment, and limits |
| Haversine formula | Great-circle distance between two lat/long coordinates; used for nearby-airport discovery |
| NDC | New Distribution Capability — the airline distribution standard Duffel uses |
| LCC | Low Cost Carrier (e.g. Jetstar, Ryanair) — sells direct, generally outside NDC/GDS |
| IATA code | The 3-letter airport identifier used globally (e.g. SYD, LHR) |
| RTW | Around The World — a multi-leg itinerary monitored as a combined total price |
