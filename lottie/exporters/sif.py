
from .base import exporter
from ..parsers.sif.builder import to_sif
from ..utils.file import open_file


@exporter("Synfig", ["sif"], [], {"pretty"})
def export_sif(animation, file, pretty=True):
    with open_file(file) as fp:
        dom = to_sif(animation).to_xml()
        dom.writexml(fp, "", "  " if pretty else "", "\n" if pretty else "")
