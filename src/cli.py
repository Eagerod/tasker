import argparse
import os
import sqlite3
import sys
from datetime import date

from tasker import Tasker, InvalidStartDateException, DuplicateNameException, InvalidCadenceException


class TaskerCli(object):
    def __init__(self, database=None):
        if not database:
            database = os.path.join(os.path.expanduser('~'), '.tasker.sqlite')

        self.db = sqlite3.connect(database)
        self.tasker = Tasker(self.db)

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
            print 'Things to do:'
            for row in task_instances:
                print '  {}. ({}) {}'.format(str(row.id).rjust(5), row.date, row.task)
            print 'To complete any task, use:\n    {} --complete N'.format(sys.argv[0])

    def _get_task_name(self):
        while True:
            name = raw_input('Enter task name: ')
            try:
                self.tasker.assert_name_unique(name)
                return name
            except DuplicateNameException as e:
                print >> sys.stderr, e.message

    def _get_cadence(self):
        while True:
            print 'Available cadences:'
            print '\n'.join('  {}. {}'.format(i+1, o.title()) for i, o in enumerate(Tasker.Cadence.ALL))
            cadence = raw_input('Select cadence: ')
            try:
                cadence = Tasker.Cadence.ALL[int(cadence) - 1]
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
    command_group = parser.add_mutually_exclusive_group()

    parser.add_argument('--database', '-d', help='path to database file, if default not desired')

    command_group.add_argument('--create', action='store_true', help='starts an interactive task creation')
    command_group.add_argument('--check', action='store_true', help='prints any tasks that are unfinished and exits')
    command_group.add_argument('--complete', dest='task_id', help='complete an existing task')

    args = parser.parse_args()

    tasker = TaskerCli(args.database)

    if args.create:
        tasker.create_task()
    elif args.check:
        tasker.print_tasks()
    elif args.task_id:
        tasker.complete_task(args.task_id)
    else:
        parser.print_usage()
        sys.exit(-1)


if __name__ == '__main__':
    do_program()
