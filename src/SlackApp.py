from datetime import datetime, time, timezone, timedelta
from logging import Logger
from time import sleep

import requests

USERAGENT = "ERIC-CTE/1.0 (nolanwelch@outlook.com)"


class MessageResponse:
    def __init__(self, resolved_channel_id: str, timestamp: datetime, message):
        if not resolved_channel_id:
            raise ValueError("Resolved channel ID cannot be empty")
        elif timestamp is None or not isinstance(timestamp, datetime):
            raise TypeError("Timestamp must be a datetime")
        elif message is None:
            raise TypeError("Message cannot be None")

        self.resolved_channel_id = resolved_channel_id
        self.timestamp = timestamp
        self.message = str(message)


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

        self._logger = logger
        self._token = token
        self._quiet_hours_start = quiet_hours_start
        self._quiet_hours_end = quiet_hours_end

    def in_quiet_hrs(self, dt: datetime = datetime.now()) -> bool:
        """Determine whether quiet hours are in effect for a given datetime"""
        t = dt.time()
        if self._quiet_hours_start < self._quiet_hours_end:
            return t >= self._quiet_hours_start and t <= self._quiet_hours_end
        else:  # quiet hours cross midnight
            return t >= self._quiet_hours_start or t <= self._quiet_hours_end

    def send_message(self, channel_id: str, msg) -> MessageResponse:
        try:
            if self.in_quiet_hrs():
                now = datetime.now()
                if now.hour >= self._quiet_hours_start.hour:
                    now += timedelta(days=1)
                schedule_dt = datetime(
                    now.year,
                    now.month,
                    now.day,
                    self._quiet_hours_end.hour,
                    self._quiet_hours_end.minute,
                    0,
                )
                return self.schedule_message(channel_id, schedule_dt, msg)
            result = requests.post(
                "https://slack.com/api/chat.postMessage",
                json={"channel": channel_id, "text": str(msg)},
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-type": "application/json",
                    "User-Agent": USERAGENT,
                },
            )
            if result.status_code == 200 and result.json()["ok"]:
                self._logger.info("Posted message to Slack")
                data = result.json()
                timestamp = float(data["message"]["ts"])
                timestamp = datetime.fromtimestamp(timestamp, timezone.utc)
                return MessageResponse(data["channel"], timestamp, msg)
            else:
                self._logger.warning(
                    f"Could not post message to Slack (status code {result.status_code})"
                )
                return None
        except Exception as e:
            self._logger.error(f"Error posting message to Slack: {e}")
            return None

    def send_multiple(self, channel_ids: list[str], msg) -> list[MessageResponse]:
        """Send the same message to a list of Slack IDs"""
        responses = []
        for id in channel_ids:
            responses.append(self.send_message(id, msg))
            sleep(1)  # respect the rate limit
        return responses

    def schedule_message(self, channel_id: str, dt: datetime, msg) -> MessageResponse:
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
                    "User-Agent": USERAGENT,
                },
            )
            self._logger.error(result.json())
            if result.status_code == 200 and result.json()["ok"]:
                self._logger.info("Scheduled Slack message")
                data = result.json()
                return MessageResponse(data["channel"], dt, msg)
            else:
                self._logger.warning(
                    f"Could not schedule Slack message (status code {result.status_code})"
                )
                return None
        except Exception as e:
            self._logger.error(f"Error queueing Slack message: {e}")
            return None

    def fetch_timestamp(self, msg: MessageResponse) -> datetime:
        """Uses the Slack API to get the timestamp of a scheduled message
        given its corresponding MessageResponse object"""
        if msg is None:
            return None
        try:
            result = requests.get(
                "https://slack.com/api/conversations.history",
                params={
                    "channel": msg.resolved_channel_id,
                    "oldest": msg.timestamp.timestamp() - 5,
                },
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "User-Agent": USERAGENT,
                },
            )
            if result.status_code == 200 and result.json()["ok"]:
                self._logger.info("Fetched Slack history")
                data = result.json()
                for m in data["messages"]:
                    if m["text"] == msg.message:
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
