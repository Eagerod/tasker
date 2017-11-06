from fabric.api import local, task


@task
def setup(quiet=False):
    local('pip install {} -r requirements.txt'.format('--quiet' if quiet else ''))


@task
def lint():
    setup(quiet=True)
    local('flake8 .')


@task
def test():
    setup(quiet=True)
    local('python -m unittest discover -v -t . -s tests')


@task
def coverage():
    setup(quiet=True)
    local('coverage run -m unittest discover -v -t . -s tests')
    local('coverage report')


@task
def install_globally():
    local('pip install --upgrade .')
