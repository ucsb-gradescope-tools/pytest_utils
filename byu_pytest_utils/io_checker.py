import argparse
import math
import os.path
import re
import runpy
import sys
import traceback
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
    def __init__(self, dialog_file, echo_output):
        self.echo_output = echo_output

        with open(dialog_file) as file:
            self.inputs, self.expected_output = self._extract_input(file.read())
        self.observed_output = ""

    @staticmethod
    def _extract_input(dialogue_contents: str):
        # Find all tokens delimited by << and >> and return them
        # as a list along with the original contents with the << and >> removed
        inputs = re.findall(r'<<(.*?)>>', dialogue_contents)
        dialogue_contents = re.sub(r'<<(.*?)>>', r'\1', dialogue_contents)
        return inputs, dialogue_contents

    def _assert_output(self):
        # Pad the output with spaces so that the diff is easier to read
        def pad(s):
            return s + ' ' * (80 - len(s))

        try:
            assert pad(self.observed_output) == pad(self.expected_output)
        except AssertionError as err:
            edit_score = self.edit_dist(self.observed_output, self.expected_output)
            err._partial_credit = max(0.0, round(edit_score / len(self.expected_output) * 0.8, 2))
            raise

    def edit_dist(self, observed: str, expected: str) -> float:
        """
        Align seq1 against seq2 using Needleman-Wunsch
        Put seq1 on left (j) and seq2 on top (i)
        => matrix[i][j]
        """
        MATCH = 1
        SUB = -1
        INDEL = -1
        GAP = '-'

        def get_i_j(len_i, len_j):
            for ii in range(len_i):
                for jj in range(len_j):
                    yield ii, jj

        len1 = len(observed)
        len2 = len(expected)

        score_matrix = {}
        path_matrix = {}

        # Initialize base cases
        score_matrix[0, 0] = 0
        path_matrix[0, 0] = (-1, -1)

        for i in range(1, len2 + 1):
            score_matrix[i, 0] = score_matrix[i - 1, 0] + INDEL
            path_matrix[i, 0] = (i - 1, 0)

        for j in range(1, len1 + 1):
            score_matrix[0, j] = score_matrix[0, j - 1] + INDEL
            path_matrix[0, j] = (0, j - 1)

        # Fill in!
        ij = get_i_j(len2, len1)
        for i, j in ij:
            si = i
            i += 1  # adjust for extra row at beginning of matrix
            sj = j
            j += 1  # adjust for extra column at beginning of matrix
            # Which of the three paths is best?
            match = score_matrix[i - 1, j - 1] + (MATCH if observed[sj] == expected[si] else SUB)
            gap_i = score_matrix.get((i - 1, j), math.inf) + INDEL
            gap_j = score_matrix.get((i, j - 1), math.inf) + INDEL
            # Break ties using diagonal, left (gap in i), top (gap in j)
            if match >= gap_i and match >= gap_j:
                score = match
                path = (i - 1, j - 1)
            elif gap_i >= gap_j:
                score = gap_i
                path = (i - 1, j)
            else:
                score = gap_j
                path = (i, j - 1)

            score_matrix[i, j] = score
            path_matrix[i, j] = path

        # Extract path
        align_path = [(len2, len1)]
        while align_path[-1] != (0, 0):
            prev = align_path[-1]
            align_path.append(path_matrix[prev])
        align_path = list(reversed(align_path))

        # Interpret alignment (currently unused, but maybe handy?)
        align1 = ''
        align2 = ''
        a1 = 0
        a2 = 0
        for (pi, pj), (ci, cj) in zip(align_path[:-1], align_path[1:]):
            # Is the move a match, gap1, or gap2?
            di = ci - pi
            dj = cj - pj
            if di == 1 and dj == 1:  # match
                align1 += observed[a1]
                a1 += 1
                align2 += expected[a2]
                a2 += 1
            elif di == 1:  # gap1 -> took from seq2, but not seq1
                align1 += GAP
                align2 += expected[a2]
                a2 += 1
            else:  # gap2 -> took from seq1, but not seq2
                align1 += observed[a1]
                a1 += 1
                align2 += GAP

        return score_matrix[len2, len1]

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
    parser = argparse.ArgumentParser()
    parser.add_argument('dialog_file', help='Dialog file to write')
    parser.add_argument('python_script', help='Python script to run')
    parser.add_argument('script_args', nargs='*', help='Arguments to the python script (if any)')
    args = parser.parse_args()

    record_script(args.dialog_file, args.python_script, *args.script_args)
