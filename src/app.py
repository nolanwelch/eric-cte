import logging
import os
import sys
import time
from datetime import timedelta

from Database import Database
from dotenv import dotenv_values
from SlackApp import SlackApp
from SlingApp import SlingApp

BOOKING_FETCH_DELAY_SECS = 300
SLACK_QUEUE_DELAY_SECS = 600
SLING_TTL_SECS = 86_400

QUIET_HOURS_END = 8  # 8:00 AM
QUIET_HOURS_START = 21  # 9:00 PM

os.chdir(os.path.dirname(os.path.realpath(__file__)))

# TODO LIST
# - Graph program logic flow
# - Get shifts from Sling for given date
# - Listen for Slack reactions and check against ID
# - Perform on-campus PID checks when new booking detected/sent
# - Figure out why logging isn't printing


def get_secrets(filepath: str) -> dict[str, str | None]:
    if not os.path.exists(filepath):
        raise Exception(f"Filepath {filepath} does not exist")
    return dotenv_values(filepath)


def validate_secrets(secrets: dict) -> None:
    keys = [
        "BOOKEO_API_KEY",
        "BOOKEO_SECRET_KEY",
        "CAMPUS_ROSTER_PATH",
        "CTE_DB_PATH",
        "SLACK_BOT_TOKEN",
        "SLACK_SIGNING_SECRET",
        "SLING_USERNAME",
        "SLING_PASSWORD",
        "MSG_QUEUE_PATH",
        "LOG_PATH",
    ]
    for s in keys:
        if s not in secrets.keys():
            raise KeyError(f"Secret {s} not found in config")
        elif not secrets[s]:
            raise ValueError(f"Value for secret {s} is empty")
    logging.info("Secrets validated")


def main():
    secrets = get_secrets("config.env")
    validate_secrets(secrets)
    sling = SlingApp(
        secrets["SLING_USERNAME"], secrets["SLING_PASSWORD"], SLING_TTL_SECS
    )
    db = Database(
        secrets["CTE_DB_PATH"],
        secrets["CAMPUS_ROSTER_PATH"],
        secrets["BOOKEO_SECRET_KEY"],
        secrets["BOOKEO_API_KEY"],
    )
    slack = SlackApp(
        secrets["SLACK_BOT_TOKEN"],
        secrets["SLACK_SIGNING_SECRET"],
        secrets["MSG_QUEUE_PATH"],
        QUIET_HOURS_START,
        QUIET_HOURS_END,
    )
    last_queue_check = -1
    last_booking_fetch = -1

    admins = db.get_admins()

    while True:
        curr_time = time.time()

        if curr_time - last_booking_fetch > BOOKING_FETCH_DELAY_SECS:
            # TODO: Fix this loopy spaghetti code
            last_booking_fetch = curr_time
            bookings = db.fetch_bookings(timedelta(weeks=1))
            for b in bookings:
                b["employeeID"] = sling.fetch_employee_id(b["startTime"])
            db.update_database(bookings)
            new_pids = db.fetch_new_on_campus_pids()
            invalid_pids = [p for p in new_pids if not db.is_on_campus_student(p)]
            if invalid_pids:
                # Make note in DB that admin has been notified
                # Notify admin
                for a in admins:
                    # TODO: Add system to tie booking ID and names to PIDs. Use SQL queries.
                    slack.send_message(
                        a["slackID"],
                        f"Hey {a['firstName']}, there are some invalid on-campus PIDs in bookings {0}. They are: {0}",
                    )
            for b in bookings:
                # TODO: For each new booking, notify the employee assigned to the shift
                pass
            # TODO: Check for replies from Slack
            events = []
            if events:
                for a in admins:
                    slack.send_message(a["slackID"], "An event has happened!")
        if curr_time - last_queue_check > SLACK_QUEUE_DELAY_SECS:
            last_queue_check = curr_time
            slack.send_queued_messages()


def test():
    secrets = get_secrets("config.env")
    validate_secrets(secrets)
    slack = SlackApp(
        secrets["SLACK_BOT_TOKEN"],
        secrets["SLACK_SIGNING_SECRET"],
        secrets["MSG_QUEUE_PATH"],
        QUIET_HOURS_START,
        QUIET_HOURS_END,
    )
    slack.send_message("U05F0L9LN3G", "This is a test!")
    # sling = SlingApp(
    #     secrets["SLING_USERNAME"], secrets["SLING_PASSWORD"], SLING_TTL_SECS
    # )
    # dt = datetime.fromtimestamp(1688139900).strftime(r"%Y-%m-%dT%H:%M:00Z")
    # print(dt)
    # print(sling.fetch_employee_id(dt))
    sys.exit()


if __name__ == "__main__":
    # test()
    main()
