import argparse
import os.path
import re
import runpy
import sys
import traceback
from functools import wraps

from byu_pytest_utils.edit_dist import edit_dist


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


def record_script(dialog_file, script_name, *script_args):
    # Intercept input, print, and sys.argv
    sys.argv = [script_name, *(str(a) for a in script_args)]
    with open(dialog_file, 'w') as file:
        def _input(prompt):
            file.write(prompt)
            response = input(prompt)
            file.write(f'<<{response}>>\n')
            return response

        def _print(*args, **kwargs):
            print(*args, **kwargs)
            print(*args, **kwargs, file=file)

        _globals = {
            'input': _input,
            'print': _print,
            'sys': sys
        }

        # Run script as __main__
        result = runpy.run_path(script_name, _globals, '__main__')

    return result


class IOChecker:
    DEFAULT_GROUP = '.'
    MAX_PARTIAL_CREDIT = 1

    def __init__(self, dialog_file, echo_output):
        self.echo_output = echo_output

        with open(dialog_file) as file:
            text = file.read()
            self.inputs, no_inputs = self._extract_input(text)
            self.weights, self.groups, self.expected_output = self._extract_weights(no_inputs)
        self.observed_output = ""

    @staticmethod
    def _extract_input(dialogue_contents: str):
        # Find all tokens delimited by << and >> and return them
        # as a list along with the original contents with the << and >> removed
        inputs = re.findall(r'<<(.*?)>>', dialogue_contents)
        dialogue_contents = re.sub(r'<<(.*?)>>', r'\1', dialogue_contents)
        return inputs, dialogue_contents

    @staticmethod
    def _extract_weights(dialog_contents: str):
        # blah blah [[foo;10]] blah blah
        group_weights = {IOChecker.DEFAULT_GROUP: 0}
        groups = ''
        # Iterate through the dialog contents
        # Characters not in a group are assigned to weight group 'a'
        # Each weight group is assigned the next letter of the alphabet
        # A group starts with [[ and ends with ]]
        # The semicolon separates the group text from the weight
        # All text in a group is assigned to the same weight group
        # e.g.
        # quux [[foo;30]] bar [[baz;20]] quux
        # produces groups: aaaaabbbaaaacccaaaa
        # and group_weights: {'-': 40, 'b': 30, 'c': 20}
        i = 0
        while i < len(dialog_contents):
            if dialog_contents[i:i + 2] == '[[':
                # Start of a group
                group_name = chr(ord('a') - 1 + len(group_weights))
                group_match = re.search(r'\[\[(.*?);(\d+?)]]', dialog_contents[i:], flags=re.DOTALL)
                group_text = group_match.group(1)
                group_weights[group_name] = int(group_match.group(2))
                groups += group_name * len(group_text)
                i += group_match.end()
            else:
                # Not in a group
                groups += IOChecker.DEFAULT_GROUP
                i += 1
        total = sum(group_weights.values())
        if total > 100:
            raise Exception('Group weights must add up to 100 or less')
        group_weights[IOChecker.DEFAULT_GROUP] = 100 - total

        # Then remove the groups from the dialog contents
        dialog_contents = re.sub(r'\[\[(.*?);(.+?)]]', r'\1', dialog_contents, flags=re.DOTALL)

        return group_weights, groups, dialog_contents

    def _assert_output(self):
        # Pad the output with spaces so that the diff is easier to read
        def pad(s):
            return s + ' ' * (80 - len(s))

        try:
            assert pad(self.observed_output) == pad(self.expected_output)
        except AssertionError as err:
            edit_score, obs, exp = edit_dist(
                self.observed_output,
                self.expected_output,
                GAP='`'
            )

            # Cap partial credit at 90%
            # The last 10% is for getting everything correct
            err._partial_credit = IOChecker.MAX_PARTIAL_CREDIT * self._compute_partial_credit(obs, exp)
            raise

    def _compute_partial_credit(self, obs, exp):
        # insert gaps (i.e. DEFAULT_GROUP) into self.groups to match exp
        # then iterate over obs, exp, and groups
        # to compute rate of matches per group
        # (a gap in obs counts as group DEFAULT_GROUP)
        # and return the weighted average
        # e.g. if groups is '---bbbccc'
        # and group_weights is {'-': 50, 'b': 20, 'c': 30}
        # and exp is 'foobar`baz'
        # and obs is 'boobarflaz'
        # then groups should become '---bbb-ccc'
        # and the weighted average should be
        #   2/4 * 50 + 3/3 * 20 + 2/3 * 30 = 65
        if len(exp) - exp.count('`') != len(self.groups):
            raise Exception('Too many gaps in expected output')
        groups = ''
        i = 0
        g = 0
        while i < len(exp):
            if exp[i] == '`':
                groups += IOChecker.DEFAULT_GROUP
                i += 1
            else:
                groups += self.groups[g]
                g += 1
                i += 1
        assert len(groups) == len(exp)

        # Compute weighted average
        group_counts = {}
        group_matches = {}
        for obs_c, exp_c, group in zip(obs, exp, groups):
            if obs_c == exp_c:
                group_matches[group] = group_matches.get(group, 0) + 1
            group_counts[group] = group_counts.get(group, 0) + 1

        weighted_sum = 0
        for group, count in group_counts.items():
            weighted_sum += group_matches.get(group, 0) / count * self.weights[group]

        return round(weighted_sum / 100, 4)

    def _final_assert_output(self):
        self._assert_output()

    def _consume_output(self, printed_text):
        self.observed_output += printed_text
        if self.echo_output:
            print(printed_text, end='')

    @wraps(input)
    def _input(self, prompt):
        self._consume_output(prompt)
        if not self.inputs:
            raise Exception("input() called more times than expected")
        input_text = self.inputs.pop(0)
        self._consume_output(input_text + '\n')
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
            result = None
            # get stack trace as string
            self._consume_output(f'\nException: {ex}\n')
            self._consume_output(traceback.format_exc())

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
        result = self.expected_output[len(self.observed_output):next_newline].strip()
        if self.echo_output:
            print(result)
        self.observed_output += result + '\n'
        return result

    @wraps(print)
    def _print(self, *values, **kwargs):
        sep = kwargs.get('sep', ' ')
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
    parser = argparse.ArgumentParser()
    parser.add_argument('dialog_file', help='Dialog file to write')
    parser.add_argument('python_script', help='Python script to run')
    parser.add_argument('script_args', nargs='*', help='Arguments to the python script (if any)')
    args = parser.parse_args()

    record_script(args.dialog_file, args.python_script, *args.script_args)
