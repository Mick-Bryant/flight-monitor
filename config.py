import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    APP_NAME = os.getenv("APP_NAME", "Flight Monitor")

    # Security key for sessions and forms — keep this secret
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")

    # Database — SQLite file in the project folder
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///flight_monitor.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Duffel API
    DUFFEL_ACCESS_TOKEN = os.getenv("DUFFEL_ACCESS_TOKEN", "")
    DUFFEL_API_URL      = "https://api.duffel.com"
    DUFFEL_API_VERSION  = "v2"

    # SendGrid
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
    ALERT_FROM_EMAIL = os.getenv("ALERT_FROM_EMAIL", "")

    # Price monitor settings
    CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 60))
    ALERT_THRESHOLD_USD    = float(os.getenv("ALERT_THRESHOLD_USD", 400.00))
