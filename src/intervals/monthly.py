from base_interval import BaseInterval


class MonthlyInterval(BaseInterval):
    @staticmethod
    def next_interval(start_date):
        # No "month" timedelta :(
        if start_date.month == 12:
            return start_date.replace(year=start_date.year + 1, month=1)
        return start_date.replace(month=start_date.month + 1)

    @staticmethod
    def is_compatible(date):
        return date.day <= 28