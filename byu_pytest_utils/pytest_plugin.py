import pytest
import json

metadata = {}


# @pytest.mark.hookwrapper
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):
    x = yield
    if item._obj not in metadata:
        metadata[item._obj] = {}
    metadata[item._obj]['max_score'] = getattr(item._obj, 'max_score', 0)
    metadata[item._obj]['visibility'] = getattr(item._obj, 'visibility', 'visible')
    x._result.metadata_key = item._obj
    # x._result.visibility = getattr(item._obj, 'visibility', 'visible')


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem):
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
        meta = metadata[s.metadata_key]
        max_score = meta['max_score']

        score = max_score

        if 'partial_credit' in meta:
            score = max_score * meta['partial_credit']
            output += s.longreprtext

        elif s.outcome == 'failed':
            score = 0
            output += s.longreprtext

        json_results["tests"].append(
            {
                'score': score,
                'max_score': max_score,
                'name': s.nodeid,
                'output': output,
                'visibility': meta['visibility']
            }
        )

    with open('results.json', 'w') as results:
        results.write(json.dumps(json_results, indent=4))
