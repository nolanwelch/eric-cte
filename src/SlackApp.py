import json
import os
import time
from datetime import datetime
from logging import Logger

import requests
import slack_bolt
from Event import Event
from Singleton import Singleton


class SlackApp(metaclass=Singleton):
    QUIET_HOURS_END = 8  # 8:00 AM
    QUIET_HOURS_START = 21  # 9:00 PM

    def __init__(
        self, logger: Logger, token: str, secret: str, message_queue_filepath: str
    ):
        if not os.path.exists(message_queue_filepath):
            raise Exception("Message queue filepath not found")
        self._logger = logger
        self._message_queue_filepath = message_queue_filepath
        self._messages_queued = self._are_messages_queued()
        self._token = token
        self._secret = secret

    def _in_quiet_hrs(self) -> bool:
        """Determine whether quiet hours are currently in effect"""
        hr = datetime.now().hour
        return not (self.QUIET_HOURS_END <= hr < self.QUIET_HOURS_START)

    def _are_messages_queued(self) -> bool:
        """Check whether messages remain in the message queue"""
        try:
            with open(self._message_queue_filepath, "r") as f:
                data = json.loads(f.read() or "[]")
                return len(data) != 0
        except Exception as e:
            self._logger.error(f"Error checking if messages queued: {e}")
            return False

    def send_message(self, channel_id: str, msg):
        try:
            msg = str(msg)
            if self._in_quiet_hrs():
                self._queue_message(channel_id, msg)
                return
            result = requests.post(
                "https://slack.com/api/chat.postMessage",
                params={"channel": channel_id, "text": msg},
                headers={"Authorization": f"Bearer {self._token}"},
            )
            if result.status_code == 200 and result.json()["ok"]:
                self._logger.info("Posted message to Slack")
            else:
                self._logger.error("Could not post message to Slack")
        except Exception as e:
            self._logger.error(f"Error posting message to Slack: {e}")

    def send_multiple(self, users: list[str], msg):
        """Send the same message to a list of Slack IDs"""
        for u in users:
            self.send_message(u, msg)

    def _queue_message(self, user_id: str, msg):
        """Queue a message to be sent outside of quiet hours"""
        # TODO: Add some more error handling for malformed JSON
        try:
            with open(self._message_queue_filepath, "r+") as f:
                data = json.loads(f.read() or "[]")
                data.append({"user_id": user_id, "msg": str(msg)})
                f.seek(0)
                f.truncate()
                f.write(json.dumps(data))
            self._logger.info(f"Queued message to {user_id}")
            self._messages_queued = True
        except Exception as e:
            self._logger.error(f"Error when queueing message: {e}")

    def send_queued_messages(self):
        """Send all messages that have been queued"""
        try:
            if not self._messages_queued or self._in_quiet_hrs():
                return
            with open(self._message_queue_filepath, "r+") as f:
                data = json.loads(f.read() or "[]")
                for m in data:
                    self.send_message(m["user_id"], m["msg"])
                    self._logger.info(f"Sent queued message to {m['user_id']}")
                self._logger.info(f"Sent {len(data)} queued message(s)")
                f.seek(0)
                f.truncate()
                f.write("[]")
            self._messages_queued = False
        except Exception as e:
            self._logger.error(f"Error when sending queued message(s): {e}")

    # TODO: Write this method!
    def fetch_new_events(self) -> list[Event]:
        """Uses the Slack API to fetch new message/react Events"""
        try:
            events = []
            return events
        except Exception as e:
            self._logger.error(f"Error when fetching new events: {e}")
