from sqlalchemy.schema import Column
from sqlalchemy.types import Date, Integer, String

from base import Base


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    cadence = Column(String, nullable=False)
    start = Column(Date, nullable=False)
