import argparse
import os
import sys
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tasker import Tasker, InvalidStartDateException, DuplicateNameException, InvalidCadenceException
from models import Base
from intervals.interval_factory import IntervalFactory, UnsupportedIntervalException


class TaskerCliOptions(object):
    CREATE = 'create'
    CHECK = 'check'
    COMPLETE = 'complete'


class TaskerCli(object):
    DEFAULT_DATABASE_URI = 'sqlite:///{}'.format(os.path.join(os.path.expanduser('~'), '.tasker.sqlite'))

    def __init__(self, database=None):
        if not database:
            database = self.DEFAULT_DATABASE_URI

        self.database_uri = database

        engine = create_engine(self.database_uri)
        Base.metadata.create_all(engine)
        Base.metadata.bind = engine

        session = sessionmaker(bind=engine)
        self.db = session()

        self.tasker = Tasker(self.db)

        self._run_path = sys.argv[0]
        # Scan through $PATH, and determine if this could be run without the full path.
        run_directory = os.path.dirname(sys.argv[0])
        if run_directory[-1] != os.path.sep:
            run_directory = run_directory + os.path.sep
        len_run_directory = len(run_directory)

        for a_path in os.environ['PATH'].split(os.pathsep):
            if a_path[-1] != os.path.sep:
                a_path = a_path + os.path.sep
            if a_path == run_directory:
                self._run_path = self._run_path[len_run_directory:]
                break

        # Attempt to load up all intervals from the intervals directory.
        self.all_cadences = {}
        intervals_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), 'intervals'))
        for f in os.listdir(intervals_dir):
            # Only take py files
            if not f.endswith('.py') or f in ('__init__.py', 'base_interval.py', 'interval_factory.py'):
                continue

            interval_name = f.replace('.py', '')
            try:
                interval = IntervalFactory.get(interval_name)
            except UnsupportedIntervalException:
                pass

            self.all_cadences[interval.approximate_period()] = (interval_name, interval)

    def create_task(self):
        name = self._get_task_name()
        cadence = self._get_cadence()
        while True:
            start = self._get_first_date()
            try:
                self.tasker.assert_start_date_valid(cadence, start)
                break
            except InvalidStartDateException as e:
                print >> sys.stderr, e.message

        self.tasker.create_task(name, cadence, start)

    def print_tasks(self):
        self.tasker.schedule_tasks()
        self._print_remaining_tasks()

    def complete_task(self, ti_id):
        self.tasker.complete_task_instance(ti_id)

    def _print_remaining_tasks(self):
        task_instances = self.tasker.get_incomplete_task_instances()
        if len(task_instances):

            # Get the highest TI id, so that the indent can be exactly 4 spaces in from the longest ID.
            max_id = max(ti[0] for ti in task_instances)
            rjust = 4 + len(str(max_id))

            print 'Things to do:'
            for row in task_instances:
                ti_id, name, date, done = row
                print '{}. ({}) {}'.format(str(ti_id).rjust(rjust), date, name)

            database_str = ' '
            if self.database_uri != self.DEFAULT_DATABASE_URI:
                database_str = ' --database "{}" '.format(self.database_uri)

            print 'To complete any task, use:\n    {}{}{} N'.format(
                self._run_path, database_str, TaskerCliOptions.COMPLETE
            )

    def _get_task_name(self):
        while True:
            name = raw_input('Enter task name: ').strip()

            if not name:
                continue

            try:
                self.tasker.assert_name_unique(name)
                return name
            except DuplicateNameException as e:
                print >> sys.stderr, e.message

    def _get_cadence(self):
        all_cadences_keys = sorted(self.all_cadences.keys())
        cadence_lst = ['  {}. {}'.format(i+1, self.all_cadences[o][0].title()) for i, o in enumerate(all_cadences_keys)]

        while True:
            print 'Available cadences:'
            print '\n'.join(cadence_lst)
            cadence = raw_input('Select cadence: ').strip()

            if not cadence:
                continue

            try:
                cadence = self.all_cadences[all_cadences_keys[int(cadence) - 1]][0]
            except ValueError:
                pass

            cadence = cadence.lower()
            try:
                self.tasker.assert_cadence_valid(cadence)
                return cadence
            except InvalidCadenceException as e:
                print >> sys.stderr, e.message

    def _get_first_date(self):
        while True:
            start = raw_input('When does this start (YYYY-MM-DD; default today): ').strip()

            if start == '':
                return date.today()

            try:
                return date(*[int(i) for i in start.split('-')])
            except (TypeError, ValueError) as e:
                print >> sys.stderr, 'Not a valid (YYYY-MM-DD) ({})'.format(e.message)


def do_program():
    parser = argparse.ArgumentParser(description='Pretty basic interval task management system')

    parser.add_argument('--database', '-d', help='database uri, defaults to sqlite:///$HOME/.tasker.sqlite')

    subparsers = parser.add_subparsers(dest='command', help='sub-commands')

    subparsers.add_parser(TaskerCliOptions.CREATE, help='create a task')
    subparsers.add_parser(TaskerCliOptions.CHECK, help='print pending/incomplete tasks')

    complete_parser = subparsers.add_parser(TaskerCliOptions.COMPLETE, help='complete an existing task')
    complete_parser.add_argument('task_id', help='task ID to complete')

    args = parser.parse_args()

    tasker_cli = TaskerCli(args.database)

    if args.command == TaskerCliOptions.CREATE:
        try:
            tasker_cli.create_task()
        except (KeyboardInterrupt, EOFError):
            print ''
            sys.exit(-1)
    elif args.command == TaskerCliOptions.CHECK:
        tasker_cli.print_tasks()
    elif args.command == TaskerCliOptions.COMPLETE:
        tasker_cli.complete_task(args.task_id)
    else:  # pragma: no cover
        # Shouldn't actually be reachable, but a good failsafe in case commands are added to the list without actually
        # being implemented.
        parser.print_usage(sys.stderr)
        sys.exit(-1)


if __name__ == '__main__':
    do_program()
