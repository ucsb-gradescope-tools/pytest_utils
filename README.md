# Gradescope Pytest Library

A package for producing Gradescope-compatible results.json files with Pytest tests.

## Usage

At the top of the file where you define your tests, put:

```
import pytest_utils
from pytest_utils.decorators import max_score, visibility, tags
```

Then annotate your tests using the provided decorators.

### max_score

To set the maximum score for a test:

```
@max_score(value)
def test_a():
```

Where `value` is a numeric value. Default value is 0.

### visibility

To set the visibility of a test:

```
@visibility(value)
def test_a():
```

Where `value` is 'visible', 'hidden', 'after\_due\_date', or 'after\_published.' Default value is 'visible.'

### tags

To add extra tags to a test:

```
@tags(value)
def test_a():
```

Where `value` is a string array. Default value is an empty array.

## Running Locally

To run locally:

```
> git clone https://github.com/ucsb-gradescope-tools/pytest_utils.git
> cd pytest_utils
> pip3 install -e .
```

Then, in the directory where your `test_assignment.py` lives:

```
> pytest
```

The results will be written to results.json.

## Example

The assignment is to create a file called `assignment.py` with a function `hello()` which returns "hello". The `test_assignment.py` file is:

```
import pytest_utils
from pytest_utils.decorators import max_score, visibility, tags
from assignment import *

class TestAssignment(object):
    @max_score(10)
    def test_one(self):
        assert(hello() == "hello")
```
