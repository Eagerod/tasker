from collections import namedtuple
from datetime import date, timedelta


TaskInstance = namedtuple('TaskInstance', ['id', 'task', 'date', 'done'])


class TaskerException(Exception):
    pass


class DuplicateNameException(TaskerException):
    pass


class InvalidStartDateException(TaskerException):
    pass


class InvalidCadenceException(TaskerException):
    pass


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
    CREATE_LATEST_TIS_VIEW = '''
        CREATE VIEW IF NOT EXISTS latest_tis AS
            SELECT ti.id AS id, ti.task AS task, ti.date AS date, ti.done AS done FROM tis ti
            JOIN (
                SELECT task, max(date) AS date FROM tis GROUP BY task
            ) mti
            ON mti.task = ti.task AND ti.date = mti.date;
    '''
    SELECT_SCHEDULABLE_TASKS = '''
        SELECT t.id, t.name, t.cadence, t.start, ti.date, ti.done
        FROM tasks t
        LEFT JOIN (
            SELECT task, date, done FROM latest_tis
        ) ti ON t.id = ti.task
        GROUP BY t.id, t.name, t.cadence, t.start, ti.done
        ORDER BY t.id, ti.done;
    '''
    SELECT_TASK_BY_NAME = '''
        SELECT count(*) FROM tasks WHERE name = ?;
    '''
    SELECT_INCOMPLETE_TIS = '''
        SELECT ti.id, t.name, ti.date
        FROM tasks t
        JOIN tis ti ON ti.task = t.id
        WHERE ti.done = "false"
        ORDER BY ti.date;
    '''
    INSERT_TASK = '''
        INSERT INTO tasks (name, cadence, start) VALUES (?,?,?)
    '''
    INSERT_TI = '''
        INSERT INTO tis (task, date) VALUES (?,?);
    '''
    UPDATE_TI_DONE = '''
        UPDATE tis SET done = "true" WHERE id = ?
    '''


class Tasker(object):
    """
    Class that manages recurring tasks in an SQLite3 database.
    """
    class Cadence(object):
        """
        Pseudo-enum for supported cadences.
        """
        DAILY = 'daily'
        WEEKLY = 'weekly'
        MONTHLY = 'monthly'

        ALL = (DAILY, WEEKLY, MONTHLY)

    def __init__(self, database):
        """
        :param database: The sqlite3 database connection for this instance.
        """
        self.db = database
        self._db_initialized = False

    def _initialize_db(self):
        """
        Initialize the database by ensuring that the required tables are present.

        NOTE: Currently has no support whatsoever for managing schema evolution.
        """
        if self._db_initialized:
            return

        cursor = self.db.cursor()
        cursor.execute(Queries.CREATE_TASKS_TABLE)
        cursor.execute(Queries.CREATE_TASK_INSTANCES_TABLE)
        cursor.execute(Queries.CREATE_LATEST_TIS_VIEW)
        self.db.commit()

        self._db_initialized = True

    def _get_next_date(self, cadence, start_date, last_date):
        """
        Get the next scheduleable date for a given start date and last scheduled date.

        :param cadence: Schedule cadence for the task being checked.
        :param start_date: The date the initial task was scheduled.
        :param last_date: The last date a task instance was scheduled.
        """
        if not last_date:
            return start_date

        date_components = last_date.split('-')
        recent_date = date(*(int(d) for d in date_components))
        if cadence == Tasker.Cadence.DAILY:
            return (recent_date + timedelta(days=1)).isoformat()
        if cadence == Tasker.Cadence.WEEKLY:
            return (recent_date + timedelta(days=7)).isoformat()
        elif cadence == Tasker.Cadence.MONTHLY:
            # No "month" timedelta :(
            if recent_date.month == 12:
                return (recent_date.replace(year=recent_date.year + 1, month=1)).isoformat()
            return (recent_date.replace(month=recent_date.month + 1)).isoformat()

    def assert_cadence_valid(self, cadence):
        """
        Ensure that the provided cadence exists in the set of supported cadences.

        :raises InvalidCadenceException: If the cadence is not present in the list of available/configured cadences.
        """
        if cadence not in Tasker.Cadence.ALL:
            raise InvalidCadenceException('Cadence {} not available.')

    def assert_name_unique(self, name):
        """
        Ensure that a task by this name doesn't already exist in the tasks list.

        :raises DuplicateNameException: When a task with this name already exists.
        """
        self._initialize_db()

        cursor = self.db.cursor()
        cursor.execute(Queries.SELECT_TASK_BY_NAME, (name,))
        self.db.commit()

        for row in cursor:
            if row != (0,):
                raise DuplicateNameException('Task "{}" already exists'.format(name))

    def assert_start_date_valid(self, cadence, start_date):
        """
        Ensure that the date provided makes sense for the cadence it should run at.

        :raises InvalidStartDateException: When a start date and cadence could cause tasks to skip instances.
        """
        if cadence == Tasker.Cadence.MONTHLY and start_date.day > 28:
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

        self._initialize_db()
        self.assert_name_unique(name)
        cursor = self.db.cursor()
        cursor.execute(Queries.INSERT_TASK, (name, cadence, start_date))
        self.db.commit()

    def schedule_tasks(self, until_date=None):
        """
        Search through the list of all tasks, and ensure that if a task could be scheduled on or before today's date,
        that it exists in the database with the earliest of possible dates. i.e. The next task instance should be
        scheduled if it's not in the future.
        """
        self._initialize_db()

        cursor = self.db.cursor()
        cursor.execute(Queries.SELECT_SCHEDULABLE_TASKS)
        self.db.commit()

        if not until_date:
            until_date = date.today()

        until_date_str = until_date.strftime('%Y-%m-%d')
        insert_statements = []

        # This could probably be cleaned up a lot, likely by fixing the query, more than anything.
        for row in cursor:
            # Three possible cases.
            #    - The most recent ti is done. (Check date and maybe create a new one)
            #    - The most recent ti is not done. (Leave it)
            #    - There has never been a ti. (Make one)
            next_date = self._get_next_date(row[2], row[3], row[4])
            if next_date == row[4] or next_date > until_date_str:
                continue

            if next_date <= until_date_str and row[5] != 'false':
                insert_statements.append((row[0], next_date))

        cursor = self.db.cursor()
        cursor.executemany(Queries.INSERT_TI, insert_statements)
        self.db.commit()

    def complete_task_instance(self, ti_id):
        """
        Set the provided task instance to be "done"

        :param ti_id: The id for the task instance.
        """
        cursor = self.db.cursor()
        cursor.execute(Queries.UPDATE_TI_DONE, (ti_id,))
        self.db.commit()

    def get_incomplete_task_instances(self):
        """
        Returns a list of named tuples of the task instances that are still pending. Sorted by scheduled date ascending.
        """
        cursor = self.db.cursor()
        cursor.execute(Queries.SELECT_INCOMPLETE_TIS)
        self.db.commit()

        return [TaskInstance(t[0], t[1], t[2], 'false') for t in cursor.fetchall()]
