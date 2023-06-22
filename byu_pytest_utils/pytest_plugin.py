import pytest
import json

metadata = {}
test_group_stats = {}

MIN_LINES_DIFF = 3


def pytest_assertrepr_compare(config, op, left, right):
    if op == '==' \
            and isinstance(left, str) and len(left_lines := left.splitlines()) > MIN_LINES_DIFF \
            and isinstance(right, str) and len(right_lines := right.splitlines()) > MIN_LINES_DIFF:
        # Use custom side-by-side assertion diff
        # How wide?
        left_width = max((len(line) for line in left_lines))
        right_width = max((len(line) for line in right_lines))
        left_view_lines = [f"{line:<{left_width}}" for line in left_lines]
        right_view_lines = [f"{line:<{right_width}}" for line in right_lines]

        # Pad with empty lines
        while len(left_view_lines) < len(right_view_lines):
            left_view_lines.append(' ' * left_width)
        while len(right_view_lines) < len(left_view_lines):
            right_view_lines.append(' ' * right_width)

        # Join lines side by side
        diff_view = [
            'Observed (left) == Expected (right)',
            *(l + ' | ' + r for l, r in zip(left_view_lines, right_view_lines))
        ]
        return diff_view


def pytest_generate_tests(metafunc):
    if hasattr(metafunc.function, '_group_stats'):
        group_stats = metafunc.function._group_stats

        for group_name, stats in group_stats.items():
            stats['max_score'] *= getattr(metafunc.function, 'max_score', 0)
            stats['score'] *= getattr(metafunc.function, 'max_score', 0)
            test_name = f'{metafunc.function.__module__}.py::{metafunc.function.__name__}[{group_name}]'
            test_group_stats[test_name] = stats

        metafunc.parametrize('group_name', group_stats.keys())
    else:
        test_name = f'{metafunc.function.__module__}.py::{metafunc.function.__name__}'
        test_group_stats[test_name] = {
            'max_score': getattr(metafunc.function, 'max_score', 0)
        }


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):
    x = yield
    if item._obj not in metadata:
        metadata[item._obj] = {}
    metadata[item._obj]['max_score'] = getattr(item._obj, 'max_score', 0)
    metadata[item._obj]['visibility'] = getattr(
        item._obj, 'visibility', 'visible')
    x._result.metadata_key = item._obj


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    # Deprecated function - remove with CheckIO stuff
    outcome = yield
    excinfo = outcome.excinfo
    if excinfo is not None \
            and excinfo[0] is AssertionError \
            and hasattr(excinfo[1], '_partial_credit'):
        metadata[pyfuncitem._obj]['partial_credit'] = excinfo[1]._partial_credit


def pytest_terminal_summary(terminalreporter, exitstatus):
    json_results = {'tests': []}

    all_tests = []
    if 'passed' in terminalreporter.stats:
        all_tests = all_tests + terminalreporter.stats['passed']
    if 'failed' in terminalreporter.stats:
        all_tests = all_tests + terminalreporter.stats['failed']

    for s in all_tests:
        output = s.capstdout + '\n' + s.capstderr
        group_stats = test_group_stats[s.nodeid]

        max_score = group_stats['max_score']
        score = group_stats.get('score', max_score if s.passed else 0)

        output += s.longreprtext

        json_results["tests"].append(
            {
                'score': round(score, 4),
                'max_score': round(max_score, 4),
                'name': s.nodeid,
                'output': output,
                'visibility': 'visible',
            }
        )

    with open('results.json', 'w') as results:
        results.write(json.dumps(json_results, indent=4))
