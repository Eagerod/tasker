from datetime import date

from sqlalchemy import func
from sqlalchemy.types import Boolean
from sqlalchemy.sql.expression import and_, literal_column

from intervals.interval_factory import IntervalFactory, UnsupportedIntervalException
from models import Task, TaskInstance


class TaskerException(Exception):
    pass


class DuplicateNameException(TaskerException):
    pass


class InvalidStartDateException(TaskerException):
    pass


class InvalidCadenceException(TaskerException):
    pass


class Tasker(object):
    """
    Class that manages recurring tasks in an SQLAlchemy managed database.
    """
    def __init__(self, database):
        """
        :param database: An SQLAlchemy database session.
        """
        self.db = database

    def _get_next_date(self, cadence, start_date, last_date):
        """
        Get the next scheduleable date for a given start date and last scheduled date.

        :param cadence: Schedule cadence for the task being checked.
        :param start_date: The date the initial task was scheduled.
        :param last_date: The last date a task instance was scheduled.
        """
        if not last_date:
            return start_date

        return IntervalFactory.get(cadence).next_interval(last_date)

    def assert_cadence_valid(self, cadence):
        """
        Ensure that the provided cadence exists in the set of supported cadences.

        :raises InvalidCadenceException: If the cadence is not present in the list of available/configured cadences.
        """
        try:
            IntervalFactory.get(cadence)
        except UnsupportedIntervalException:
            raise InvalidCadenceException('Cadence {} not available.'.format(cadence))

    def assert_name_unique(self, name):
        """
        Ensure that a task by this name doesn't already exist in the tasks list.

        :raises DuplicateNameException: When a task with this name already exists.
        """
        task = self.db.query(Task).filter(Task.name == name).first()

        if task:
            raise DuplicateNameException('Task "{}" already exists.'.format(name))

    def assert_start_date_valid(self, cadence, start_date):
        """
        Ensure that the date provided makes sense for the cadence it should run at.

        :raises InvalidStartDateException: When a start date and cadence could cause tasks to skip instances.
        """
        if not IntervalFactory.get(cadence).is_compatible(start_date):
            raise InvalidStartDateException(
                'Cadence {} and start date: {} could lose task instances.'.format(cadence, start_date)
            )

    def create_task(self, name, cadence, start_date):
        """
        Create a task that will be used to derive task instances.

        :param name: The name of the task.
        :param cadence: How often this task will schedule itself to create task instances.
        :param start_date: The date for which the first task instance should create itself.
        """
        self.assert_cadence_valid(cadence)
        self.assert_start_date_valid(cadence, start_date)
        self.assert_name_unique(name)

        self.db.add(Task(name=name, cadence=cadence, start=start_date))
        self.db.commit()

    def schedule_tasks(self, until_date=None):
        """
        Search through the list of all tasks, and ensure that if a task could be scheduled on or before today's date,
        that it exists in the database with the earliest of possible dates. i.e. The next task instance should be
        scheduled if it's not in the future.
        """
        max_ti_dates = self.db \
            .query(TaskInstance.task, func.max(TaskInstance.date).label('date')) \
            .group_by(TaskInstance.task) \
            .subquery()
        latest_tis = self.db \
            .query(TaskInstance) \
            .join(max_ti_dates, and_(
                TaskInstance.task == max_ti_dates.c.task,
                TaskInstance.date == max_ti_dates.c.date
            )).subquery()
        scheduleable = self.db \
            .query(Task.id,
                   Task.name,
                   Task.cadence,
                   Task.start,
                   latest_tis.c.date,
                   latest_tis.c.done) \
            .outerjoin(latest_tis, Task.id == latest_tis.c.task) \
            .order_by(Task.id)

        if not until_date:
            until_date = date.today()

        # This could probably be cleaned up a lot, likely by fixing the query, more than anything.
        for row in scheduleable.all():
            # Three possible cases.
            #    - The most recent ti is done. (Check date and maybe create a new one)
            #    - The most recent ti is not done. (Leave it)
            #    - There has never been a ti. (Make one)
            next_date = self._get_next_date(row.cadence, row.start, row.date)
            if next_date == row.date or next_date > until_date:
                continue

            if next_date <= until_date and row.done is not False:
                self.db.add(TaskInstance(task=row.id, date=next_date))

        self.db.commit()

    def complete_task_instance(self, ti_id):
        """
        Set the provided task instance to be "done"

        :param ti_id: The id for the task instance.
        """
        self.db.query(TaskInstance).filter(TaskInstance.id == ti_id).update({'done': True})
        self.db.commit()

    def get_incomplete_task_instances(self):
        """
        Returns a list of named tuples of the task instances that are still pending. Sorted by scheduled date ascending.
        """
        return self.db \
            .query(TaskInstance.id, Task.name, TaskInstance.date, literal_column('0', Boolean)) \
            .join(Task, Task.id == TaskInstance.task) \
            .filter(TaskInstance.done == False) \
            .order_by(TaskInstance.date).all()  # noqa: E712 (== operator with boolean not allowed for regular Python)
