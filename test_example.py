from byu_pytest_utils.decorators import max_score
from byu_pytest_utils.dialog import dialog


@max_score(10)
def test_pass():
    print("pass!")


@max_score(20)
def test_fail():
    assert 7 == 8


@max_score(10)
def test_check_io_old():
    from byu_pytest_utils import check_io
    check_io(
        "test_expected_output.txt",
        "test_script.py", 'woot'
    )


@max_score(10)
def test_check_io_input_indicated():
    from byu_pytest_utils import check_io
    check_io(
        "test_expected_output_new.txt",
        "test_script.py", 'woot'
    )


@dialog(
    "test_expected_output_dialog.txt",
    "test_script.py", 'woot'
)
@max_score(10)
def test_dialog(group_name):
    pass


@dialog(
    "test_expected_output_new_extra_input.txt",
    "test_script.py", 'woot'
)
@max_score(10)
def test_dialog_new_extra_input(group_name): ...


@max_score(10)
@dialog(
    "test_expected_output_new_missing_input.txt",
    "test_script.py", 'woot'
)
def test_check_io_new_missing_input(group_name): ...


if __name__ == '__main__':
    import pytest

    retcode = pytest.main(["--no-header", "-vv", "--capture=tee-sys"])
    print(retcode)
