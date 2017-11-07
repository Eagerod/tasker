class BaseInterval(object):
    @staticmethod
    def next_interval(date):
        """
        Return the interval that should come after the one passed in.

        :param date: The date from which to calculate the next interval.
        """
        raise NotImplementedError

    @staticmethod
    def is_compatible(date):
        """
        Return true if the date provided is compatible for future intervals to be created properly.
        """
        return True

    @staticmethod
    def approximate_period():
        """
        Return the approximate number of days between each interval. Used for sorting purposes.
        """
        raise NotImplementedError
