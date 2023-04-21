from byu_pytest_utils import dialog, max_score


@dialog(
    "dialogs/test_dialog_should_pass.txt",
    "script_for_dialog_passes.py", 'woot', 7
)
@max_score(10)
def test_dialog_should_pass(group_name):
    """Everything should pass"""

@dialog(
    "dialogs/test_dialog_should_pass.txt",
    "script_for_dialog_fails.py", 'woot', 7, 'foobar'
)
@max_score(10)
def test_dialog_should_fail(group_name):
    """
    seven should pass, but another-number and everything-else should fail
    """

@dialog(
    "dialogs/test_dialog_expects_more_input.txt",
    "script_for_dialog_passes.py", 'woot'
)
@max_score(10)
def test_dialog_expects_more_input_should_fail(group_name):
    """
    args, seven, and eight should pass, 
    but nine and everything-else should not
    """

@max_score(10)
@dialog(
    "dialogs/test_dialog_expects_less_input.txt",
    "script_for_dialog_passes.py", 'woot'
)
def test_dialog_expects_less_input(group_name):
    """
    seven should pass, but everything-else should fail
    There should be an error: "Input called more times than expected"
    """


