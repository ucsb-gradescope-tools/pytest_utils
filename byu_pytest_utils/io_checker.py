import os.path
import runpy
import sys
from functools import wraps


def check_io(expected_dialog_file, script_name, *script_args, echo_output=False):
    """
    Run the script and check it's input and print calls against the expected dialog
    :param expected_dialog_file: A file that contains the expected dialog of the script
    :param script_name: Name of script (including necessary path and .py extension) being called
    :param script_args: Command-line arguments to the script
    :return: A dictionary containing the resulting namespace of the executed script
    """
    if not os.path.exists(script_name):
        raise Exception(f'{script_name} not found. Was it submitted?')

    wrapper = IOChecker(expected_dialog_file, echo_output)
    return wrapper.run_script(script_name, *script_args)


class IOChecker:
    def __init__(self, expected_output_file, echo_output):
        self.echo_output = echo_output
        with open(expected_output_file) as file:
            self.expected_output = file.read()
        self.observed_output = ""

    def _assert_output(self):
        if self.observed_output != self.expected_output[:len(self.observed_output)]:
            next_newline = self.expected_output.find('\n', len(self.observed_output))
            assert self.observed_output == self.expected_output[:next_newline], "Program output did not match expected output"

    @wraps(input)
    def _input(self, prompt):
        self.observed_output += prompt
        if self.echo_output:
            print(prompt, end='')
        self._assert_output()
        # Input is from the current position to next newline in expected output
        next_newline = self.expected_output.find('\n', len(self.observed_output))
        result = self.expected_output[len(self.observed_output):next_newline]
        if self.echo_output:
            print(result)
        self.observed_output += result + '\n'
        return result

    @wraps(print)
    def _print(self, *values, **kwargs):
        sep = kwargs.get('sep', ', ')
        end = kwargs.get('end', '\n')
        res = sep.join(str(t) for t in values) + end
        self.observed_output += res
        self._assert_output()
        if self.echo_output:
            print(*values, **kwargs)

    def run_script(self, script_name, *args):
        # Intercept input, print, and sys.argv
        sys.argv = [script_name, *(str(a) for a  in args)]
        _globals = {
            'input': self._input,
            'print': self._print,
            'sys': sys
        }

        # Run script as __main__
        result = runpy.run_path(script_name, _globals, '__main__')

        # Final assertion of observed and expected output
        assert self.observed_output == self.expected_output, "Program output did not match expected output"

        return result


if __name__ == '__main__':
    expected_dialog_file = sys.argv[1]
    script, *args = sys.argv[2:]
    check_io(expected_dialog_file, script, *args, echo_output=True)
    # To test from the command line, run
    # python -m byu_pytest_utils.io_checker test_expected_output.txt test_script.py woot

