from datetime import timedelta

from base_interval import BaseInterval


class WeeklyInterval(BaseInterval):
    @staticmethod
    def next_interval(start_date):
        return start_date + timedelta(days=7)

    @staticmethod
    def approximate_period():
        return 7
