from contextlib import contextmanager


@contextmanager
def open_file(file_or_name, mode="w"):
    if isinstance(file_or_name, str):
        obj = open(file_or_name, mode)
        try:
            yield obj
        finally:
            obj.close()
    else:
        yield file_or_name
