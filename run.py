import logging
import sys
from app import create_app
from app.monitor import start_scheduler

# Set up logging before anything else
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("flight_alert.log"),
    ],
)
log = logging.getLogger(__name__)
app = create_app()

if __name__ == "__main__":
    run_check = "--check" in sys.argv

    log.info("Starting Flight Monitor...")

    if run_check:
        from app.monitor import check_all_routes, check_rtw_itineraries
        log.info("Running initial price check...")
        check_all_routes(app)
        check_rtw_itineraries(app)
    else:
        log.info("Skipping initial check — scheduler will run on interval")

    start_scheduler(app)
    log.info("Starting web server on http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
