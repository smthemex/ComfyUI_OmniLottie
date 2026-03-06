from .base import importer
from ..parsers.tgs import parse_tgs


@importer("Lottie JSON / Telegram Sticker", ["json", "tgs"], slug="lottie")
def import_tgs(file, *a, **kw):
    return parse_tgs(file, *a, **kw)
