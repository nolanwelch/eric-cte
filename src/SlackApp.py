from datetime import datetime, time, timezone
from logging import Logger

import requests


class Message:
    def __init__(self, resolved_channel_id: str, timestamp: datetime, message):
        if resolved_channel_id == "":
            raise ValueError("Resolved channel ID cannot be empty")
        elif timestamp is None or not isinstance(timestamp, datetime):
            raise TypeError("Timestamp must be a datetime")
        elif message is None:
            raise TypeError("Message cannot be None")

        self.resolved_channel_id = resolved_channel_id
        self.timestamp = timestamp
        self.message = message


class SlackApp:
    def __init__(
        self,
        logger: Logger,
        token: str,
        quiet_hours_start: time,
        quiet_hours_end: time,
    ):
        if None in (quiet_hours_start, quiet_hours_end):
            raise TypeError("Quiet hours cannot be None")
        elif quiet_hours_end >= quiet_hours_start:
            raise ValueError("Quiet hours end time must be before the start time")

        self._logger = logger
        self._token = token
        self._quiet_hours_start = quiet_hours_start
        self._quiet_hours_end = quiet_hours_end

    def in_quiet_hrs(self, dt: datetime = datetime.now()) -> bool:
        """Determine whether quiet hours are in effect for a given datetime"""
        t = time(dt.hour, dt.minute)
        return not (self._quiet_hours_end <= t < self._quiet_hours_start)

    def send_message(self, channel_id: str, msg) -> Message:
        try:
            if self.in_quiet_hrs():
                return self.schedule_message(channel_id, datetime, msg)
            result = requests.post(
                "https://slack.com/api/chat.postMessage",
                json={"channel": channel_id, "text": str(msg)},
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-type": "application/json",
                },
            )
            if result.status_code == 200 and result.json()["ok"]:
                self._logger.info("Posted message to Slack")
                data = result.json()
                timestamp = float(data["message"]["ts"])
                timestamp = datetime.fromtimestamp(timestamp, timezone.utc)
                return Message(data["channel"], timestamp, msg)
            else:
                self._logger.warning(
                    f"Could not post message to Slack (status code {result.status_code})"
                )
                return None
        except Exception as e:
            self._logger.error(f"Error posting message to Slack: {e}")
            return None

    def send_multiple(self, channel_ids: list[str], msg) -> list[Message]:
        """Send the same message to a list of Slack IDs"""
        return [self.send_message(id, msg) for id in channel_ids]

    def schedule_message(self, channel_id: str, dt: datetime, msg) -> Message:
        """Schedule a message to be sent at the given datetime"""
        try:
            result = requests.post(
                "https://slack.com/api/chat.scheduleMessage",
                json={
                    "channel": channel_id,
                    "text": str(msg),
                    "post_at": dt.timestamp(),
                },
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-type": "application/json",
                },
            )
            if result.status_code == 200 and result.json()["ok"]:
                self._logger.info("Scheduled Slack message")
                data = result.json()
                return Message(data["channel"], dt, msg)
            else:
                self._logger.warning(
                    f"Could not schedule Slack message (status code {result.status_code})"
                )
                return None
        except Exception as e:
            self._logger.error(f"Error queueing Slack message: {e}")
            return None

    def message_has_reaction(self, message: Message, reaction: str) -> bool:
        """Uses the Slack API to check if the specified Message has the given reaction applied"""
        try:
            if reaction == "thumbsup":
                reaction = "+1"

            result = requests.get(
                "https://slack.com/api/reactions.get",
                params={
                    "channel": message.resolved_channel_id,
                    "timestamp": message.timestamp.timestamp(),
                },
                headers={"Authorization": f"Bearer {self._token}"},
            )
            if result.status_code == 200 and result.json()["ok"]:
                self._logger.info("Fetched reactions from Slack")
                data = result.json()
                for r in data["message"]["reactions"]:
                    if r["name"] == reaction:
                        return True
                return False
            else:
                self._logger.warning(
                    f"Could not fetch reactions from Slack (status code {result.status_code})"
                )
                return False
        except Exception as e:
            self._logger.error(f"Error when checking for reaction: {e}")
            return False

    def fetch_timestamp(self, message: Message) -> datetime:
        """Uses the Slack API to get the timestamp of a scheduled message
        given its corresponding Message object"""
        if message is None:
            return None
        try:
            result = requests.get(
                "https://slack.com/api/conversations.history",
                params={
                    "channel": message.resolved_channel_id,
                    "oldest": message.timestamp.timestamp() - 5,
                },
                headers={"Authorization": f"Bearer {self._token}"},
            )
            if result.status_code == 200 and result.json()["ok"]:
                self._logger.info("Fetched Slack history")
                data = result.json()
                for m in data["messages"]:
                    if m["text"] == message.message:
                        timestamp = float(m["ts"])
                        timestamp = datetime.fromtimestamp(timestamp, timezone.utc)
                        return timestamp
                return None
            else:
                self._logger.warning(
                    f"Could not fetch Slack history (status code {result.status_code})"
                )
                return None
        except Exception as e:
            self._logger.error(f"Error fetching Slack history: {e}")
            return None

    def update_message(self, message: Message) -> Message:
        """Update a Message object to have the most recent timestamp data"""
        try:
            if message is None:
                return None
            ts = self.fetch_timestamp(message)
            if ts is None:
                return None
            return Message(message.resolved_channel_id, ts, message.message)
        except Exception as e:
            self._logger.error(f"Error updating Message timestamp: {e}")
            return message

    def delete_message(self, message: Message):
        try:
            if message is None:
                return
            result = requests.post(
                "https://slack.com/api/chat.delete",
                params={
                    "channel": message.resolved_channel_id,
                    "ts": message.timestamp.timestamp(),
                },
                headers={"Authorization": f"Bearer {self._token}"},
            )
            if result.status_code == 200 and result.json()["ok"]:
                self._logger.info("Deleted message from Slack")
            else:
                self._logger.warning("Could not delete message from Slack")
        except Exception as e:
            self._logger.error(f"Error deleting message: {e}")
