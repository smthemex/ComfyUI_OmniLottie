import cairosvg
import io

from .base import exporter
from .svg import export_svg


def _export_cairo(func, animation, fp, frame, dpi):
    intermediate = io.StringIO()
    export_svg(animation, intermediate, frame)
    intermediate.seek(0)
    func(file_obj=intermediate, write_to=fp, dpi=dpi)


@exporter("PNG", ["png"], [], {"frame"})
def export_png(animation, fp, frame=0, dpi=96):
    _export_cairo(cairosvg.svg2png, animation, fp, frame, dpi)


@exporter("PDF", ["pdf"], [], {"frame"})
def export_pdf(animation, fp, frame=0, dpi=96):
    _export_cairo(cairosvg.svg2pdf, animation, fp, frame, dpi)


@exporter("PostScript", ["ps"], [], {"frame"})
def export_ps(animation, fp, frame=0, dpi=96):
    _export_cairo(cairosvg.svg2ps, animation, fp, frame, dpi)
