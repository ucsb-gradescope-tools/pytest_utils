from byu_pytest_utils.decorators import max_score


@max_score(10)
def test_pass():
    print("pass!")


@max_score(20)
def test_fail():
    assert 7 == 8


if __name__ == '__main__':
    import pytest

    retcode = pytest.main(["--no-header", "-vv", "--capture=tee-sys"])
    print(retcode)
