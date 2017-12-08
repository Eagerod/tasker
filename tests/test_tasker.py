import sqlite3
from datetime import date
from unittest import TestCase

from src.tasker import Tasker, DuplicateNameException, InvalidStartDateException, InvalidCadenceException, TaskInstance


class TaskerTest(TestCase):
    def setUp(self):
        super(TaskerTest, self).setUp()
        self.db = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)

    def test_create_task(self):
        tasker = Tasker(self.db)

        tasker.create_task('Fix bike', 'once', date(2016, 11, 2))
        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))
        tasker.create_task('Get gas', 'weekly', date(2016, 11, 5))
        tasker.create_task('Pay bills', 'monthly', date(2016, 11, 4))

        cursor = self.db.cursor()
        cursor.execute('SELECT id, name, cadence, start FROM tasks ORDER BY start;')
        self.db.commit()

        tasks = cursor.fetchall()

        self.assertEqual(tasks, [
            (1, 'Fix bike', 'once', date(2016, 11, 2)),
            (2, 'Make coffee', 'daily', date(2016, 11, 3)),
            (4, 'Pay bills', 'monthly', date(2016, 11, 4)),
            (3, 'Get gas', 'weekly', date(2016, 11, 5))
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
        tasker.create_task('Fix bike', 'once', date(2016, 11, 2))
        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))
        tasker.create_task('Get gas', 'weekly', date(2016, 11, 5))
        tasker.create_task('Pay bills', 'monthly', date(2016, 11, 4))

        tasker.schedule_tasks()

        cursor = self.db.cursor()
        cursor.execute('SELECT task, date, done FROM tis ORDER BY date;')
        self.db.commit()

        tis = cursor.fetchall()

        self.assertEqual(tis, [
            (1, date(2016, 11, 2), 'false'),
            (2, date(2016, 11, 3), 'false'),
            (4, date(2016, 11, 4), 'false'),
            (3, date(2016, 11, 5), 'false')
        ])

    def test_schedule_tasks_nothing_exists(self):
        tasker = Tasker(self.db)

        tasker.schedule_tasks()

        cursor = self.db.cursor()
        cursor.execute('SELECT task, date, done FROM tis ORDER BY date;')
        self.db.commit()

        tis = cursor.fetchall()

        self.assertEqual(tis, [])

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
            (1, date(2016, 12, 4), 'true'),
            (1, date(2017, 1, 4), 'false')
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

        cursor = self.db.cursor()
        cursor.execute('SELECT task, date, done FROM tis ORDER BY date;')
        self.db.commit()

        tis = cursor.fetchall()

        self.assertEqual(tis, [
            (1, date(2016, 11, 3), 'false'),
            (3, date(2016, 11, 4), 'false'),
            (2, date(2016, 11, 5), 'false')
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

        cursor = self.db.cursor()
        cursor.execute('SELECT task, date, done FROM tis ORDER BY date, task;')
        self.db.commit()

        tis = cursor.fetchall()

        self.assertEqual(tis, [
            (1, date(2016, 11, 2), 'true'),
            (2, date(2016, 11, 3), 'true'),
            (2, date(2016, 11, 4), 'false'),
            (4, date(2016, 11, 4), 'true'),
            (3, date(2016, 11, 5), 'true'),
            (3, date(2016, 11, 12), 'false'),
            (4, date(2016, 12, 4), 'false')
        ])

    def test_complete_task_instance(self):
        tasker = Tasker(self.db)

        tasker.create_task('Make coffee', 'daily', date(2016, 11, 3))

        tasker.schedule_tasks()
        tasker.complete_task_instance(1)

        cursor = self.db.cursor()
        cursor.execute('SELECT task, date, done FROM tis ORDER BY date;')
        self.db.commit()

        tis = cursor.fetchall()

        self.assertEqual(tis, [
            (1, date(2016, 11, 3), 'true')
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
            TaskInstance(1, 'Make coffee', date(2016, 11, 3), 'false'),
            TaskInstance(3, 'Pay bills', date(2016, 11, 4), 'false'),
            TaskInstance(2, 'Get gas', date(2016, 11, 5), 'false')
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
            (1, date(2016, 11, 3), 'true'),
            (1, date(2016, 11, 4), 'false'),
            (3, date(2016, 11, 4), 'true'),
            (2, date(2016, 11, 5), 'true'),
            (2, date(2016, 11, 12), 'false'),
            (3, date(2016, 12, 4), 'false')
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
            (2, date(2016, 11, 4), 'true'),
            (1, date(2016, 11, 5), 'true')
        ])
