# Tasker

Tasker is a python application that manages a database of to-dos.
Tasker was created because of what I've found to be the lack of persistence in typical calendar apps' reminder systems.
Tasker can be very easily configured to run when starting a new terminal session, which can end up providing just the right amount of nudging to convince you to get things done.

## Installation

Since this is still a personal project, and hasn't been released to the general, it doesn't live on pypi.
It can still be installed using pip with:

```
pip install https://github.com/eagerod/tasker.git@<version>#egg=tasker
```
or
```
pip install git+ssh://github.com/eagerod/tasker.git@<version>#egg=tasker
```

## Usage

Start out by creating some tasks:

```
$ tasker create
> Enter task name: Pay Phone Bill
> Available cadences:
>   1. Once
>   2. Daily
>   3. Weekly
>   4. Monthly
> Select cadence: monthly
> When does this start (YYYY-MM-DD; default today): 2017-11-22
```

Tasker will automatically create an sqlite3 database at `$HOME/.tasker.sqlite`. 
This will keep track of the tasks that you've done, and the tasks that you have yet to do.
You can check your list of unfinished tasks with:

```
$ tasker check     
> Things to do:
>       1. (2017-11-22) Pay Phone Bill
> To complete any task, use:
>     tasker complete N
```

After completing a task with:

```
$ tasker complete 1
```

Tasker will reschedule the next instance of your task the next time you check your tasks list

```
$ tasker check
> Things to do:
>       2. (2017-12-22) Pay Phone Bill
> To complete any task, use:
>     tasker complete N
```

Note: Tasker does support using MySQL instead of sqlite3.
To use it, install Tasker with the mysql feature, and provide a database parameter when making command line calls:

```
pip install https://github.com/eagerod/tasker.git@<version>#egg=tasker[mysql]
```
or
```
pip install git+ssh://github.com/eagerod/tasker.git@<version>#egg=tasker[mysql]
```

Create a database for Tasker in your mysql instance, and run

```
$ tasker --database mysql://root@localhost/tasker create
...
```

## Usage on Shell Start 

Using Tasker when starting a new shell session is the easiest way to get a little nudge for your remaining tasks.

Mac:
```
echo "tasker check" >> ~/.bash_profile
```
Linux:
```
echo "tasker check" >> ~/.bashrc
```

Now whenever you open a new terminal, you'll be reminding of remaining tasks in Tasker.

## Default Cadences

By default, there are 4 task cadences that can be used.

- Once: When the task has been scheduled and completed, it will never appear again.
- Daily: When the task has been scheduled and completed, an instance of the task will appear the next day
- Weekly: When the task has been scheduled and completed, an instance of the task will appear on the next n-th day of the week. Ex. Tasks will always appear on Wednesday if the initial task was scheduled on Wednesday.
- Monthly: When the task has been scheduled and completed, an instance of the task will appear on the next n-th day of the month. Ex. Tasks will always appear on the 22th of the month if the initial task was scheduled on the 22th.
