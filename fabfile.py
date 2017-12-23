import os

from fabric.api import local, task, runs_once


PROJECT_ROOT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@task
@runs_once
def setup(quiet=False):
    local('pip install {} -r requirements.txt'.format('--quiet' if quiet else ''))


@task
@runs_once
def lint():
    setup(quiet=True)
    local('flake8 .')


@task
@runs_once
def test():
    setup(quiet=True)
    local('python -m unittest discover -v -t . -s tests')


@task
@runs_once
def coverage():
    setup(quiet=True)

    # To test things in the CLI, coverage has to be started with, and all subprocesses within have to be started with
    # COVERAGE_PROCESS_START (http://coverage.readthedocs.io/en/coverage-4.2/subprocess.html).
    # A sitecustomize.py file must also be created to that when python subprocesses are fired up, they can recognize
    # that they're a part of a coverage run.
    coverage_file = os.path.join(PROJECT_ROOT_DIRECTORY, '.coveragerc')
    sitecustomize_path = os.path.join(PROJECT_ROOT_DIRECTORY, 'sitecustomize.py')

    sitecustomize_file_contents = 'import coverage\ncoverage.process_startup()\n'

    with open(sitecustomize_path, 'w') as f:
        f.write(sitecustomize_file_contents)

    local('coverage erase')
    local('COVERAGE_PROCESS_START={} coverage run -m unittest discover -v -t . -s tests'.format(coverage_file))
    local('coverage combine')
    local('coverage report -m')

    os.unlink(sitecustomize_path)


@task
@runs_once
def install_globally(extras=''):
    if extras:
        extras = '[{}]'.format(extras)
    local('pip install --upgrade .{}'.format(extras))
