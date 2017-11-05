import argparse
import sys

from tasker import TaskerCli


class TaskerCliCommand(object):
    ADD_TASK = object()
    RUN_CHECK = object()


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