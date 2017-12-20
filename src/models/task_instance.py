from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Boolean, Date, Integer

from base import Base


class TaskInstance(Base):
    __tablename__ = 'taskinstances'

    id = Column(Integer, primary_key=True)
    task = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    date = Column(Date, nullable=False)
    done = Column(Boolean, default=False)
