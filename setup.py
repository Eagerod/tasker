import setuptools


setuptools.setup(
    name='tasker',
    license='MIT',
    version='0.3.4',
    description='manage recurring tasks on the command line.',
    author='Aleem Haji',
    author_email='hajial@gmail.com',
    packages=['tasker', 'tasker.intervals', 'tasker.models'],
    package_dir={'tasker': 'src'},
    entry_points={
        'console_scripts': [
            'tasker = tasker.cli:do_program'
        ]
    },
    install_requires=[
        'sqlalchemy~=1.1.15'
    ],
    extras_require={
        'mysql': 'mysql-python~=1.2.5'
    }
)
