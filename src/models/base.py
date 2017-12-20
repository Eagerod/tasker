from sqlalchemy.ext.declarative import declarative_base


_Base = declarative_base()


class Base(_Base):
    __abstract__ = True

    def __eq__(self, other):
        if self is other:
            return True

        if not type(other) == type(self):
            return False

        # Don't allow for comparison of abstract base models.
        if not hasattr(self, '__table__'):
            return False

        # Same types, so same columns
        for column in self.__table__.columns:
            if not getattr(self, column.name) == getattr(other, column.name):
                return False

        return True

    def __repr__(self):
        column_str = ' '.join('{}={}'.format(c, getattr(self, c.name)) for c in self.__table__.columns)
        return '<{} at {}: {}>'.format(type(self).__name__, id(self), column_str)
