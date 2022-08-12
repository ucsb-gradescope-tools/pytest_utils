# Gradescope Pytest Library

A package for producing Gradescope-compatible results.json files with Pytest tests.

This is a fork of [https://github.com/ucsb-gradescope-tools/pytest_utils](https://github.com/ucsb-gradescope-tools/pytest_utils).
Many thanks to UCSB for making this available!

We have converted the codebase to use poetry so we can add it to pypi.

## Usage

At the top of the file where you define your tests, put:

```
import byu_pytest_utils
from byu_pytest_utils.decorators import max_score, visibility, tags
```

Then annotate your tests using the provided decorators.

### max_score

To set the maximum score for a test:

```
@max_score(maximum)
def test_a():
```

Where `maximum` is a numeric value. Default value is 0.

### visibility

To set the visibility of a test:

```
@visibility(option)
def test_a():
```

Where `option` is 'visible', 'hidden', 'after\_due\_date', or 'after\_published.' Default value is 'visible.'

### tags

To add extra tags to a test:

```
@tags(tag_list)
def test_a():
```

Where `tag_list` is a list of strings. Default value is an empty list.

## Running Locally

To run locally:

```
> pip install byu_pytest_utils
```

Then, in the directory where your `test_assignment.py` lives:

```
> pytest
```

The results will be written to results.json.

## Example

The assignment is to create a file called `assignment.py` with a function `hello()` which returns "hello". The `test_assignment.py` file is:

```
import byu_pytest_utils
from byu_pytest_utils.decorators import max_score, visibility, tags
from assignment import *

@max_score(10)
def test_one(self):
    assert(hello() == "hello")
    
```

See also `test_example.py`
