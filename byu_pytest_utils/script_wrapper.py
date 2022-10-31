import os
import runpy
import sys
from functools import wraps


class ScriptWrapper:
    def __init__(self, expected_output_file):
        with open(expected_output_file) as file:
            self.expected_output = file.read()
        self.observed_output = ""

    def _assert_output(self):
        assert self.observed_output == self.expected_output[:len(self.observed_output)]

    @wraps(input)
    def _input(self, prompt):
        self.observed_output += prompt
        print(prompt, end='')
        self._assert_output()
        # Input is from the current position to next newline in expected output
        next_newline = self.expected_output.find('\n', len(self.observed_output))
        result = self.expected_output[len(self.observed_output):next_newline]
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
        assert self.observed_output == self.expected_output

        return result


if __name__ == '__main__':
    expected_dialog_file = sys.argv[1]
    script, *args = sys.argv[2:]
    wrapper = ScriptWrapper(expected_dialog_file)
    wrapper.run_script(script, *args)
    # To test, run
    # python byu_pytest_utils/script_wrapper.py test_expected_output.txt test_script.py woot

