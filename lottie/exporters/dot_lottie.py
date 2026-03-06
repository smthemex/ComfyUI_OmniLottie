import json
import string
import zipfile

from .base import exporter
from ..parsers.baseporter import ExtraOption
from ..parsers.tgs import parse_tgs
from lottie import __version__
from ..objects import assets


@exporter("dotLottie Archive", ["lottie"], [
    ExtraOption("id", help="ID of the animation", default=None),
    ExtraOption("append", help="Append animation to existing archive", action="store_true"),
    ExtraOption("revision", help="File revision", type=int, default=None),
    ExtraOption("author", help="File author", default=None),
    ExtraOption("speed", help="Playback speed", type=float, default=1),
    ExtraOption("theme_color", help="Theme color", type=str, default="#ffffff"),
    ExtraOption("no_loop", help="Disable Looping", action="store_false", dest="loop"),
    ExtraOption("no_pack", help="Don't auto-pack images", action="store_false", dest="pack_images"),
], slug="dotlottie")
def export_dotlottie(animation, file, id=None, append=False, revision=None, author=None,
                     speed=1.0, theme_color="#ffffff", loop=True, pack_images=True):

    files = {}

    if append:
        with zipfile.ZipFile(file, "r") as zf:
            with zf.open("manifest.json") as manifest:
                meta = json.load(manifest)

            for name in zf.namelist():
                if name != "manifest.json":
                    files[name] = zf.read(name)
    else:
        meta = {
            "generator": "Python Lottie " + __version__,
            "version": 1.0,
            "revision": 1,
            "author": "",
            "animations": [],
            "custom": {}
        }

    if revision is not None:
        meta["revision"] = revision

    if author is not None:
        meta["author"] = author

    if id is None:
        if animation.name:
            idok = string.ascii_letters + string.digits + "_-"
            id = "".join(filter(lambda x: x in idok, animation.name.replace(" ", "_")))
        if not id:
            id = "animation_%s" % len(meta["animations"])

    meta["animations"].append({
        "id": id,
        "speed": speed,
        "themeColor": theme_color,
        "loop": loop,
    })

    if pack_images and animation.assets:
        animation = animation.clone()
        image_no = 0
        for asset in animation.assets:
            if isinstance(asset, assets.Image):
                ext, data = asset.image_data()
                if not ext:
                    continue
                pathname = "images/"
                while True:
                    basename = "image_%s.%s" % (image_no, ext)
                    image_no += 1
                    if pathname+basename not in files:
                        break
                files[pathname+basename] = data
                asset.image_path = pathname
                asset.image = basename
                asset.is_embedded = False

    files["manifest.json"] = json.dumps(meta)
    files["animations/%s.json" % id] = json.dumps(animation.to_dict())

    with zipfile.ZipFile(file, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
