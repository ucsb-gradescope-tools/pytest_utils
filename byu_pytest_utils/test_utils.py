import importlib
import os.path
import subprocess
from pathlib import Path
import inspect
import pytest
import sys


def compare_files(file_1, file_2):
    with open(file_1) as f1:
        with open(file_2) as f2:
            expected = f1.read().strip()
            observed = f2.read().strip()
            assert observed == expected


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
    return proc.stdout.decode().replace('\r','')


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
