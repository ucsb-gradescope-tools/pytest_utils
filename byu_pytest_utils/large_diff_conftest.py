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
