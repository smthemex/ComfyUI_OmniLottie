import io
import os

import cv2
import numpy
from PIL import Image

from .cairo import export_png
from .gif import _log_frame
from .base import exporter
from ..parsers.baseporter import ExtraOption


## @see http://www.fourcc.org/codecs.php
formats4cc = {
    "avi": cv2.VideoWriter_fourcc(*"XVID"),
    "mp4": cv2.VideoWriter_fourcc(*'MP4V'),
    #"mp4": cv2.VideoWriter_fourcc(*'X264'),
    "webm": cv2.VideoWriter_fourcc(*'VP80'),
}


@exporter("Video", list(formats4cc.keys()), [
    ExtraOption("format", default=None, help="Specific video format", choices=list(formats4cc.keys())),
], [], "video")
def export_video(animation, fp, format=None):
    start = int(animation.in_point)
    end = int(animation.out_point)
    if format is None:
        fn = fp if isinstance(fp, str) else fp.name
        format = os.path.splitext(fn)[1][1:]
    fmt = formats4cc[format]
    video = cv2.VideoWriter(fp, fmt, animation.frame_rate, (animation.width, animation.height))

    for i in range(start, end+1):
        _log_frame(format, i, end)
        file = io.BytesIO()
        export_png(animation, file, i)
        file.seek(0)
        video.write(cv2.cvtColor(numpy.array(Image.open(file)), cv2.COLOR_RGB2BGR))

    _log_frame(format)
    video.release()
