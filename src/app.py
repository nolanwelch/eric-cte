import datetime as dt
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from time import sleep

import pytz
import requests
from Booking import Booking
from Database import Database
from dotenv import dotenv_values
from Secrets import secret_keys
from SlackApp import SlackApp

LOCAL_TIMEZONE = pytz.timezone("America/New_York")
USERAGENT = "ERIC-CTE/1.0 (nolanwelch@outlook.com)"

# TODO
# - Add functionality to check for updates made to bookings (namely, new/modified PIDs)
# - Write tests for all classes and methods
# - Restructure try/catch and Exception raising (https://stackoverflow.com/a/18679131/8344620))

# TODO: Future plans
# - Fetch emails via SMTP to update local on-campus roster


def get_secrets(filepath: str) -> dict[str, str | None]:
    if not os.path.exists(filepath):
        raise OSError(f"Filepath {filepath} does not exist")
    return dotenv_values(filepath)


def validate_secrets(secret_dict: dict, keys: list[str]) -> None:
    for s in keys:
        if s not in secret_dict.keys():
            raise KeyError(f"Secret {s} not found in config")
        elif not secret_dict[s]:
            raise ValueError(f"Value for secret {s} is empty")
    logging.info("Secrets validated")


def connected_to_internet() -> bool:
    try:
        _ = requests.head("http://www.google.com", timeout=5)
        return True
    except:
        return False


def main():
    logger = logging.getLogger("eric-cte")
    secrets = get_secrets("config.env")
    validate_secrets(secrets, secret_keys)

    fh = TimedRotatingFileHandler(
        filename=secrets["LOG_PATH"],
        when="midnight",
        backupCount=60,
        encoding="utf-8",
    )
    fh.setFormatter(
        logging.Formatter("%(asctime)s;%(levelname)s;%(message)s", "%Y-%m-%d %H:%M:%S")
    )
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)

    slack = SlackApp(
        logger,
        secrets["SLACK_BOT_TOKEN"],
        quiet_hours_start=dt.time(hour=21),
        quiet_hours_end=dt.time(hour=8),
    )
    db = Database(
        logger,
        secrets["CTE_DB_PATH"],
        secrets["CAMPUS_ROSTER_PATH"],
        secrets["BOOKEO_SECRET_KEY"],
        secrets["BOOKEO_API_KEY"],
    )

    admins = db.get_admins()
    admin_slack_ids = [db.get_slack_id(a.employee_id) for a in admins]

    last_fetch = dt.datetime.fromtimestamp(0)

    while True:
        while not connected_to_internet():
            logger.error("No Internet connection")
            sleep(60)

        # Update local database
        db.clear()
        fetch_delta = dt.timedelta(days=31)
        bookings: list[Booking] = []
        if dt.datetime.now() - last_fetch > dt.timedelta(minutes=5):
            last_fetch = dt.datetime.now()
            bookings = db.fetch_bookings(fetch_delta)
            db.insert_new_bookings(bookings)

        for b in bookings:
            booking_datetime = b.start.astimezone(LOCAL_TIMEZONE)
            booking_date = booking_datetime.strftime("%A, %B %-d")
            # Check for invalid on-campus PIDs
            pids = db.get_on_campus_pids(b.id)
            pids = [p for p in pids if p != db.get_matching_pid(p)]
            if not db.admin_notified_pids(b) and pids:
                m = f":x: There are some invalid on-campus PIDs in booking *{b.id}* on {booking_date}. "
                m += f"They are: {', '.join(f'*{p.id}* ({p.last_name}, {p.first_name})' for p in pids)}. "
                m += f"Contact email: {b.email}"
                slack.send_multiple(admin_slack_ids, m)
                db.mark_admin_notified_pids(b)
                for p in pids:
                    db.remove_pid(p)

        sleep(30)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    os.chdir("..")
    logging.basicConfig(level=logging.INFO)
    main()
