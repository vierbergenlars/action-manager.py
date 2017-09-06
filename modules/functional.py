from functools import partial, reduce

def n_chars(n: int, s) -> str:
    """
    Takes the first n characters
    """
    return s[0:n]


first_char = partial(n_chars, 1)


def first_word(s: str) -> str:
    """
    Takes the first word
    """
    return s.split(' ')[0]


def drop_first_n_words(n: int, s: str) -> str:
    """
    Removes the first word
    """
    return ' '.join(s.split(' ')[n:])


drop_first_word = partial(drop_first_n_words, 1)


def drop_first_word_if_eq(drop_if: str, s: str) -> str:
    return drop_first_word(s) if drop_if == first_word(s) else s


def apply(*args: [callable], **k):
    fns = args[:-1]
    data = args[-1]
    for fn in fns:
        data = fn(data, **k)
        k = {}
    return data


def drop_first_if_eq(drop_if: str, s: str) -> str:
    return s[len(drop_if):] if s[0:len(drop_if)] == drop_if else s

def drop_until(until: str, s: str) -> str:
    return s[s.find(until):]

def drop_from(end: str, s: str) -> str:
    idx = s.find(end)
    return s[:idx] if idx >= 0 else s


def apply(x, y, **k):
    return y(x, **k)


def foldr(fns, data, **kwargs):
    return reduce(partial(apply, **kwargs), fns, data)


def drop_kwargs(x, *a, **k):
    return x(*a)
