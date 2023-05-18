from byu_pytest_utils import dialog_exec, cache

# This file demonstrates how we can use
#  predefined assets (like compiled binaries)
#  in the dialog framework

@cache
def binary():
    print('g++ -o ./exec main.cpp')
    return './exec'

@dialog_exec(
    'example.dialog.txt',
    binary, 'arg1', 'arg2'
)
def test_binary(): ...

