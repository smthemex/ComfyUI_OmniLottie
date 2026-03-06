from .base import importer
from ..parsers.sif import parse_sif_file


@importer("Synfig", ["sif", "sifz"])
def import_sif(file, *a, **kw):
    return parse_sif_file(file, *a, **kw)
