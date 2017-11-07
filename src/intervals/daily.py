from datetime import timedelta

from base_interval import BaseInterval


class DailyInterval(BaseInterval):
    @staticmethod
    def next_interval(start_date):
        return start_date + timedelta(days=1)
