import os
import re
import base64
import mimetypes
from io import BytesIO
from .base import LottieObject, LottieProp, PseudoBool, Index
from .layers import Layer
from .shapes import ShapeElement
from .composition import Composition


## @ingroup Lottie
class Asset(LottieObject):
    @classmethod
    def _load_get_class(cls, lottiedict):
        if "p" in lottiedict or "u" in lottiedict:
            return Image
        if "layers" in lottiedict:
            return Precomp


## @ingroup Lottie
class Image(Asset):
    """!
        External image

        @see http://docs.aenhancers.com/sources/filesource/
    """
    _props = [
        LottieProp("height", "h", float, False),
        LottieProp("width", "w", float, False),
        LottieProp("id", "id", str, False),
        LottieProp("image", "p", str, False),
        LottieProp("image_path", "u", str, False),
        LottieProp("is_embedded", "e", PseudoBool, False),
    ]

    @staticmethod
    def guess_mime(file):
        if isinstance(file, str):
            filename = file
        elif hasattr(file, "name"):
            filename = file.name
        else:
            return "application/octet-stream"
        return mimetypes.guess_type(filename)

    def __init__(self, id=""):
        ## Image Height
        self.height = 0
        ## Image Width
        self.width = 0
        ## Image ID
        self.id = id
        ## Image name
        self.image = ""
        ## Image path
        self.image_path = ""
        ## Image data is stored as a data: url
        self.is_embedded = False

    def load(self, file, format=None):
        """!
        @param file     Filename, file object, or PIL.Image.Image to load
        @param format   Format to store the image data as
        """
        from PIL import Image

        if not isinstance(file, Image.Image):
            image = Image.open(file)
        else:
            image = file

        self._id_from_file(file)

        self.image_path = ""
        if format is None:
            format = (image.format or "png").lower()
        self.width, self.height = image.size
        output = BytesIO()
        image.save(output, format=format)
        self.image = "data:image/%s;base64,%s" % (
            format,
            base64.b64encode(output.getvalue()).decode("ascii")
        )
        self.is_embedded = True
        return self

    def _id_from_file(self, file):
        if not self.id:
            if isinstance(file, str):
                self.id = os.path.basename(file)
            elif hasattr(file, "name"):
                self.id = os.path.basename(file.name)
            elif hasattr(file, "filename"):
                self.id = os.path.basename(file.filename)
            else:
                self.id = "image_%s" % id(self)

    @classmethod
    def embedded(cls, image, format=None):
        """!
        Create an object from an image file
        """
        lottie_image = cls()
        return lottie_image.load(image, format)

    @classmethod
    def linked(cls, filename):
        from PIL import Image
        image = Image.open(filename)
        lottie_image = cls()
        lottie_image._id_from_file(filename)
        lottie_image.image_path, lottie_image.image = os.path.split(filename)
        lottie_image.image_path += "/"
        lottie_image.width = image.width
        lottie_image.height = image.height
        return lottie_image

    def image_data(self):
        """
        Returns a tuple (format, data) with the contents of the image

        `format` is a string like "png", and `data` is just raw binary data.

        If it's impossible to fetch this info, returns (None, None)
        """
        if self.is_embedded:
            m = re.match("data:[^/]+/([^;,]+);base64,(.*)", self.image)
            if m:
                return m.group(1), base64.b64decode(m.group(2))
            return None, None
        path = self.image_path + self.image
        if os.path.isfile(path):
            with open(path, "rb") as imgfile:
                return os.path.splitext(path)[1][1:], imgfile.read()
        return None, None


## @ingroup Lottie
class CharacterData(LottieObject):
    """!
    Character shapes
    """
    _props = [
        LottieProp("shapes", "shapes", ShapeElement, True),
    ]

    def __init__(self):
        self.shapes = []


## @ingroup Lottie
class Chars(LottieObject):
    """!
    Defines character shapes to avoid loading system fonts
    """
    _props = [
        LottieProp("character", "ch", str, False),
        LottieProp("font_family", "fFamily", str, False),
        LottieProp("font_size", "size", float, False),
        LottieProp("font_style", "style", str, False),
        LottieProp("width", "w", float, False),
        LottieProp("data", "data", CharacterData, False),
    ]

    def __init__(self):
        ## Character Value
        self.character = ""
        ## Character Font Family
        self.font_family = ""
        ## Character Font Size
        self.font_size = 0
        ## Character Font Style
        self.font_style = "" # Regular
        ## Character Width
        self.width = 0
        ## Character Data
        self.data = CharacterData()

    @property
    def shapes(self):
        return self.data.shapes


## @ingroup Lottie
class Precomp(Asset, Composition):
    _props = [
        LottieProp("id", "id", str, False),
    ]

    def __init__(self, id="", animation=None):
        super().__init__()
        ## Precomp ID
        self.id = id
        self.animation = animation
        if animation:
            self.animation.assets.append(self)

    def _on_prepare_layer(self, layer):
        if self.animation:
            self.animation.prepare_layer(layer)

    def set_timing(self, outpoint, inpoint=0, override=True):
        for layer in self.layers:
            if override or layer.in_point is None:
                layer.in_point = inpoint
            if override or layer.out_point is None:
                layer.out_point = outpoint
