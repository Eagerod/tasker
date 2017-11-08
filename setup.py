import setuptools


setuptools.setup(
    name='tasker',
    license='MIT',
    version='0.0.4',
    description='manage recurring tasks on the command line.',
    author='Aleem Haji',
    author_email='hajial@gmail.com',
    packages=['tasker', 'tasker.intervals'],
    package_dir={'tasker': 'src'},
    entry_points={
        'console_scripts': [
            'tasker = tasker.cli:do_program'
        ]
    }
)
