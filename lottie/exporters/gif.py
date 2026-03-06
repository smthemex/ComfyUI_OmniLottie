import io
from PIL import Image
from PIL import features

from .cairo import export_png
from .base import exporter, io_progress
from ..parsers.baseporter import ExtraOption


def _png_gif_prepare(image):
    if image.mode not in ["RGBA", "RGBa"]:
        image = image.convert("RGBA")
    alpha = image.getchannel("A")
    image = image.convert("RGB").convert('P', palette=Image.ADAPTIVE, colors=255)
    mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
    image.paste(255, mask=mask)
    return image


def _log_frame(fmt, frame_no=None, end=None):
    if frame_no is None:
        io_progress().report_message("%s frame rendering completed" % (fmt))
    else:
        io_progress().report_progress("%s rendering frame" % fmt, frame_no, end)


@exporter("GIF", ["gif"], [
    ExtraOption("skip_frames", type=int, default=1, help="Only renderer 1 out of these many frames"),
])
def export_gif(animation, fp, dpi=96, skip_frames=1):
    """
    Gif export

    Note that it's a bit slow.
    """
    start = int(animation.in_point)
    end = int(animation.out_point)
    frames = []
    for i in range(start, end+1, skip_frames):
        _log_frame("GIF", i, end)
        file = io.BytesIO()
        export_png(animation, file, i, dpi)
        file.seek(0)
        frames.append(_png_gif_prepare(Image.open(file)))
    _log_frame("GIF")

    io_progress().report_message("GIF Writing to file...")
    duration = int(round(1000 / animation.frame_rate * skip_frames / 10)) * 10
    frames[0].save(
        fp,
        format='GIF',
        append_images=frames[1:],
        save_all=True,
        duration=duration,
        loop=0,
        transparency=255,
        disposal=2,
    )


@exporter("WebP", ["webp"], [
    ExtraOption("lossless", action="store_true", help="If present, use lossless compression"),
    ExtraOption("quality", type=int, default=80,
                help="Compression effort between 0 and 100\n" +
                     "for lossy 0 gives the smallest size\n" +
                     "for lossless 0 gives the largest file"),
    ExtraOption("method", type=int, default=0, help="Quality/speed trade-off (0=fast, 6=slower-better)"),
    ExtraOption("skip_frames", type=int, default=1, help="Only renderer 1 out of these many frames"),
])
def export_webp(animation, fp, dpi=96, lossless=False, quality=80, method=0, skip_frames=1):
    """
    Export WebP

    See https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp
    """
    if not features.check("webp_anim"):
        raise Exception("WebP animations not supported in this system")

    start = int(animation.in_point)
    end = int(animation.out_point)
    frames = []
    for i in range(start, end+1, skip_frames):
        _log_frame("WebP", i, end)
        file = io.BytesIO()
        export_png(animation, file, i, dpi)
        file.seek(0)
        frames.append(Image.open(file))

    _log_frame("WebP")

    io_progress().report_message("WebP Writing to file...")
    duration = int(round(1000 / animation.frame_rate * skip_frames))
    frames[0].save(
        fp,
        format='WebP',
        append_images=frames[1:],
        save_all=True,
        duration=duration,
        loop=0,
        background=(0, 0, 0, 0),
        lossless=lossless,
        quality=quality,
        method=method
    )


@exporter("TIFF", ["tiff"])
def export_tiff(animation, fp, dpi=96):
    """
    Export TIFF
    """
    start = int(animation.in_point)
    end = int(animation.out_point)
    frames = []
    for i in range(start, end+1):
        _log_frame("TIFF", i, end)
        file = io.BytesIO()
        export_png(animation, file, i, dpi)
        file.seek(0)
        frames.append(Image.open(file))
    _log_frame("TIFF")

    io_progress().report_message("TIFF Writing to file...")
    duration = int(round(1000 / animation.frame_rate))
    frames[0].save(
        fp,
        format='TIFF',
        append_images=frames[1:],
        save_all=True,
        duration=duration,
        loop=0,
        dpi=(dpi, dpi),
    )
