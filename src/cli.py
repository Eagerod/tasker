import argparse
import os
import sqlite3
import sys
from datetime import date

from tasker import Tasker, InvalidStartDateException, DuplicateNameException, InvalidCadenceException

class Queries(object):
    SELECT_INCOMPLETE_TIS = '''
        SELECT ti.id, t.name, ti.date
        FROM tasks t
        JOIN tis ti ON ti.task = t.id
        WHERE ti.done = "false";
    '''

class TaskCreator(object):
    def __init__(self, db):
        self.db = db

    def _get_task_name(self):
        tasker = Tasker(self.db)
        cursor = self.db.cursor()

        while True:
            name = raw_input('Enter task name: ')
            try:
                tasker.assert_name_unique(name)
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
                Tasker(self.db).assert_cadence_valid(cadence)
                return cadence
            except InvalidCadenceException as e:
                print >> sys.stderr, e.message

    def _get_first_date(self):
        while True:
            start = raw_input('When does this start (YYYY-MM-DD): ')
            try:
                return date(*[int(i) for i in start.split('-')])
            except:
                print >> sys.stderr, 'Not a valid (YYYY-MM-DD)'

    def create_task_from_user_input(self):
        tasker = Tasker(self.db)
        name = self._get_task_name()
        cadence = self._get_cadence()
        while True:
            start = self._get_first_date()
            try:
                tasker.assert_start_date_valid(cadence, start)
                break
            except InvalidStartDateException as e:
                print >> sys.stderr, e.message

        Tasker(self.db).create_task(name, cadence, start)


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
            print 'To complete any task, use:\n    {} --complete N'.format(sys.argv[0])


class TaskerCli(object):
    def __init__(self, database=None):
        if not database:
            database = os.path.join(os.path.expanduser('~'), '.tasker.sqlite')

        self.db = sqlite3.connect(database)
        self.tasker = Tasker(self.db)

    def create_task(self):
        TaskCreator(self.db).create_task_from_user_input()

    def print_tasks(self):
        self.tasker.schedule_tasks()
        TaskPrinter(self.db).print_remaining_tasks()

    def complete_task(self, ti_id):
        self.tasker.complete_task_instance(ti_id)



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