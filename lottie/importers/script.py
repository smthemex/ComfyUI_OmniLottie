import json
import tempfile
import subprocess
from .base import importer
from ..objects import Animation


@importer("Python script", ["py"])
def import_python_script(file, *a, **kw):

    out = subprocess.check_output(["python", file, "--version"])
    if b"python-lottie script" not in out:
        raise Exception("Not a valid script")

    data = subprocess.check_output(["python", file, "--path", "", "--name", "-", "--format", "json"])
    return Animation.load(json.loads(data))
