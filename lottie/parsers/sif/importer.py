from ..tgs import open_maybe_gzipped


def parse_sif_file(file):
    from .converter import convert
    from . import api
    return convert(open_maybe_gzipped(file, api.Canvas.from_xml_file))
