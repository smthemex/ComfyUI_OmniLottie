from .base import importer
from ..parsers.baseporter import ExtraOption
from ..parsers.svg import parse_svg_file
from ..parsers.tgs import open_maybe_gzipped


@importer("SVG", ["svg", "svgz"], [
    ExtraOption(
        "layer_frames", type=int, default=0,
        help="If greater than 0, treats every layer in the SVG as a different animation frame,\n"
        "greater values increase the time each frames lasts for."),
    ExtraOption("n_frames", type=int, default=60),
    ExtraOption("framerate", type=int, default=60),
])
def import_svg(file, *a, **kw):
    return open_maybe_gzipped(file, lambda svgfile: parse_svg_file(svgfile, *a, **kw))
