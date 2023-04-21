import importlib
import os.path
import runpy
import subprocess
from functools import wraps
from pathlib import Path
import inspect
from typing import Union

import pytest
import sys


# Deprecated - use dialog instead
def compare_files(expected_file, observed_file):
    with open(expected_file) as exp_f:
        with open(observed_file) as obs_f:
            expected = exp_f.read().strip()
            observed = obs_f.read().strip()
            assert observed == expected


def run_python_script(script, *args, module='__main__'):
    """
    Run the python script with arguments

    If the script expects STDIN, use the dialog framework instead

    :param script: Python script to run
    :param args: Arguments to the python script
    :param module: Defaults to '__main__'
    :return: Namespace as a result of running the script
    """
    if not os.path.exists(script):
        pytest.fail(f'The file {script} does not exist. Did you submit it?')

    def _input(*args):
        raise Exception("input function not supported for this test")

    sys.argv = [script, *(str(a) for a in args)]
    _globals = {
        'sys': sys,
        'input': _input
    }
    return runpy.run_path(script, _globals, module)


# Deprecated - use run_python_script instead
def run_python(*command, stdin=None):
    for token in command:
        missing = None
        if isinstance(token, str) and token.endswith('.py') and not os.path.exists(token):
            missing = os.path.basename(token)
        elif isinstance(token, Path) and token.name.endswith('.py') and not token.exists():
            missing = token.name

        if missing:
            print(f'Missing: {token}')
            pytest.fail(f'The file {missing} does not exist. Did you submit it?')

    input_bytes = stdin.encode() if stdin else None

    _command = [sys.executable]
    _command.extend((str(c) for c in command))
    proc = subprocess.run(_command, input=input_bytes, capture_output=True)
    if proc.returncode != 0:
        pytest.fail(f'The command {" ".join(_command)} failed with exit code {proc.returncode}. '
                    f'{proc.stderr.decode()}')
    return proc.stdout.decode().replace('\r', '')


def ensure_missing(file: Union[Path, str]):
    """
    Use the decorator to ensure the provided file is always missing
    when the test starts
    """
    if isinstance(file, str):
        file = Path(file)
    def decorator(func):
        @wraps(func)
        def new_func(*args, **kwargs):
            file.unlink(missing_ok=True)
            return func(*args, **kwargs)

        return new_func

    return decorator


def with_import(module_name=None, function_name=None):
    # Create a decorator
    def decorator(test_function):
        # Import function_name from module_name, then run function
        # with function_name passed in as first arg
        nonlocal function_name
        nonlocal module_name
        params = inspect.signature(test_function).parameters
        first_param = next((pname for pname, _ in params.items()))
        function_name = function_name or first_param
        module_name = module_name or function_name

        @wraps(test_function)
        def new_test_function(*args, **kwargs):
            try:
                module = importlib.import_module(module_name)
                func = getattr(module, function_name)
                return test_function(func, *args, **kwargs)

            except ModuleNotFoundError as err:
                pytest.fail(
                    f'{type(err).__name__}: {err}\n'
                    f'Unable to load {module_name}.py. '
                    f'Was {module_name}.py submitted?'
                )
            except ImportError as err:
                pytest.fail(
                    f'{type(err).__name__}: {err}\n'
                    f'Unable to load {module_name}.py. '
                    f'Are there errors in the file?'
                )
            except KeyError as err:
                pytest.fail(
                    f'{type(err).__name__}: {err}\n'
                    f'Unable to load {function_name} from {module_name}.py. '
                    f'Is {function_name} defined?'
                )

        # Modify signature to look like test_function but without
        # anything filled by with_import
        sig = inspect.signature(test_function)
        sig._parameters = dict(sig.parameters)
        del sig._parameters[first_param]
        new_test_function.__signature__ = sig

        return new_test_function

    if callable(module_name):
        # The decorator was used without arguments,
        # so this call is the decorator
        func = module_name
        module_name = None
        return decorator(func)
    else:
        return decorator
