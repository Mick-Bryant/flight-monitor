from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone, timedelta
import secrets
import json

db = SQLAlchemy()

# ---------------------------------------------------------------------------
# Subscription tier definitions
# ---------------------------------------------------------------------------

TIERS = {
    "trial": {
        "name":            "Trial",
        "price_aud":       0,
        "max_routes":      3,
        "max_rtw":         1,
        "max_recipients":  1,
        "check_interval":  120,
        "weekly_summary":  True,
        "recommendations": False,
        "trial_days":      14,
    },
    "explorer": {
        "name":            "Explorer",
        "price_aud":       8,
        "price_aud_annual": 80,
        "max_routes":      5,
        "max_rtw":         2,
        "max_recipients":  1,
        "check_interval":  120,
        "weekly_summary":  True,
        "recommendations": False,
        "trial_days":      0,
    },
    "traveller": {
        "name":            "Traveller",
        "price_aud":       20,
        "price_aud_annual": 192,
        "max_routes":      20,
        "max_rtw":         20,
        "max_recipients":  4,
        "check_interval":  60,
        "weekly_summary":  True,
        "recommendations": True,
        "trial_days":      0,
    },
}

# ---------------------------------------------------------------------------
# Region definitions
# ---------------------------------------------------------------------------

REGIONS = [
    "Australia / Oceania", "Asia", "Middle East",
    "Europe", "Africa", "North America", "South America",
]

THRESHOLD_DEFAULTS = {
    "domestic":      150.00,
    "oceania":       200.00,
    "asia":          300.00,
    "middle_east":   350.00,
    "europe":        500.00,
    "africa":        400.00,
    "north_america": 550.00,
    "south_america": 500.00,
    "international": 400.00,
}

REGION_TO_KEY = {
    "Australia / Oceania": "oceania",
    "Asia":                "asia",
    "Middle East":         "middle_east",
    "Europe":              "europe",
    "Africa":              "africa",
    "North America":       "north_america",
    "South America":       "south_america",
}

# Same-city airport groups for RTW validation
SAME_CITY_GROUPS = [
    {"LHR", "LGW", "STN", "LCY", "LTN"},
    {"CDG", "ORY"},
    {"JFK", "EWR", "LGA"},
    {"LAX", "BUR", "LGB", "ONT", "SNA"},
    {"ORD", "MDW"},
    {"SFO", "OAK", "SJC"},
    {"IAH", "HOU"},
    {"DCA", "IAD", "BWI"},
    {"NRT", "HND"},
    {"KIX", "ITM", "UKB"},
    {"FRA", "HHN"},
    {"BER", "SXF", "TXL"},
    {"FCO", "CIA"},
    {"MXP", "LIN", "BGY"},
    {"MAD", "TOJ"},
    {"BCN", "GRO", "REU"},
    {"AMS", "EIN"},
    {"ARN", "BMA", "NYO"},
    {"CPH", "MMX"},
    {"SYD", "WSI"},
    {"MEL", "AVV"},
    {"YYZ", "YTZ", "YHM"},
    {"YVR", "YXX"},
    {"YUL", "YMX"},
    {"PEK", "PKX"},
    {"PVG", "SHA"},
    {"ICN", "GMP"},
    {"TPE", "TSA"},
    {"DXB", "AUH", "SHJ"},
]


def same_city(iata_a, iata_b):
    if iata_a == iata_b:
        return True
    for group in SAME_CITY_GROUPS:
        if iata_a in group and iata_b in group:
            return True
    return False


def check_leg_connection(prev_destination, next_origin):
    if prev_destination == next_origin:
        return True, False, False
    if same_city(prev_destination, next_origin):
        return False, True, False
    return False, False, True


def detect_route_type(origin_airport, destination_airport):
    if origin_airport is None or destination_airport is None:
        return "international", "international"
    if (origin_airport.country and destination_airport.country and
            origin_airport.country == destination_airport.country):
        return "domestic", "domestic"
    if (origin_airport.region and destination_airport.region and
            origin_airport.region == destination_airport.region):
        region_key = REGION_TO_KEY.get(
            origin_airport.region, "international"
        )
        return "regional", region_key
    dest_key = REGION_TO_KEY.get(
        destination_airport.region, "international"
    )
    return "international", dest_key


def find_or_create_global_route(origin, destination, departure_date,
                                 return_date, adults, cabin_class):
    """
    Find an existing global route matching these parameters,
    or create a new one. Returns the GlobalRoute object.
    """
    existing = GlobalRoute.query.filter_by(
        origin         = origin,
        destination    = destination,
        departure_date = departure_date,
        return_date    = return_date,
        adults         = adults,
        cabin_class    = cabin_class,
    ).first()

    if existing:
        if not existing.is_active:
            existing.is_active = True
        return existing

    route = GlobalRoute(
        origin         = origin,
        destination    = destination,
        departure_date = departure_date,
        return_date    = return_date,
        adults         = adults,
        cabin_class    = cabin_class,
    )
    db.session.add(route)
    db.session.flush()
    return route


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id                   = db.Column(db.Integer, primary_key=True)
    name                 = db.Column(db.String(100), nullable=False)
    email                = db.Column(db.String(150), unique=True, nullable=False)
    password             = db.Column(db.String(200), nullable=False)
    alert_email          = db.Column(db.String(150), nullable=True)
    is_admin             = db.Column(db.Boolean, default=False)
    created_at           = db.Column(db.DateTime,
                                     default=lambda: datetime.now(timezone.utc))
    is_active            = db.Column(db.Boolean, default=True)
    reset_token          = db.Column(db.String(100), nullable=True)
    reset_token_expires  = db.Column(db.DateTime, nullable=True)

    # Currency and preferences
    preferred_currency   = db.Column(db.String(3), default="AUD")
    airline_memberships  = db.Column(db.Text, default="[]")
    alert_emails         = db.Column(db.Text, default="[]")

    # Thresholds
    threshold_domestic      = db.Column(db.Float, default=150.00)
    threshold_oceania       = db.Column(db.Float, default=200.00)
    threshold_asia          = db.Column(db.Float, default=300.00)
    threshold_middle_east   = db.Column(db.Float, default=350.00)
    threshold_europe        = db.Column(db.Float, default=500.00)
    threshold_africa        = db.Column(db.Float, default=400.00)
    threshold_north_america = db.Column(db.Float, default=550.00)
    threshold_south_america = db.Column(db.Float, default=500.00)
    threshold_international = db.Column(db.Float, default=400.00)

    # Flight optimization preference (Traveller only)
    optimize_for             = db.Column(db.String(15),  default="cheapest")

    # Email confirmation
    email_confirmed          = db.Column(db.Boolean,     default=False)
    confirm_token            = db.Column(db.String(100), nullable=True)
    confirm_token_expires    = db.Column(db.DateTime,    nullable=True)

    # Onboarding
    onboarding_complete      = db.Column(db.Boolean, default=False)

    # Subscription
    account_type             = db.Column(db.String(20), default="self_registered")
    subscription_tier        = db.Column(db.String(20), default="trial")
    subscription_status      = db.Column(db.String(20), default="active")
    billing_period           = db.Column(db.String(10), default="monthly")
    trial_started_at         = db.Column(db.DateTime, nullable=True)
    trial_expires_at         = db.Column(db.DateTime, nullable=True)
    subscription_started_at  = db.Column(db.DateTime, nullable=True)
    subscription_period_end  = db.Column(db.DateTime, nullable=True)
    stripe_customer_id       = db.Column(db.String(100), nullable=True)
    stripe_subscription_id   = db.Column(db.String(100), nullable=True)

    # Relationships
    user_routes     = db.relationship("UserRoute", backref="user",
                                      lazy=True, cascade="all, delete-orphan")
    rtw_itineraries = db.relationship("RTWItinerary", backref="user",
                                      lazy=True, cascade="all, delete-orphan")

    # ---------------------------------------------------------------------------
    # Email helpers
    # ---------------------------------------------------------------------------

    def get_alert_email(self):
        return self.alert_email if self.alert_email else self.email

    def get_alert_emails(self):
        """All alert recipients up to tier limit."""
        try:
            extras = json.loads(self.alert_emails or "[]")
        except Exception:
            extras = []
        primary   = self.get_alert_email()
        all_emails = [primary] + [e for e in extras if e != primary]
        limit      = self.tier_config().get("max_recipients", 1)
        return all_emails[:limit]

    # ---------------------------------------------------------------------------
    # Membership helpers
    # ---------------------------------------------------------------------------

    def get_memberships(self):
        try:
            return json.loads(self.airline_memberships or "[]")
        except Exception:
            return []

    def is_member(self, airline_name):
        if not airline_name:
            return False
        memberships   = self.get_memberships()
        airline_lower = airline_name.lower()
        return any(
            m.lower() in airline_lower or airline_lower in m.lower()
            for m in memberships
        )

    # ---------------------------------------------------------------------------
    # Threshold helpers
    # ---------------------------------------------------------------------------

    def get_threshold(self, threshold_key):
        mapping = {
            "domestic":      self.threshold_domestic,
            "oceania":       self.threshold_oceania,
            "asia":          self.threshold_asia,
            "middle_east":   self.threshold_middle_east,
            "europe":        self.threshold_europe,
            "africa":        self.threshold_africa,
            "north_america": self.threshold_north_america,
            "south_america": self.threshold_south_america,
            "international": self.threshold_international,
        }
        return mapping.get(
            threshold_key,
            THRESHOLD_DEFAULTS.get(threshold_key, 400.00)
        )

    # ---------------------------------------------------------------------------
    # Subscription helpers
    # ---------------------------------------------------------------------------

    def tier_config(self):
        if self.is_admin:
            return {
                "name": "Admin", "max_routes": 9999, "max_rtw": 9999,
                "max_recipients": 99, "check_interval": 60,
                "weekly_summary": True, "recommendations": True,
            }
        return TIERS.get(self.subscription_tier or "trial", TIERS["trial"])

    def can_optimize(self):
        """Fastest / Best Value modes are Traveller-only."""
        return self.subscription_tier == "traveller" or self.is_admin

    def is_trial(self):
        return self.subscription_tier == "trial" and not self.is_admin

    def is_invited(self):
        return self.account_type == "invited"

    def is_active_subscriber(self):
        return self.subscription_tier in ("explorer", "traveller")

    def trial_active(self):
        if self.is_admin:
            return True
        if self.account_type == "invited":
            return True
        if self.subscription_tier != "trial":
            return True
        if not self.trial_expires_at:
            return True
        expires = self.trial_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < expires

    def trial_days_remaining(self):
        if not self.is_trial() or not self.trial_expires_at:
            return 0
        expires = self.trial_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return max(0, (expires - datetime.now(timezone.utc)).days)

    def can_add_route(self):
        if self.is_admin:
            return True
        count = UserRoute.query.filter_by(user_id=self.id).count()
        return count < self.tier_config()["max_routes"]

    def can_add_rtw(self):
        if self.is_admin:
            return True
        count = RTWItinerary.query.filter_by(user_id=self.id).count()
        return count < self.tier_config()["max_rtw"]

    def routes_remaining(self):
        if self.is_admin:
            return 999
        count = UserRoute.query.filter_by(user_id=self.id).count()
        return max(0, self.tier_config()["max_routes"] - count)

    def rtw_remaining(self):
        if self.is_admin:
            return 999
        count = RTWItinerary.query.filter_by(user_id=self.id).count()
        return max(0, self.tier_config()["max_rtw"] - count)

    def start_trial(self):
        now = datetime.now(timezone.utc)
        self.account_type       = "self_registered"
        self.subscription_tier  = "trial"
        self.subscription_status = "active"
        self.trial_started_at   = now
        self.trial_expires_at   = now + timedelta(days=14)

    def activate_as_invited(self):
        """Set up account as a free invited Explorer."""
        self.account_type        = "invited"
        self.subscription_tier   = "explorer"
        self.subscription_status = "active"
        self.trial_started_at    = None
        self.trial_expires_at    = None

    def skip_trial(self, tier="explorer"):
        now = datetime.now(timezone.utc)
        self.subscription_tier       = tier
        self.subscription_status     = "active"
        self.account_type            = "self_registered"
        self.trial_expires_at        = now
        self.subscription_started_at = now

    def upgrade(self, tier, billing_period="monthly"):
        now = datetime.now(timezone.utc)
        self.subscription_tier       = tier
        self.subscription_status     = "active"
        self.billing_period          = billing_period
        self.subscription_started_at = now
        if billing_period == "annual":
            self.subscription_period_end = now + timedelta(days=365)
        else:
            self.subscription_period_end = now + timedelta(days=31)
        # Invited users become self_registered when they pay
        if self.account_type == "invited":
            self.account_type = "self_registered"

    def cancel_subscription(self):
        """Mark subscription as cancelled — runs to period end."""
        self.subscription_status = "cancelled"

    def deactivate(self):
        """Deactivate account — monitoring stops immediately."""
        self.subscription_status = "deactivated"
        self.is_active           = False

    # ---------------------------------------------------------------------------
    # Auth helpers
    # ---------------------------------------------------------------------------

    def generate_confirm_token(self):
        """Generate an email confirmation token valid for 24 hours."""
        self.confirm_token         = secrets.token_urlsafe(32)
        self.confirm_token_expires = (
            datetime.now(timezone.utc) + timedelta(hours=24)
        )
        return self.confirm_token

    def confirm_token_valid(self):
        if not self.confirm_token or not self.confirm_token_expires:
            return False
        expires = self.confirm_token_expires
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < expires

    def generate_reset_token(self):
        self.reset_token         = secrets.token_urlsafe(32)
        self.reset_token_expires = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        )
        return self.reset_token

    def reset_token_valid(self):
        if not self.reset_token or not self.reset_token_expires:
            return False
        expires = self.reset_token_expires
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < expires

    def __repr__(self):
        return f"<User {self.email}>"


class Invite(db.Model):
    __tablename__ = "invites"

    id         = db.Column(db.Integer, primary_key=True)
    token      = db.Column(db.String(64), unique=True, nullable=False)
    email      = db.Column(db.String(150), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"),
                           nullable=False)
    created_at = db.Column(db.DateTime,
                           default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at    = db.Column(db.DateTime, nullable=True)
    used_by    = db.Column(db.Integer, db.ForeignKey("users.id"),
                           nullable=True)
    is_active  = db.Column(db.Boolean, default=True)

    creator = db.relationship("User", foreign_keys=[created_by])
    user    = db.relationship("User", foreign_keys=[used_by])

    def is_valid(self):
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return (
            self.is_active and
            self.used_at is None and
            datetime.now(timezone.utc) < expires
        )

    def status(self):
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if self.used_at:
            return "Used"
        if datetime.now(timezone.utc) > expires:
            return "Expired"
        if not self.is_active:
            return "Cancelled"
        return "Active"

    @staticmethod
    def generate(created_by_id, email=None, days_valid=7):
        return Invite(
            token      = secrets.token_urlsafe(32),
            email      = email,
            created_by = created_by_id,
            expires_at = (
                datetime.now(timezone.utc) + timedelta(days=days_valid)
            ),
        )

    def __repr__(self):
        return f"<Invite {self.token[:8]}... status={self.status()}>"


class Airport(db.Model):
    __tablename__ = "airports"

    id           = db.Column(db.Integer,     primary_key=True)
    iata_code    = db.Column(db.String(3),   unique=True, nullable=False)
    icao_code    = db.Column(db.String(4),   nullable=True)
    name         = db.Column(db.String(200), nullable=False)
    city         = db.Column(db.String(100), nullable=False)
    municipality = db.Column(db.String(100), nullable=True)
    country      = db.Column(db.String(100), nullable=False)
    iso_country  = db.Column(db.String(2),   nullable=True)
    region       = db.Column(db.String(50),  nullable=True)
    airport_type = db.Column(db.String(20),  nullable=True)
    latitude     = db.Column(db.Float,       nullable=True)
    longitude    = db.Column(db.Float,       nullable=True)
    is_active    = db.Column(db.Boolean,     default=True)

    def display_name(self):
        city_name = self.municipality or self.city
        return (f"{city_name} ({self.iata_code}) "
                f"— {self.name}, {self.country}")

    def is_large(self):
        return self.airport_type == "large_airport"

    def __repr__(self):
        return f"<Airport {self.iata_code} {self.city}>"


class GlobalRoute(db.Model):
    """
    One row per unique flight combination.
    Shared across all users — price history and market data
    are stored here, checked once per cycle regardless of
    how many users monitor this route.
    """
    __tablename__ = "global_routes"

    id             = db.Column(db.Integer, primary_key=True)
    origin         = db.Column(db.String(3),   nullable=False)
    destination    = db.Column(db.String(3),   nullable=False)
    departure_date = db.Column(db.String(10),  nullable=False)
    return_date    = db.Column(db.String(10),  nullable=True)
    adults         = db.Column(db.Integer,     default=1)
    cabin_class    = db.Column(db.String(20),  default="economy")
    last_checked   = db.Column(db.DateTime,    nullable=True)
    is_active      = db.Column(db.Boolean,     default=True)
    created_at     = db.Column(db.DateTime,
                               default=lambda: datetime.now(timezone.utc))

    user_routes = db.relationship("UserRoute", backref="global_route",
                                  lazy=True)
    history     = db.relationship("PriceHistory", backref="global_route",
                                  lazy=True, cascade="all, delete-orphan")
    market      = db.relationship("MarketSummary", backref="global_route",
                                  lazy=True, cascade="all, delete-orphan")

    def active_user_routes(self):
        return [ur for ur in self.user_routes if ur.is_active]

    def __repr__(self):
        return (f"<GlobalRoute {self.origin}->{self.destination} "
                f"{self.departure_date}>")


class UserRoute(db.Model):
    """
    One row per user per monitored route.
    Contains user-specific preferences and personal baseline.
    Links to a GlobalRoute for shared market data.
    """
    __tablename__ = "user_routes"

    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey("users.id"),
                                  nullable=False)
    global_route_id   = db.Column(db.Integer,
                                  db.ForeignKey("global_routes.id"),
                                  nullable=False)
    route_type        = db.Column(db.String(20),  default="international")
    optimize_for      = db.Column(db.String(15),  nullable=True)
    threshold_usd     = db.Column(db.Float,       default=400.00)
    nearby_airports   = db.Column(db.Boolean,     default=False)
    nearby_min_saving = db.Column(db.Float,       default=200.00)
    flexible_dates    = db.Column(db.Boolean,     default=False)
    flex_period_type  = db.Column(db.String(10),  default="weeks")
    flex_period_value = db.Column(db.Integer,     default=2)
    flex_duration     = db.Column(db.Boolean,     default=False)
    flex_duration_days = db.Column(db.Integer,    default=7)
    baseline_price    = db.Column(db.Float,       nullable=True)
    is_active         = db.Column(db.Boolean,     default=True)
    created_at        = db.Column(db.DateTime,
                                  default=lambda: datetime.now(timezone.utc))

    alerts = db.relationship("AlertLog", backref="user_route",
                             lazy=True, cascade="all, delete-orphan")

    def effective_optimize_for(self):
        """Route override → user default → cheapest.
        Silently downgrades to cheapest if user is not Traveller."""
        mode = self.optimize_for or self.user.optimize_for or "cheapest"
        if mode not in ("cheapest", "fastest", "best_value"):
            return "cheapest"
        if mode != "cheapest" and not self.user.can_optimize():
            return "cheapest"
        return mode

    def flex_days(self):
        if not self.flexible_dates:
            return 0
        if self.flex_period_type == "weeks":
            return (self.flex_period_value or 2) * 7
        return self.flex_period_value or 14

    def __repr__(self):
        return (f"<UserRoute user={self.user_id} "
                f"global={self.global_route_id}>")


class PriceHistory(db.Model):
    """
    One row per offer per check — stored against global_route.
    Shared across all users monitoring the same route.
    """
    __tablename__ = "price_history"

    id              = db.Column(db.Integer, primary_key=True)
    global_route_id = db.Column(db.Integer,
                                db.ForeignKey("global_routes.id"),
                                nullable=True)
    # Legacy column — kept for backward compatibility
    route_id        = db.Column(db.Integer, nullable=True)
    price           = db.Column(db.Float,       nullable=False)
    currency        = db.Column(db.String(3),   nullable=False)
    airline         = db.Column(db.String(100), nullable=True)
    stops            = db.Column(db.Integer,     nullable=True)
    duration_minutes = db.Column(db.Integer,     nullable=True)
    is_cheapest      = db.Column(db.Boolean,     default=False)
    checked_date    = db.Column(db.String(10),  nullable=True)
    checked_at      = db.Column(db.DateTime,
                                default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return (f"<PriceHistory global_route={self.global_route_id} "
                f"price={self.price}>")


class MarketSummary(db.Model):
    """
    One row per global_route per check — aggregated market metrics.
    Shared across all users monitoring the same route.
    """
    __tablename__ = "market_summary"

    id              = db.Column(db.Integer, primary_key=True)
    global_route_id = db.Column(db.Integer,
                                db.ForeignKey("global_routes.id"),
                                nullable=True)
    # Legacy column — kept for backward compatibility
    route_id        = db.Column(db.Integer, nullable=True)
    checked_at      = db.Column(db.DateTime,
                                default=lambda: datetime.now(timezone.utc))
    checked_date    = db.Column(db.String(10),  nullable=True)
    market_min      = db.Column(db.Float,       nullable=False)
    market_median   = db.Column(db.Float,       nullable=False)
    market_mean     = db.Column(db.Float,       nullable=False)
    offer_count     = db.Column(db.Integer,     nullable=False)
    cheapest_airline = db.Column(db.String(100), nullable=True)
    currency        = db.Column(db.String(3),   nullable=True)

    def __repr__(self):
        return (f"<MarketSummary global_route={self.global_route_id} "
                f"min={self.market_min}>")


class AlertLog(db.Model):
    """
    One row per alert sent — stored against user_route.
    Personal — each user has their own alert history.
    Never scrubbed.
    """
    __tablename__ = "alert_log"

    id             = db.Column(db.Integer, primary_key=True)
    user_route_id  = db.Column(db.Integer,
                               db.ForeignKey("user_routes.id"),
                               nullable=True)
    # Legacy column — kept for backward compatibility
    route_id       = db.Column(db.Integer, nullable=True)
    baseline_price = db.Column(db.Float,       nullable=False)
    alerted_price  = db.Column(db.Float,       nullable=False)
    drop_amount    = db.Column(db.Float,       nullable=False)
    currency       = db.Column(db.String(3),   nullable=False)
    airline        = db.Column(db.String(100), nullable=True)
    alert_type     = db.Column(db.String(20),  default="sudden_sale")
    historic_avg   = db.Column(db.Float,       nullable=True)
    sent_at        = db.Column(db.DateTime,
                               default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return (f"<AlertLog user_route={self.user_route_id} "
                f"type={self.alert_type}>")


class AppConfig(db.Model):
    """
    Admin-editable key/value configuration parameters.
    Used for tunable system settings such as effective-cost coefficients.
    """
    __tablename__ = "app_config"

    id         = db.Column(db.Integer,     primary_key=True)
    key        = db.Column(db.String(100), unique=True, nullable=False)
    value      = db.Column(db.Text,        nullable=False)
    updated_at = db.Column(db.DateTime,
                           default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<AppConfig {self.key}={self.value}>"


class RTWItinerary(db.Model):
    __tablename__ = "rtw_itineraries"

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"),
                               nullable=False)
    name           = db.Column(db.String(200), nullable=False)
    is_active      = db.Column(db.Boolean,    default=True)
    created_at     = db.Column(db.DateTime,
                               default=lambda: datetime.now(timezone.utc))
    baseline_total = db.Column(db.Float,      nullable=True)
    last_total     = db.Column(db.Float,      nullable=True)
    last_currency  = db.Column(db.String(3),  nullable=True)
    last_checked   = db.Column(db.DateTime,   nullable=True)
    threshold_usd  = db.Column(db.Float,      default=600.00)

    legs = db.relationship("RTWLeg", backref="itinerary", lazy=True,
                           cascade="all, delete-orphan",
                           order_by="RTWLeg.leg_order")

    def __repr__(self):
        return f"<RTWItinerary {self.name} user={self.user_id}>"


class RTWLeg(db.Model):
    __tablename__ = "rtw_legs"

    id                 = db.Column(db.Integer, primary_key=True)
    itinerary_id       = db.Column(db.Integer,
                                   db.ForeignKey("rtw_itineraries.id"),
                                   nullable=False)
    leg_order          = db.Column(db.Integer,    nullable=False)
    origin             = db.Column(db.String(3),  nullable=False)
    destination        = db.Column(db.String(3),  nullable=False)
    departure_date     = db.Column(db.String(10), nullable=False)
    cabin_class        = db.Column(db.String(20), default="economy")
    adults             = db.Column(db.Integer,    default=1)
    is_surface_segment = db.Column(db.Boolean,    default=False)
    last_price         = db.Column(db.Float,      nullable=True)
    last_currency      = db.Column(db.String(3),  nullable=True)
    last_airline       = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return (f"<RTWLeg {self.leg_order}: "
                f"{self.origin}->{self.destination}>")
