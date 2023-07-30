import json
import logging
import os
import time
from datetime import datetime

import requests
import slack_bolt
from Event import Event
from Singleton import Singleton


class SlackApp(metaclass=Singleton):
    QUIET_HOURS_END = 8  # 8:00 AM
    QUIET_HOURS_START = 21  # 9:00 PM

    def __init__(self, token: str, secret: str, message_queue_filepath: str):
        if not os.path.exists(message_queue_filepath):
            raise Exception("Message queue filepath not found")
        self.message_queue_filepath = message_queue_filepath
        self.messages_queued = self._are_messages_queued()
        # self.app = slack_bolt.App(token=token, signing_secret=secret)
        # self.app.start()
        logging.info("Launched Slack app")

    def _in_quiet_hrs(self) -> bool:
        """Determine whether quiet hours are currently in effect"""
        hr = datetime.now().hour
        return not (self.QUIET_HOURS_END <= hr < self.QUIET_HOURS_START)

    def _are_messages_queued(self) -> bool:
        """Check whether messages remain in the message queue"""
        try:
            with open(self.message_queue_filepath, "r") as f:
                data = json.loads(f.read() or "[]")
                return len(data) != 0
        except Exception as e:
            logging.error(f"Error checking if messages queued: {e}")
            return False

    def send_message(self, user_id: str, msg):
        try:
            msg = str(msg)
            if self._in_quiet_hrs():
                self._queue_message(user_id, msg)
                return
            # result = requests.post(
            #     "https://slack.com/api/chat.postMessage",
            #     params={"token": self.token, "channel": user_id, "text": msg},
            # )
            # print(result.status_code)
            # if result.status_code == 200:
            #     logging.info("Posted message to Slack")
            # else:
            #     logging.error("Could not post message to Slack")
            result = self.app.client.chat_postMessage("D" + user_id, msg)
            logging.info(str(result))
        except Exception as e:
            logging.error(f"Error posting message to Slack: {e}")

    def send_multiple(self, users: list[str], msg):
        """Send the same message to a list of Slack IDs"""
        for u in users:
            self.send_message(u, msg)

    def _queue_message(self, user_id: str, msg: str):
        """Queue a message to be sent outside of quiet hours"""
        # TODO: Add some more error handling for malformed JSON
        try:
            with open(self.message_queue_filepath, "r+") as f:
                data = json.loads(f.read() or "[]")
                data.append({"user_id": user_id, "msg": msg})
                f.seek(0)
                f.truncate()
                f.write(json.dumps(data))
            logging.info(f"Queued message to {user_id}")
            self.messages_queued = True
        except Exception as e:
            logging.error(f"Error when queueing message: {e}")

    def send_queued_messages(self):
        """Send all messages that have been queued"""
        try:
            if not self.messages_queued or self._in_quiet_hrs():
                return
            with open(self.message_queue_filepath, "r+") as f:
                data = json.loads(f.read() or "[]")
                for m in data:
                    self.send_message(m["user_id"], m["msg"])
                    logging.info(f"Sent queued message to {m['user_id']}")
                logging.info(f"Sent {len(data)} queued message(s)")
                f.seek(0)
                f.truncate()
                f.write("[]")
            self.messages_queued = False
        except Exception as e:
            logging.error(f"Error when sending queued message(s): {e}")

    def get_new_events(self) -> list[Event]:
        try:
            events = []

            return events
        except Exception as e:
            logging.error(f"Error when fetching new events: {e}")
