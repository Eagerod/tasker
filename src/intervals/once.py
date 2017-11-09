from base_interval import BaseInterval


class OnceInterval(BaseInterval):
    @staticmethod
    def next_interval(start_date):
        return start_date

    @staticmethod
    def approximate_period():
        return 0
