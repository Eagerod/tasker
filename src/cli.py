import argparse
import os
import sqlite3
import sys
from datetime import date

from tasker import Tasker, InvalidStartDateException, DuplicateNameException, InvalidCadenceException
from intervals.interval_factory import IntervalFactory, UnsupportedIntervalException


class TaskerCliOptions(object):
    ATTACH = 'attach'
    CHECK = 'check'
    COMPLETE = 'complete'
    CREATE = 'create'


class TaskerCli(object):
    def __init__(self, database=None):
        if not database:
            database = os.path.join(os.path.expanduser('~'), '.tasker.sqlite')

        self._db_path = database
        self.db = sqlite3.connect(database)
        self.tasker = Tasker(self.db)

        self._run_path = sys.argv[0]
        # Scan through $PATH, and determine if this could be run without the full path.
        for a_path in os.environ['PATH'].split(os.pathsep):
            if a_path[-1] != os.path.sep:
                a_path = a_path + os.path.sep
            if self._run_path.find(a_path, 0, len(a_path)) == 0:
                self._run_path = self._run_path[len(a_path):]

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

    def attach_bash_profile(self):
        command_length = len(sys.argv[0])
        with open(os.path.join(os.path.expanduser('~'), '.bash_profile'), 'a+') as bash_profile_file:
            bash_profile_file.seek(0)
            file_lines = []
            done = False
            for line in bash_profile_file.readlines():
                if (line.find('tasker', 0, 6) == 0 or line.find(sys.argv[0], 0, command_length) == 0):
                    if done:
                        continue

                    file_lines.append('tasker --database "{}" {}\n'.format(self._db_path, TaskerCliOptions.CHECK))
                    done = True
                else:
                    file_lines.append(line)
            bash_profile_file.seek(0)
            bash_profile_file.truncate()
            bash_profile_file.writelines(file_lines)

    def _print_remaining_tasks(self):
        task_instances = self.tasker.get_incomplete_task_instances()
        if len(task_instances):
            print 'Things to do:'
            for row in task_instances:
                print '  {}. ({}) {}'.format(str(row.id).rjust(5), row.date, row.task)
            print 'To complete any task, use:\n    {} complete N'.format(self._run_path)

    def _get_task_name(self):
        while True:
            name = raw_input('Enter task name: ')
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
            cadence = raw_input('Select cadence: ')
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
            start = raw_input('When does this start (YYYY-MM-DD): ')
            try:
                return date(*[int(i) for i in start.split('-')])
            except (TypeError, ValueError) as e:
                print >> sys.stderr, 'Not a valid (YYYY-MM-DD) ({})'.format(e.message)


def do_program():
    parser = argparse.ArgumentParser(description='Pretty basic interval task management system')

    parser.add_argument('--database', '-d', help='path to database file, defaults to ~/.tasker.sqlite')

    subparsers = parser.add_subparsers(dest='command', help='sub-commands')

    create_parser = subparsers.add_parser(TaskerCliOptions.CREATE, help='create a task')

    check_parser = subparsers.add_parser(TaskerCliOptions.CHECK, help='print pending/incomplete tasks')
    
    complete_parser = subparsers.add_parser(TaskerCliOptions.COMPLETE, help='complete an existing task')
    complete_parser.add_argument('task_id', help='task ID to complete')

    attach_parser = subparsers.add_parser(TaskerCliOptions.ATTACH, 
                                          help='attach tasker to ~/.bash_profile to check on terminal start')

    args = parser.parse_args()

    tasker = TaskerCli(args.database)

    if args.command == TaskerCliOptions.CREATE:
        tasker.create_task()
    elif args.command == TaskerCliOptions.CHECK:
        tasker.print_tasks()
    elif args.command == TaskerCliOptions.COMPLETE:
        tasker.complete_task(args.task_id)
    elif args.command == TaskerCliOptions.ATTACH:
        tasker.attach_bash_profile()
    else:  # pragma: no cover
        # Shouldn't actually be reachable, but a good failsafe in case commands are added to the list without actually
        # being implemented.
        parser.print_usage(sys.stderr)
        sys.exit(-1)


if __name__ == '__main__':
    do_program()
