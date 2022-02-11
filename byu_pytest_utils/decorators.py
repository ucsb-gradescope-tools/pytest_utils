def max_score(maximum):
    """
    Decorator for setting the max score of a test

    :param maximum: the maximum score that can be earned
    """
    def wrapper(f):
        f.max_score = maximum
        return f
    return wrapper


def visibility(option):
    """
    Optional decorator for setting the visibility of a test

    :param option: 'visible', 'hidden', 'after_due_date', 'after_published'
    """
    def wrapper(f):
        f.visibility = option
        return f
    return wrapper


def tags(tag_list):
    """
    Optional decorator for adding extra tags to a test

    :param tag_list: a list of strings
    """
    def wrapper(f):
        f.tags = tag_list
        return f
    return wrapper
