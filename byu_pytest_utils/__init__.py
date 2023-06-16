import inspect
from pathlib import Path
import pytest

pytest.register_assert_rewrite("byu_pytest_utils.io_checker")
pytest.register_assert_rewrite("byu_pytest_utils.dialog")

from .utils import run_python_script, with_import, ensure_missing  # nopep8
from .cpp_utils import compile_cpp  # nopep8
from .decorators import max_score, visibility, tags, cache  # nopep8
from .dialog import dialog, dialog_exec  # nopep8
from functools import cache  # nopep8

# Type stubs to make these variables discoverable
# Actual values are supplied by __getattr__
this_folder: Path
test_files: Path


def _get_caller_file() -> Path:
    s = inspect.stack()
    # Find index of the first frame outside byu-pytest-utils
    index = 0
    while s[index].filename == __file__:
        index += 1
    return Path(s[index].filename).absolute()


# We want `this_folder` to be the folder of the caller
def _get_caller_folder() -> Path:
    caller_file = _get_caller_file()
    return caller_file.parent


def __getattr__(name):
    if name == 'this_folder':
        return _get_caller_folder()
    elif name == 'test_files':
        return _get_caller_folder() / 'test_files'
    else:
        return globals()[name]
