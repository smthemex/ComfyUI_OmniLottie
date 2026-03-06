import os
import subprocess
from . import objects, parsers, utils, exporters, nvector, importers
from .nvector import *
from .utils.color import Color

try:
    from .version import __version__
except ImportError:
    here = os.path.dirname(os.path.abspath(__file__))
    pipe = subprocess.Popen(
        ['git', 'describe', '--abbrev=0', '--tags'],
        cwd=here,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.PIPE
    )
    out, err = pipe.communicate()
    if pipe.returncode == 0:
        __version__ = out.strip()[1:].decode("ascii") + "+git"
    else:
        vfn = os.path.join(os.path.dirname(os.path.dirname(here)), "version")
        if os.path.exists(vfn):
            with open(vfn) as vf:
                __version__ = vf.read().strip() + "+src"
        else:
            __version__ = "unknown"

try:
    version_tuple = tuple(map(int, __version__.split("+")[0].split("."))) if __version__ != "unknown" else (0, 0, 0)
except ValueError:
    version_tuple = (0, 0, 0)
    __version__ = "unknown"


__all__ = ["objects", "parsers", "utils", "exporters", "nvector", "NVector", "Point", "Color", "importers"]
