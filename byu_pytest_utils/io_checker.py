import os.path
import runpy
import sys
from functools import wraps

import pytest


def check_io(expected_dialog_file, script_name, *script_args, echo_output=False):
    """
    Run the script and check it's input and print calls against the expected dialog
    :param echo_output:
    :param expected_dialog_file: A file that contains the expected dialog of the script
    :param script_name: Name of script (including necessary path and .py extension) being called
    :param script_args: Command-line arguments to the script
    :return: A dictionary containing the resulting namespace of the executed script
    """
    if not os.path.exists(script_name):
        raise Exception(f'{script_name} not found. Was it submitted?')

    with open(expected_dialog_file) as file:
        if "<<" not in file.read():
            # Old behavior
            wrapper = IOCheckerObsolete(expected_dialog_file, echo_output)
            return wrapper.run_script(script_name, *script_args)
        else:
            # New behavior
            wrapper = IOChecker(expected_dialog_file, echo_output)
            return wrapper.run_script(script_name, *script_args)


class IOChecker:
    def __init__(self, dialogue_file, echo_output):
        self.echo_output = echo_output
        with open(dialogue_file) as file:
            self.dialogue_content = file.read()
        self.dialogue_pos = 0
        self.expected_output = ""
        self.observed_output = ""

    def _assert_output(self):
        for p, (o, e) in enumerate(zip(self.observed_output, self.expected_output)):
            if o != e:
                assert self.observed_output[:p] == self.expected_output[:p]

        assert self.observed_output == self.expected_output

    def _final_assert_output(self):
        # Grab whatever is left in the dialogue file
        # add it to expected_output
        # and assert_output
        self.expected_output += self.dialogue_content[self.dialogue_pos:] \
            .replace('<<', '').replace('>>', '')
        self.dialogue_pos = len(self.dialogue_content)
        self._assert_output()

    def _consume_output(self, printed_text):
        self.observed_output += printed_text
        # expected_output gets the next part of the dialogue file
        # either the length of the printed text or to the next <<
        # whichever comes first
        next_input_pos = self.dialogue_content.find('<<', self.dialogue_pos)
        if next_input_pos == -1:
            next_input_pos = len(self.dialogue_content)
        next_chunk_pos = min(next_input_pos, self.dialogue_pos + len(printed_text))
        self.expected_output += self.dialogue_content[self.dialogue_pos:next_chunk_pos]
        self.dialogue_pos = next_chunk_pos
        if self.echo_output:
            print(printed_text, end='')
        self._assert_output()

    @wraps(input)
    def _input(self, prompt):
        self._consume_output(prompt)
        # Input is found in the dialogue file between << and >>
        # If the next part of the dialogue file is not an input, then
        #   add the missing text to the expected output
        if not self.dialogue_content[self.dialogue_pos:].startswith('<<'):
            # The user didn't print enough before calling input
            # Add the missing text to the expected output
            # and assert_output
            next_input_pos = self.dialogue_content.find('<<', self.dialogue_pos)
            if next_input_pos == -1:
                next_input_pos = len(self.dialogue_content)
            self.expected_output += self.dialogue_content[self.dialogue_pos:next_input_pos]
            self.dialogue_pos = next_input_pos
            self._assert_output()
        else:
            # The user printed enough before calling input
            # Consume the input from the dialogue file
            self.dialogue_pos += 2
            end_input_pos = self.dialogue_content.find('>>', self.dialogue_pos)
            if end_input_pos == -1:
                raise Exception("Missing >> in dialogue file")
            input_text = self.dialogue_content[self.dialogue_pos:end_input_pos]
            # advance past the >> and the newline
            self.dialogue_pos = end_input_pos + 3
            self.expected_output += input_text + '\n'
            self.observed_output += input_text + '\n'
            if self.echo_output:
                print(input_text)
            return input_text

    @wraps(print)
    def _print(self, *values, **kwargs):
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        res = sep.join(str(t) for t in values) + end
        self._consume_output(res)

    def run_script(self, script_name, *args, module='__main__'):
        # Intercept input, print, and sys.argv
        sys.argv = [script_name, *(str(a) for a in args)]
        _globals = {
            'input': self._input,
            'print': self._print,
            'sys': sys
        }

        # Run script as __main__
        try:
            result = runpy.run_path(script_name, _globals, module)
        except Exception as ex:
            pass

        # Final assertion of observed and expected output
        self._final_assert_output()

        return result


class IOCheckerObsolete:
    def __init__(self, expected_output_file, echo_output):
        self.echo_output = echo_output
        with open(expected_output_file) as file:
            self.expected_output = file.read()
        self.observed_output = ""

    def _assert_output(self):
        if self.observed_output != self.expected_output[:len(self.observed_output)]:
            next_newline = self.expected_output.find('\n', len(self.observed_output))
            assert self.observed_output == self.expected_output[
                                           :next_newline], "Program output did not match expected output"

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
        sys.argv = [script_name, *(str(a) for a in args)]
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
