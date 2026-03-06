import sys
import json
import gzip
import codecs

from .base import exporter
from ..utils.file import open_file
from ..parsers.baseporter import ExtraOption
from .tgs_validator import TgsValidator


@exporter("Lottie JSON", ["json"], [], {"pretty"}, "lottie")
def export_lottie(animation, file, pretty=False):
    with open_file(file) as fp:
        kw = {}
        if pretty:
            kw = dict(indent=4)
        json.dump(animation.to_dict(), fp, **kw)


@exporter("Telegram Animated Sticker", ["tgs"], [
    ExtraOption("no_sanitize", help="Disable Sticker fit", action="store_false", dest="sanitize"),
    ExtraOption("no_validate", help="Disable feature validation", action="store_false", dest="validate"),
])
def export_tgs(animation, file, sanitize=False, validate=False):
    if sanitize:
        animation.tgs_sanitize()

    with gzip.open(file, "wb") as gzfile:
        lottie_dict = animation.to_dict()
        lottie_dict["tgs"] = 1
        json.dump(lottie_dict, codecs.getwriter('utf-8')(gzfile))

    if validate:
        validator = TgsValidator()
        validator(animation)
        validator.check_file_size(file)
        if validator.errors:
            sys.stdout.write("\n".join(map(str, validator.errors))+"\n")


class HtmlOutput:
    def __init__(self, animation, file):
        self.animation = animation
        self.file = file

    def style(self):
        self.file.write("""
    <style>
        #bodymovin { width: %spx; height: %spx; margin: auto;
            background-color: white;
            background-size: 64px 64px;
            background-image:
                linear-gradient(to right, rgba(0, 0, 0, .3) 50%%, transparent 50%%),
                linear-gradient(to bottom, rgba(0, 0, 0, .3) 50%%, transparent 50%%),
                linear-gradient(to bottom, white 50%%, transparent 50%%),
                linear-gradient(to right, transparent 50%%, rgba(0, 0, 0, .5) 50%%);
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/bodymovin/5.5.3/lottie.js"></script>
    """ % (self.animation.width, self.animation.height))

    def body_pre(self):
        self.file.write("""
<div id="bodymovin"></div>

<script>
    var animData = {
        container: document.getElementById('bodymovin'),
        renderer: 'svg',
        loop: true,
        autoplay: true,
        """)

    def body_embedded(self):
        self.file.write("animationData: ")
        export_lottie(self.animation, self.file, True)

    def body_post(self):
        self.file.write("""
    };
    var anim = bodymovin.loadAnimation(animData);
</script>""")

    def html_begin(self):
        self.file.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <style>
        html, body { width: 100%; height: 100%; margin: 0; }
        body { display: flex; }
    </style>""")
        self.style()
        self.file.write("</head><body>")

    def html_end(self):
        self.file.write("</body></html>")


@exporter("Lottie HTML", ["html", "htm"])
def export_embedded_html(animation, file):
    with open_file(file) as fp:
        out = HtmlOutput(animation, fp)
        out.html_begin()
        out.body_pre()
        out.body_embedded()
        out.body_post()
        out.html_end()


def export_linked_html(animation, file, path):
    with open_file(file) as fp:
        out = HtmlOutput(animation, fp)
        out.html_begin()
        out.body_pre()
        file.write("path: %r" % path)
        out.body_post()
        out.html_end()
