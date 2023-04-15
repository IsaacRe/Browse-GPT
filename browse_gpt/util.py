from typing import List, Tuple
from hashlib import md5
from datetime import datetime, timedelta


def query_user_action():
    return input("Input a description of the action taken to continue (skip input to bypass override)")


def hash_url(url: str):
    return md5(url.split("//")[1].encode("utf-8")).hexdigest()


def timer() -> "TimerContext":
    return TimerContext()


class Timer:
    def __init__(self):
        self.start_time: datetime = None
        self.end_time: datetime = None
        self.duration: timedelta = None
        self.laps: List[Tuple[datetime, timedelta]] = []

    def start(self):
        self.start_time = datetime.utcnow()

    def end(self, *_):
        self.end_time = datetime.utcnow()
        self.duration = self.end_time - self.start_time

    def seconds(self):
        if self.duration:
            return self.duration.total_seconds()
        t = datetime.utcnow()
        lap = t - self.start_time
        self.laps += [(t, lap)]
        return lap


class TimerContext:
    def __init__(self):
        self.timer = Timer()

    def __enter__(self):
        self.timer.start()
        return self.timer

    def __exit__(self, *_):
        self.timer.end()
