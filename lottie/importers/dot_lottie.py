import json
import zipfile

from .base import importer
from ..parsers.baseporter import ExtraOption
from ..parsers.tgs import parse_tgs
from ..objects import Animation, assets


@importer("dotLottie Archive", ["lottie"], [
    ExtraOption("id", help="ID of the animation to extract", default=None)
], slug="dotlottie")
def import_dotlottie(file, id=None):
    with zipfile.ZipFile(file) as zf:
        with zf.open("manifest.json") as manifest:
            meta = json.load(manifest)

        if id is None:
            id = meta["animations"][0]["id"]

        info = zf.getinfo("animations/%s.json" % id)

        with zf.open(info) as animfile:
            an = Animation.load(json.load(animfile))
            if an.assets:
                for asset in an.assets:
                    if isinstance(asset, assets.Image) and not asset.is_embedded:
                        fname = asset.image_path + asset.image
                        if fname in zf.namelist():
                            with zf.open(fname) as imgfile:
                                asset.load(imgfile)
            return an
