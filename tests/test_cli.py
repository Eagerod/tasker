import os
import sqlite3
from subprocess import Popen, PIPE
from unittest import TestCase


CLI_ENTER_TASK_NAME_STRING = 'Enter task name: '
CLI_ENTER_CADENCE_STRING = 'Available cadences:\n  1. Daily\n  2. Weekly\n  3. Monthly\nSelect cadence: '
CLI_ENTER_START_DATE_STRING = 'When does this start (YYYY-MM-DD): '

CLI_CADENCE_NOT_AVAILABLE_FORMAT = 'Cadence {} not available.\n'
CLI_INAPPROPRATE_DATE_FORMAT = 'Cadence {} and start date: {} could lose task instances.\n'
CLI_DUPLICATE_NAME_FORMAT = 'Task "{}" already exists.\n'
CLI_INVALID_DATE_FORMAT = 'Not a valid (YYYY-MM-DD) ({})\n'

THINGS_TO_DO_STRING = 'Things to do:\n'
COMPLETE_TASK_FORMAT = 'To complete any task, use:\n    {} --complete N\n'


class CliTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_root_dir = os.path.dirname(os.path.realpath(__file__))
        cls.root_dir = os.path.dirname(cls.test_root_dir)

        cls.cli_path = os.path.join(cls.root_dir, 'src', 'cli.py')
        cls.db_path = os.path.join(cls.test_root_dir, 'tasker_tests.sqlite')

        cls.complete_task_string = COMPLETE_TASK_FORMAT.format(cls.cli_path)
        cls._delete_temp_database()

    @classmethod
    def _delete_temp_database(cls):
        if os.path.exists(cls.db_path):
            os.unlink(cls.db_path)

    def tearDown(self):
        super(CliTest, self).tearDown()
        self._delete_temp_database()

    def _call_cli(self, cli_args, stdin=None):
        full_command = ['python', self.cli_path, '--database', self.db_path] + cli_args

        env = os.environ.copy()
        env['PYTHONPATH'] = self.root_dir

        process = Popen(full_command, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=env)
        output = process.communicate(input=stdin)
        return process.returncode, output[0], output[1]

    def test_usage_message(self):
        val = self._call_cli([])
        self.assertNotEqual(val[0], 0)
        self.assertIn('usage:', val[1])
        self.assertEqual(val[2], '')

    def test_check_with_no_db_contents(self):
        val = self._call_cli(['--check'])
        self.assertEqual(val, (0, '', ''))

    def test_create_task(self):
        input_str = 'Do some things\ndaily\n2017-11-06\n'
        output_str = '{}{}{}'.format(CLI_ENTER_TASK_NAME_STRING, CLI_ENTER_CADENCE_STRING, CLI_ENTER_START_DATE_STRING)
        val = self._call_cli(['--create'], stdin=input_str)
        self.assertEqual(val, (0, output_str, ''))

        # Verify that it was created.
        db = sqlite3.connect(self.db_path)
        cursor = db.cursor()
        cursor.execute('SELECT name, cadence, start FROM tasks')
        db.commit()

        self.assertEqual(cursor.fetchall(), [('Do some things', 'daily', '2017-11-06')])

    def test_create_task_invalid_cadence(self):
        input_str = 'Do some things\nlol testing\ndaily\n2017-11-06\n'
        output_str = '{}{}{}{}'.format(
            CLI_ENTER_TASK_NAME_STRING, CLI_ENTER_CADENCE_STRING, CLI_ENTER_CADENCE_STRING, CLI_ENTER_START_DATE_STRING
        )
        val = self._call_cli(['--create'], stdin=input_str)
        self.assertEqual(val, (0, output_str, CLI_CADENCE_NOT_AVAILABLE_FORMAT.format('lol testing')))

        # Verify that it was created.
        db = sqlite3.connect(self.db_path)
        cursor = db.cursor()
        cursor.execute('SELECT name, cadence, start FROM tasks')
        db.commit()

        self.assertEqual(cursor.fetchall(), [('Do some things', 'daily', '2017-11-06')])

    def test_create_task_invalid_interval(self):
        input_str = 'Do some things\nmonthly\n2017-11-29\n2017-11-06'
        output_str = '{}{}{}{}'.format(
            CLI_ENTER_TASK_NAME_STRING,
            CLI_ENTER_CADENCE_STRING,
            CLI_ENTER_START_DATE_STRING,
            CLI_ENTER_START_DATE_STRING
        )
        val = self._call_cli(['--create'], stdin=input_str)
        self.assertEqual(val, (0, output_str, CLI_INAPPROPRATE_DATE_FORMAT.format('monthly', '2017-11-29')))

        # Verify that it was created.
        db = sqlite3.connect(self.db_path)
        cursor = db.cursor()
        cursor.execute('SELECT name, cadence, start FROM tasks')
        db.commit()

        self.assertEqual(cursor.fetchall(), [('Do some things', 'monthly', '2017-11-06')])

    def test_create_task_duplicate_name(self):
        input_str = 'Do some things\ndaily\n2017-11-06\n'
        val = self._call_cli(['--create'], stdin=input_str)

        input_str = 'Do some things\nDo some other things\ndaily\n2017-11-07\n'
        val = self._call_cli(['--create'], stdin=input_str)
        output_str = '{}{}{}{}'.format(
            CLI_ENTER_TASK_NAME_STRING,
            CLI_ENTER_TASK_NAME_STRING,
            CLI_ENTER_CADENCE_STRING,
            CLI_ENTER_START_DATE_STRING
        )

        self.assertEqual(val, (0, output_str, CLI_DUPLICATE_NAME_FORMAT.format('Do some things')))

        # Verify that it was created.
        db = sqlite3.connect(self.db_path)
        cursor = db.cursor()
        cursor.execute('SELECT name, cadence, start FROM tasks ORDER BY start')
        db.commit()

        self.assertEqual(cursor.fetchall(), [
            ('Do some things', 'daily', '2017-11-06'), ('Do some other things', 'daily', '2017-11-07')
        ])

    def test_create_task_invalid_date(self):
        input_str = 'Do some things\ndaily\n2017-25-11\n2017-11-06\n'
        output_str = '{}{}{}{}'.format(
            CLI_ENTER_TASK_NAME_STRING,
            CLI_ENTER_CADENCE_STRING,
            CLI_ENTER_START_DATE_STRING,
            CLI_ENTER_START_DATE_STRING
        )
        val = self._call_cli(['--create'], stdin=input_str)

        self.assertEqual(val, (0, output_str, CLI_INVALID_DATE_FORMAT.format('month must be in 1..12')))

        # Verify that it was created.
        db = sqlite3.connect(self.db_path)
        cursor = db.cursor()
        cursor.execute('SELECT name, cadence, start FROM tasks ORDER BY start')
        db.commit()

        self.assertEqual(cursor.fetchall(), [('Do some things', 'daily', '2017-11-06')])

    def test_create_check_task(self):
        input_str = 'Do some things\ndaily\n2017-11-06\n'
        output_str = '{}{}{}'.format(CLI_ENTER_TASK_NAME_STRING, CLI_ENTER_CADENCE_STRING, CLI_ENTER_START_DATE_STRING)
        self._call_cli(['--create'], stdin=input_str)

        val = self._call_cli(['--check'])

        output_str = '{}      1. (2017-11-06) Do some things\n{}'.format(THINGS_TO_DO_STRING, self.complete_task_string)
        self.assertEqual(val, (0, output_str, ''))

        db = sqlite3.connect(self.db_path)
        cursor = db.cursor()
        cursor.execute('SELECT task, date, done FROM tis')
        db.commit()

        self.assertEqual(cursor.fetchall(), [(1, '2017-11-06', 'false')])

    def test_create_check_complete_task(self):
        input_str = 'Do some things\ndaily\n2017-11-06\n'
        self._call_cli(['--create'], stdin=input_str)
        self._call_cli(['--check'])

        val = self._call_cli(['--complete', '1'])
        self.assertEqual(val, (0, '', ''))

        db = sqlite3.connect(self.db_path)
        cursor = db.cursor()
        cursor.execute('SELECT task, date, done FROM tis')
        db.commit()

        self.assertEqual(cursor.fetchall(), [(1, '2017-11-06', 'true')])
