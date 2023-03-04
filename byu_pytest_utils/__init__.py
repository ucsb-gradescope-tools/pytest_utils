import inspect
from pathlib import Path
import pytest

pytest.register_assert_rewrite("byu_pytest_utils.io_checker")
pytest.register_assert_rewrite("byu_pytest_utils.dialog")

from .test_utils import compare_files, run_python, with_import
from .decorators import max_score, visibility, tags
from .io_checker import check_io
from .dialog import dialog

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
