import sqlite3
from datetime import date
from unittest import TestCase

from src.tasker import Tasker, DuplicateNameException, InvalidStartDateException, InvalidCadenceException, TaskInstance


class TaskerTest(TestCase):
    def setUp(self):
        super(TaskerTest, self).setUp()
        self.db = sqlite3.connect(":memory:")

    def test_create_task(self):
        tasker = Tasker(self.db)

        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))
        tasker.create_task('Get gas', 'weekly', date(2016, 11, 5))
        tasker.create_task('Pay bills', 'monthly', date(2016, 11, 4))

        cursor = self.db.cursor()
        cursor.execute('SELECT id, name, cadence, start FROM tasks ORDER BY start;')
        self.db.commit()

        tasks = cursor.fetchall()

        self.assertEqual(tasks, [
            (1, 'Make coffee', 'daily', '2016-11-03'),
            (3, 'Pay bills', 'monthly', '2016-11-04'),
            (2, 'Get gas', 'weekly', '2016-11-05')
        ])

    def test_create_task_duplicate(self):
        tasker = Tasker(self.db)

        tasker.create_task('Make coffee', 'daily', '2016-11-03')
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
        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))
        tasker.create_task('Get gas', 'weekly', date(2016, 11, 5))
        tasker.create_task('Pay bills', 'monthly', date(2016, 11, 4))

        tasker.schedule_tasks()

        cursor = self.db.cursor()
        cursor.execute('SELECT task, date, done FROM tis ORDER BY date;')
        self.db.commit()

        tis = cursor.fetchall()

        self.assertEqual(tis, [
            (1, '2016-11-03', 'false'),
            (3, '2016-11-04', 'false'),
            (2, '2016-11-05', 'false')
        ])

    def test_schedule_tasks_new_year(self):
        tasker = Tasker(self.db)

        # All tasks should be scheduled
        tasker.create_task('Pay bills', 'monthly', date(2016, 12, 4))

        tasker.schedule_tasks()
        tasker.complete_task_instance(1)
        tasker.schedule_tasks()

        cursor = self.db.cursor()
        cursor.execute('SELECT task, date, done FROM tis ORDER BY date;')
        self.db.commit()

        tis = cursor.fetchall()

        self.assertEqual(tis, [
            (1, '2016-12-04', 'true'),
            (1, '2017-01-04', 'false')
        ])

    def test_complete_task_instance(self):
        tasker = Tasker(self.db)

        # All tasks should be scheduled
        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))

        tasker.schedule_tasks()
        tasker.complete_task_instance(1)

        cursor = self.db.cursor()
        cursor.execute('SELECT task, date, done FROM tis ORDER BY date;')
        self.db.commit()

        tis = cursor.fetchall()

        self.assertEqual(tis, [
            (1, '2016-11-03', 'true')
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
            TaskInstance(1, 'Make coffee', '2016-11-03', 'false'),
            TaskInstance(3, 'Pay bills', '2016-11-04', 'false'),
            TaskInstance(2, 'Get gas', '2016-11-05', 'false')
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

        cursor = self.db.cursor()
        cursor.execute('SELECT task, date, done FROM tis ORDER BY date, task;')
        self.db.commit()

        tis = cursor.fetchall()

        self.assertEqual(tis, [
            (1, '2016-11-03', 'true'),
            (1, '2016-11-04', 'false'),
            (3, '2016-11-04', 'true'),
            (2, '2016-11-05', 'true'),
            (2, '2016-11-12', 'false'),
            (3, '2016-12-04', 'false')
        ])

    def test_tasker_full_scenario_schedule_complete(self):
        tasker = Tasker(self.db)

        tasker.create_task('Get gas', 'weekly', date(2016, 11, 5))
        tasker.create_task('Pay bills', 'monthly', date(2016, 11, 4))

        tasker.schedule_tasks()

        tasker.complete_task_instance(1)
        tasker.complete_task_instance(2)

        tasker.schedule_tasks(until_date=date(2016, 11, 11))

        cursor = self.db.cursor()
        cursor.execute('SELECT task, date, done FROM tis ORDER BY date, task;')
        self.db.commit()

        tis = cursor.fetchall()

        self.assertEqual(tis, [
            (2, '2016-11-04', 'true'),
            (1, '2016-11-05', 'true')
        ])
