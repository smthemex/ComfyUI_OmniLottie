from .base import LottieObject, LottieProp, LottieEnum
from .properties import Value, MultiDimensional
from .nvector import NVector
from .helpers import Transform


## @ingroup Lottie
## @ingroup LottieCheck
class MaskedPath(LottieObject):
    _props = [
        LottieProp("mask", "m", float),
        LottieProp("f", "f", Value),
        LottieProp("l", "l", Value),
        LottieProp("r", "r", float),
    ]

    def __init__(self):
        ## Type?
        self.mask = None
        ## First?
        self.f = None
        ## Last?
        self.l = None
        ## ??
        self.r = None


## @ingroup Lottie
## @ingroup LottieCheck
class TextAnimatorDataProperty(Transform):
    _props = [
        LottieProp("rx", "rx", Value),
        LottieProp("ry", "ry", Value),
        LottieProp("stroke_width", "sw", Value),
        LottieProp("stroke_color", "sc", MultiDimensional),
        LottieProp("fill_color", "fc", MultiDimensional),
        LottieProp("fh", "fh", Value),
        LottieProp("fs", "fs", Value),
        LottieProp("fb", "fb", Value),
        LottieProp("tracking", "t", Value),
        LottieProp("scale", "s", MultiDimensional),
    ]

    def __init__(self):
        super().__init__()
        ## Angle?
        self.rx = Value()
        ## Angle?
        self.ry = Value()
        ## Stroke width
        self.stroke_width = Value()
        ## Stroke color
        self.stroke_color = MultiDimensional()
        ## Fill color
        self.fill_color = MultiDimensional()
        self.fh = Value()
        ## 0-100?
        self.fs = Value()
        ## 0-100?
        self.fb = Value()
        ## Tracking
        self.tracking = Value()


## @ingroup Lottie
## @ingroup LottieCheck
class TextMoreOptions(LottieObject):
    _props = [
        LottieProp("alignment", "a", MultiDimensional),
        LottieProp("g", "g", float),
    ]

    def __init__(self):
        self.alignment = MultiDimensional(NVector(0, 0))
        self.g = None


## @ingroup Lottie
class TextJustify(LottieEnum):
    Left = 0
    Right = 1
    Center = 2


## @ingroup Lottie
class TextDocument(LottieObject):
    """!
    @see http://docs.aenhancers.com/other/textdocument/

    Note that for multi-line text, lines are separated by \\r
    """
    _props = [
        LottieProp("font_family", "f", str),
        LottieProp("color", "fc", NVector),
        LottieProp("font_size", "s", float),
        LottieProp("line_height", "lh", float),
        LottieProp("wrap_size", "sz", NVector),
        LottieProp("text", "t", str),
        LottieProp("justify", "j", TextJustify),
        # ls?
    ]

    def __init__(self, text="", font_size=10, color=None, font_family=""):
        self.font_family = font_family
        ## Text color
        self.color = color or NVector(0, 0, 0)
        ## Line height when wrapping
        self.line_height = None
        ## Text alignment
        self.justify = TextJustify.Left
        ## Size of the box containing the text
        self.wrap_size = None
        ## Text
        self.text = text
        ## Font Size
        self.font_size = font_size


## @ingroup Lottie
class TextDataKeyframe(LottieObject):
    _props = [
        LottieProp("start", "s", TextDocument),
        LottieProp("time", "t", float),
    ]

    def __init__(self, time=0, start=None):
        ## Start value of keyframe segment.
        self.start = start
        ## Start time of keyframe segment.
        self.time = time


## @ingroup Lottie
class TextData(LottieObject):
    _props = [
        LottieProp("keyframes", "k", TextDataKeyframe, True),
    ]

    def __init__(self):
        self.keyframes = []

    def get_value(self, time):
        for kf in self.keyframes:
            if kf.time >= time:
                return kf.start
        return None


## @ingroup Lottie
class TextAnimatorData(LottieObject):
    _props = [
        LottieProp("properties", "a", TextAnimatorDataProperty, True),
        LottieProp("data", "d", TextData, False),
        LottieProp("more_options", "m", TextMoreOptions, False),
        LottieProp("masked_path", "p", MaskedPath),
    ]

    def __init__(self):
        self.properties = []
        self.data = TextData()
        self.more_options = TextMoreOptions()
        self.masked_path = MaskedPath()

    def add_keyframe(self, time, item):
        self.data.keyframes.append(TextDataKeyframe(time, item))

    def get_value(self, time):
        return self.data.get_value(time)


## @ingroup Lottie
class FontPathOrigin(LottieEnum):
    Unknown = 0
    CssUrl = 1
    ScriptUrl = 2
    FontUrl = 3


## @ingroup Lottie
class Font(LottieObject):
    _props = [
        LottieProp("ascent", "ascent", float),
        LottieProp("font_family", "fFamily", str),
        LottieProp("name", "fName", str),
        LottieProp("font_style", "fStyle", str),
        LottieProp("path", "fPath", str),
        LottieProp("weight", "fWeight", str),
        LottieProp("origin", "origin", FontPathOrigin),
    ]

    def __init__(self, font_family="sans", font_style="Regular", name=None):
        self.ascent = None
        self.font_family = font_family
        self.font_style = font_style
        self.name = name or "%s-%s" % (font_family, font_style)
        self.path = None
        self.weight = None
        self.origin = None


## @ingroup Lottie
class FontList(LottieObject):
    _props = [
        LottieProp("list", "list", Font, True),
    ]

    def __init__(self):
        self.list = []

    def append(self, font):
        self.list.append(font)
