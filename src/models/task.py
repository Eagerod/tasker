from sqlalchemy.schema import Column
from sqlalchemy.types import Date, Integer, String

from base import Base


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    name = Column(String(1024), nullable=False)
    cadence = Column(String(256), nullable=False)
    start = Column(Date, nullable=False)
