import math
import re
import runpy
import sys
import traceback
from functools import wraps

from byu_pytest_utils.edit_dist import edit_dist


def dialog(dialog_file, script, *script_args):
    checker = DialogChecker(dialog_file, echo_output=True)
    try:
        group_stats = checker.run_script(script, *script_args)

    except Exception as ex:
        group_stats = {
                'group_name': 'load-tests',
                'expected': '',
                'observed': traceback.format_exc(),
                'score': 0,
                'max_score': 1,
                'passed': False,
            }

    def decorator(func):
        # func should have empty (pass) body
        @wraps(func)
        def new_func(group_name):
            group_stat = group_stats[group_name]
            if not group_stat['passed']:
                assert group_stat['observed'] == group_stat['expected']

        new_func._group_stats = group_stats
        return new_func

    return decorator


class DialogChecker:
    DEFAULT_GROUP = '.'
    DEFAULT_GROUP_NAME = 'everything-else'
    MAX_PARTIAL_CREDIT = 1
    GAP = '~'

    def __init__(self, dialog_file, echo_output):
        self.echo_output = echo_output

        with open(dialog_file) as file:
            text = file.read()
            self.inputs, no_inputs = self._extract_input(text)
            self.group_weights, self.group_names, self.group_sequence, self.expected_output = \
                self._extract_groups(no_inputs)
        self.observed_output = ""

    @staticmethod
    def _extract_input(dialogue_contents: str):
        # Find all tokens delimited by << and >> and return them
        # as a list along with the original contents with the << and >> removed
        inputs = re.findall(r'<<(.*?)>>', dialogue_contents)
        dialogue_contents = re.sub(r'<<(.*?)>>', r'\1', dialogue_contents)
        return inputs, dialogue_contents

    @staticmethod
    def _extract_groups(dialog_contents: str):
        # blah blah [[foo;name;10]] blah blah

        group_weights = {DialogChecker.DEFAULT_GROUP: 0}
        group_names = {DialogChecker.DEFAULT_GROUP: DialogChecker.DEFAULT_GROUP_NAME}

        group_sequence = ''

        # Iterate through the dialog contents
        # Characters not in a group are assigned to weight group 'a'
        # Each weight group is assigned the next letter of the alphabet
        # A group starts with [[ and ends with ]]
        # The semicolon separates the group text from the weight
        # All text in a group is assigned to the same weight group
        # e.g.
        # quux [[foo;test-foo;30]] bar [[baz;test-baz;20]] quux
        # produces groups: aaaaabbbaaaacccaaaa
        # and group_weights: {'-': 40, 'b': 30, 'c': 20}

        i = 0
        while i < len(dialog_contents):
            if dialog_contents[i:i + 2] == '``':
                # Start of a group
                group_symbol = chr(ord('a') - 1 + len(group_weights))
                group_match = re.search(r'``(.*?);(.+?);(\d+?)``', dialog_contents[i:], flags=re.DOTALL)
                group_text = group_match.group(1)
                group_name = group_match.group(2)
                group_names[group_symbol] = group_name
                group_weights[group_symbol] = int(group_match.group(3))
                group_sequence += group_symbol * len(group_text)
                i += group_match.end()
            else:
                # Not in a group
                group_sequence += DialogChecker.DEFAULT_GROUP
                i += 1
        total = sum(group_weights.values())
        if total > 100:
            raise Exception('Group weights must add up to 100 or less')
        group_weights[DialogChecker.DEFAULT_GROUP] = 100 - total

        # Then remove the groups from the dialog contents
        dialog_contents = re.sub(r'``(.*?);(.+?);(\d+?)``', r'\1', dialog_contents, flags=re.DOTALL)

        return group_weights, group_names, group_sequence, dialog_contents

    def _score_output(self):
        _, obs, exp = edit_dist(
            self.observed_output,
            self.expected_output,
            GAP=DialogChecker.GAP
        )

        # insert gaps (i.e. DEFAULT_GROUP) into self.groups to match exp
        # then iterate over obs, exp, and groups
        # to compute rate of matches per group
        # (a gap in obs counts should use the prior group)
        # and return the score for each group
        # e.g. if groups is '---bbbcccc'
        # and group_weights is {'-': 50, 'b': 20, 'c': 30}
        # and exp is 'foobar~bazz'
        # and obs is 'boobarflaz~'
        # then groups should become '---bbbbcccc'

        if len(exp) - exp.count(DialogChecker.GAP) != len(self.group_sequence):
            raise Exception('Too many gaps in expected output')

        group_ids = ''
        i = 0
        g = 0
        while i < len(exp):
            if exp[i] == DialogChecker.GAP:
                group_ids += group_ids[-1] if group_ids else DialogChecker.DEFAULT_GROUP
                i += 1
            else:
                group_ids += self.group_sequence[g]
                g += 1
                i += 1
        assert len(group_ids) == len(exp)

        # Compute group scores
        group_counts = {}
        group_matches = {}
        group_obs = {}
        group_exp = {}
        for obs_c, exp_c, group_id in zip(obs, exp, group_ids):
            if obs_c == exp_c:
                group_matches[group_id] = group_matches.get(group_id, 0) + 1
            group_counts[group_id] = group_counts.get(group_id, 0) + 1
            group_obs[group_id] = group_obs.get(group_id, '') + obs_c
            group_exp[group_id] = group_exp.get(group_id, '') + exp_c

        # Fix default group obs/exp
        # Use the full output, and pad with spaces to 80 chars
        def pad(text):
            return text + ' ' * (80 - len(text))

        group_obs[DialogChecker.DEFAULT_GROUP] = pad(obs.replace(DialogChecker.GAP, ''))
        group_exp[DialogChecker.DEFAULT_GROUP] = pad(exp.replace(DialogChecker.GAP, ''))

        group_stats = {}
        for group_id, group_name in self.group_names.items():
            group_max = self.group_weights[group_id] / 100
            group_stats[group_name] = {
                'group_name': group_name,
                'expected': group_exp[group_id].replace(DialogChecker.GAP, ''),
                'observed': group_obs[group_id].replace(DialogChecker.GAP, ''),
                'score': group_matches.get(group_id, 0) / group_counts[group_id] * group_max,
                'max_score': group_max,
                'passed': group_matches.get(group_id, -1) == group_counts[group_id],
            }

        return group_stats

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
            runpy.run_path(script_name, _globals, module)

        except Exception as ex:
            # get stack trace as string
            self._consume_output(f'\nException: {ex}\n')
            self._consume_output(traceback.format_exc())

        # Final assertion of observed and expected output
        group_stats = self._score_output()

        return group_stats
