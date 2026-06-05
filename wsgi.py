"""
Production entry point for Gunicorn.
Run with:
    gunicorn --bind 0.0.0.0:5000 --workers 2 wsgi:app
"""
import logging
from app import create_app
from app.monitor import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("flight_alert.log"),
    ],
)

app = create_app()

# Start the background price checker
start_scheduler(app)
