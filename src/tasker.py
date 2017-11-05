import os
import sqlite3
from datetime import date, timedelta


class Queries(object):
    CREATE_TASKS_TABLE = '''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            name TEXT,
            cadence TEXT,
            start DATE
        );
    '''
    CREATE_TASK_INSTANCES_TABLE = '''
        CREATE TABLE IF NOT EXISTS tis (
            id INTEGER PRIMARY KEY,
            task INT,
            date DATE,
            done BOOLEAN DEFAULT false
        );
    '''
    SELECT_INCOMPLETE_TIS = '''
        SELECT ti.id, t.name, ti.date
        FROM tasks t
        JOIN tis ti ON ti.task = t.id
        WHERE ti.done = "false";
    '''
    SELECT_SCHEDULABLE_TASKS = '''
        SELECT t.id, t.name, t.cadence, t.start, MAX(ti.date), ti.done
        FROM tasks t
        LEFT JOIN (
            SELECT task, max(date) as date, done from tis
        ) ti ON t.id = ti.task
        GROUP BY t.id, t.name, t.cadence, t.start, ti.done
        ORDER BY t.id, ti.done;
    '''
    SELECT_TASK_BY_NAME = '''
        SELECT count(*) FROM tasks WHERE name = ?;
    '''
    INSERT_TASK = '''
        INSERT INTO tasks (name, cadence, start) VALUES (?,?,?)
    '''
    INSERT_TI = '''
        INSERT INTO tis (task, date) VALUES (?,?);
    '''


class Cadence(object):
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'


class TaskCreator(object):
    def __init__(self, db):
        self.db = db

    def _get_task_name(self):
        cursor = self.db.cursor()

        while True:
            name = raw_input('Enter task name: ')

            cursor.execute(Queries.SELECT_TASK_BY_NAME, (name,))
            for row in cursor:
                if row == (0,):
                    return name
                print 'Task already exists.'

    def _get_cadence(self):
        while True:
            print 'Available cadences:'
            print '  1. Daily\n  2. Weekly\n  3. Monthly'
            cadence = raw_input('Select cadence: ')
            if cadence == '1' or cadence.lower() == Cadence.DAILY:
                return Cadence.DAILY
            if cadence == '2' or cadence.lower() == Cadence.WEEKLY:
                return Cadence.WEEKLY
            if cadence == '3' or cadence.lower() == Cadence.MONTHLY:
                return Cadence.MONTHLY

    def _get_first_date(self):
        while True:
            start = raw_input('When does this start (YYYY-MM-DD): ')
            try:
                return date(*[int(i) for i in start.split('-')])
            except:
                print 'Not a valid (YYYY-MM-DD)'

    def create_task_from_user_input(self):
        name = self._get_task_name()
        cadence = self._get_cadence()
        start = self._get_first_date()

        cursor = self.db.cursor()
        cursor.execute(Queries.INSERT_TASK, (name, cadence, start))
        self.db.commit()


class TaskUpdater(object):
    def __init__(self, db):
        self.db = db

    def _get_next_date(self, cadence, start_date, last_date):
        if not last_date:
            return start_date

        date_components = last_date.split('-')
        recent_date = date(*(int(d) for d in date_components))
        if cadence == Cadence.DAILY:
            return (recent_date + timedelta(days=1)).isoformat()
        if cadence == Cadence.WEEKLY:
            return (recent_date + timedelta(days=7)).isoformat()
        elif cadence == Cadence.MONTHLY:
            # No "month" timedelta :(
            if recent_date.month == 12:
                return (recent_date.replace(year=recent_date.year + 1, month=1)).isoformat()
            return (recent_date.replace(month=recent_date.month + 1)).isoformat()

    def update_task_instances(self):
        cursor = self.db.cursor()
        cursor.execute(Queries.SELECT_SCHEDULABLE_TASKS)
        self.db.commit()

        today_date = date.today().strftime('%Y-%m-%d')
        insert_statements = []

        for row in cursor:
            # Three possible cases.
            #    - The most recent ti is done. (Check date and maybe create a new one)
            #    - The most recent ti is not done. (Leave it)
            #    - There has never been a ti. (Make one)
            next_date = self._get_next_date(row[2], row[3], row[4])
            if next_date <= today_date and row[5] != 'false':
                insert_statements.append((row[0], self._get_next_date(row[2], row[3], row[4])))

        cursor = self.db.cursor()
        cursor.executemany(Queries.INSERT_TI, insert_statements)
        self.db.commit()

    def complete_task_instance(self, ti_id):
        cursor = self.db.cursor()
        cursor.execute('UPDATE tis SET done = "true" WHERE id = ?', (ti_id,))
        self.db.commit()


class TaskPrinter(object):
    def __init__(self, db):
        self.db = db

    def print_remaining_tasks(self):
        cursor = self.db.cursor()
        cursor.execute(Queries.SELECT_INCOMPLETE_TIS)
        self.db.commit()

        task_instances = cursor.fetchall()
        if len(task_instances):
            print 'Things to do:'
            for row in task_instances:
                print '    {}. ({}) {}'.format(row[0], row[2], row[1])


class TaskerCli(object):
    def __init__(self, database=None):
        if not database:
            database = os.path.join(os.path.expanduser('~'), '.tasker.sqlite')

        self.db = sqlite3.connect(database)
        self._init_db()

    def _init_db(self):
        cursor = self.db.cursor()
        cursor.execute(Queries.CREATE_TASKS_TABLE)
        cursor.execute(Queries.CREATE_TASK_INSTANCES_TABLE)
        self.db.commit()

    def create_task(self):
        TaskCreator(self.db).create_task_from_user_input()

    def print_tasks(self):
        TaskUpdater(self.db).update_task_instances()
        TaskPrinter(self.db).print_remaining_tasks()

    def complete_task(self, ti_id):
        TaskUpdater(self.db).complete_task_instance(ti_id)
