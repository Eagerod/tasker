from datetime import date
from unittest import TestCase

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Task
from src.tasker import Tasker, DuplicateNameException, InvalidStartDateException, InvalidCadenceException, TaskInstance


class TaskerTest(TestCase):
    def setUp(self):
        super(TaskerTest, self).setUp()

        engine = create_engine('sqlite://')
        Base.metadata.create_all(engine)
        Base.metadata.bind = engine

        session = sessionmaker(bind=engine)

        self.db = session()

        self.tasker = Tasker(self.db)

    def test_create_task(self):
        tasker = Tasker(self.db)

        tasker.create_task('Fix bike', 'once', date(2016, 11, 2))
        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))
        tasker.create_task('Get gas', 'weekly', date(2016, 11, 5))
        tasker.create_task('Pay bills', 'monthly', date(2016, 11, 4))

        tasks = self.db.query(Task).order_by(Task.start).all()

        self.assertEqual(tasks, [
            Task(id=1, name='Fix bike', cadence='once', start=date(2016, 11, 2)),
            Task(id=2, name='Make coffee', cadence='daily', start=date(2016, 11, 3)),
            Task(id=4, name='Pay bills', cadence='monthly', start=date(2016, 11, 4)),
            Task(id=3, name='Get gas', cadence='weekly', start=date(2016, 11, 5))
        ])

    def test_create_task_duplicate(self):
        tasker = Tasker(self.db)

        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))
        self.assertRaises(DuplicateNameException, tasker.create_task, 'Make coffee', 'daily', date(2016, 11, 3))

    def test_create_task_date_not_possible(self):
        tasker = Tasker(self.db)

        self.assertRaises(InvalidStartDateException, tasker.create_task, 'Pay bills', 'monthly', date(2016, 10, 29))

    def test_create_task_cadence_invalid(self):
        tasker = Tasker(self.db)

        self.assertRaises(InvalidCadenceException, tasker.create_task, 'Pay bills', 'random', date(2016, 10, 29))

    def test_schedule_tasks(self):
        tasker = Tasker(self.db)

        # All tasks should be scheduled
        tasker.create_task('Fix bike', 'once', date(2016, 11, 2))
        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))
        tasker.create_task('Get gas', 'weekly', date(2016, 11, 5))
        tasker.create_task('Pay bills', 'monthly', date(2016, 11, 4))

        tasker.schedule_tasks()
        tis = self.db.query(TaskInstance).order_by(TaskInstance.date).all()

        self.assertEqual(tis, [
            TaskInstance(id=1, task=1, date=date(2016, 11, 2), done=False),
            TaskInstance(id=2, task=2, date=date(2016, 11, 3), done=False),
            TaskInstance(id=4, task=4, date=date(2016, 11, 4), done=False),
            TaskInstance(id=3, task=3, date=date(2016, 11, 5), done=False)
        ])

    def test_schedule_tasks_nothing_exists(self):
        tasker = Tasker(self.db)

        tasker.schedule_tasks()
        self.assertEqual([], self.db.query(TaskInstance).all())

    def test_schedule_tasks_new_year(self):
        tasker = Tasker(self.db)

        # All tasks should be scheduled
        tasker.create_task('Pay bills', 'monthly', date(2016, 12, 4))

        tasker.schedule_tasks()
        tasker.complete_task_instance(1)
        tasker.schedule_tasks()

        tis = self.db.query(TaskInstance).order_by(TaskInstance.date).all()

        self.assertEqual(tis, [
            TaskInstance(id=1, task=1, date=date(2016, 12, 4), done=True),
            TaskInstance(id=2, task=1, date=date(2017, 1, 4), done=False)
        ])

    def test_schedule_tasks_repeated(self):
        tasker = Tasker(self.db)

        # All tasks should be scheduled
        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))
        tasker.create_task('Get gas', 'weekly', date(2016, 11, 5))
        tasker.create_task('Pay bills', 'monthly', date(2016, 11, 4))

        tasker.schedule_tasks()
        tasker.schedule_tasks()
        tasker.schedule_tasks()

        tis = self.db.query(TaskInstance).order_by(TaskInstance.date).all()

        self.assertEqual(tis, [
            TaskInstance(id=1, task=1, date=date(2016, 11, 3), done=False),
            TaskInstance(id=3, task=3, date=date(2016, 11, 4), done=False),
            TaskInstance(id=2, task=2, date=date(2016, 11, 5), done=False)
        ])

    def test_schedule_tasks_repeated_tasks_done(self):
        tasker = Tasker(self.db)

        # All tasks should be scheduled
        tasker.create_task('Fix bike', 'once', date(2016, 11, 2))
        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))
        tasker.create_task('Get gas', 'weekly', date(2016, 11, 5))
        tasker.create_task('Pay bills', 'monthly', date(2016, 11, 4))

        tasker.schedule_tasks()
        tasker.complete_task_instance(1)
        tasker.complete_task_instance(2)
        tasker.complete_task_instance(3)
        tasker.complete_task_instance(4)
        tasker.schedule_tasks()
        tasker.schedule_tasks()

        tis = self.db.query(TaskInstance).order_by(TaskInstance.date, TaskInstance.task).all()

        self.assertEqual(tis, [
            TaskInstance(id=1, task=1, date=date(2016, 11, 2), done=True),
            TaskInstance(id=2, task=2, date=date(2016, 11, 3), done=True),
            TaskInstance(id=5, task=2, date=date(2016, 11, 4), done=False),
            TaskInstance(id=4, task=4, date=date(2016, 11, 4), done=True),
            TaskInstance(id=3, task=3, date=date(2016, 11, 5), done=True),
            TaskInstance(id=6, task=3, date=date(2016, 11, 12), done=False),
            TaskInstance(id=7, task=4, date=date(2016, 12, 4), done=False)
        ])

    def test_complete_task_instance(self):
        tasker = Tasker(self.db)

        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))

        tasker.schedule_tasks()
        tasker.complete_task_instance(1)

        tis = self.db.query(TaskInstance).all()

        self.assertEqual(tis, [
            TaskInstance(id=1, task=1, date=date(2016, 11, 3), done=True)
        ])

    def test_get_incomplete_task_instances(self):
        tasker = Tasker(self.db)

        # All tasks should be scheduled
        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))
        tasker.create_task('Get gas', 'weekly', date(2016, 11, 5))
        tasker.create_task('Pay bills', 'monthly', date(2016, 11, 4))

        tasker.schedule_tasks()

        tis = tasker.get_incomplete_task_instances()

        self.assertEqual(tis, [
            (1, 'Make coffee', date(2016, 11, 3), False),
            (3, 'Pay bills', date(2016, 11, 4), False),
            (2, 'Get gas', date(2016, 11, 5), False)
        ])

    def test_tasker_full_scenario(self):
        tasker = Tasker(self.db)

        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))
        tasker.create_task('Get gas', 'weekly', date(2016, 11, 5))
        tasker.create_task('Pay bills', 'monthly', date(2016, 11, 4))

        tasker.schedule_tasks()

        tasker.complete_task_instance(1)
        tasker.complete_task_instance(2)
        tasker.complete_task_instance(3)

        # Schedule next iteration of every task.
        tasker.schedule_tasks()

        tis = self.db.query(TaskInstance).order_by(TaskInstance.date, TaskInstance.task).all()

        self.assertEqual(tis, [
            TaskInstance(id=1, task=1, date=date(2016, 11, 3), done=True),
            TaskInstance(id=4, task=1, date=date(2016, 11, 4), done=False),
            TaskInstance(id=3, task=3, date=date(2016, 11, 4), done=True),
            TaskInstance(id=2, task=2, date=date(2016, 11, 5), done=True),
            TaskInstance(id=5, task=2, date=date(2016, 11, 12), done=False),
            TaskInstance(id=6, task=3, date=date(2016, 12, 4), done=False)
        ])

    def test_tasker_full_scenario_schedule_complete(self):
        tasker = Tasker(self.db)

        tasker.create_task('Get gas', 'weekly', date(2016, 11, 5))
        tasker.create_task('Pay bills', 'monthly', date(2016, 11, 4))

        tasker.schedule_tasks()

        tasker.complete_task_instance(1)
        tasker.complete_task_instance(2)

        tasker.schedule_tasks(until_date=date(2016, 11, 11))

        tis = self.db.query(TaskInstance).order_by(TaskInstance.date, TaskInstance.task).all()

        self.assertEqual(tis, [
            TaskInstance(id=2, task=2, date=date(2016, 11, 4), done=True),
            TaskInstance(id=1, task=1, date=date(2016, 11, 5), done=True)
        ])
