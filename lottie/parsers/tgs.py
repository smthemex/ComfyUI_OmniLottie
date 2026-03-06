import io
import json
import gzip
from ..objects import Animation


def parse_tgs_json(file):
    """!
    Reads both tgs and lottie files, returns the json structure
    """
    return open_maybe_gzipped(file, json.load)


def open_maybe_gzipped(file, on_open):
    if isinstance(file, str):
        with open(file, "r") as fileobj:
            return open_maybe_gzipped(fileobj, on_open)

    if isinstance(file, io.TextIOBase):
        binfile = file.buffer
    else:
        binfile = file

    mn = binfile.read(2)
    binfile.seek(0)
    if mn == b'\x1f\x8b': # gzip magic number
        final_file = gzip.open(binfile, "rb")
    elif isinstance(file, io.TextIOBase):
        final_file = file
    else:
        final_file = io.TextIOWrapper(file)

    return on_open(final_file)


def parse_tgs(filename):
    """!
    Reads both tgs and lottie files
    """
    lottie = parse_tgs_json(filename)
    return Animation.load(lottie)
