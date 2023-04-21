from byu_pytest_utils.decorators import max_score

@max_score(10)
def test_should_pass():
    print("pass!")


# The purpose of this test is to see
# how a failure behaves in pycharm/results.json
@max_score(20)
def test_should_fail():
    assert 7 == 8


