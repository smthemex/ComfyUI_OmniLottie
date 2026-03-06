from .base import LottieObject, LottieProp, PseudoBool, Index
from .layers import Layer
from .assets import Asset, Chars, Precomp
from .text import FontList
from .composition import Composition

##\defgroup Lottie Lottie
#
# Objects of the lottie file structure.

## \defgroup LottieCheck Lottie (to check)
#
# Lottie objects that have not been tested


## @ingroup Lottie
class Animation(Composition):
    """!
    Top level object, describing the animation

    @see http://docs.aenhancers.com/items/compitem/
    """
    _props = [
        LottieProp("version", "v", str, False),
        LottieProp("frame_rate", "fr", float, False),
        LottieProp("in_point", "ip", float, False),
        LottieProp("out_point", "op", float, False),
        LottieProp("width", "w", int, False),
        LottieProp("height", "h", int, False),
        LottieProp("name", "nm", str, False),
        LottieProp("threedimensional", "ddd", PseudoBool, False),
        LottieProp("assets", "assets", Asset, True),
        #LottieProp("comps", "comps", Animation, True),
        LottieProp("fonts", "fonts", FontList),
        LottieProp("chars", "chars", Chars, True),
        #LottieProp("markers", "markers", Marker, True),
        #LottieProp("motion_blur", "mb", MotionBlur, False),
    ]
    _version = "5.5.2"

    def __init__(self, n_frames=60, framerate=60):
        super().__init__()
        ## The time when the composition work area begins, in frames.
        self.in_point = 0
        ## The time when the composition work area ends.
        ## Sets the final Frame of the animation
        self.out_point = n_frames
        ## Frames per second
        self.frame_rate = framerate
        ## Composition Width
        self.width = 512
        ## Composition has 3-D layers
        self.threedimensional = False
        ## Composition Height
        self.height = 512
        ## Bodymovin Version
        self.version = self._version
        ## Composition name
        self.name = None
        ## source items that can be used in multiple places. Comps and Images for now.
        self.assets = [] # Image, Precomp
        ## source chars for text layers
        self.chars = None
        ## Available fonts
        self.fonts = None

    def precomp(self, name):
        for ass in self.assets:
            if isinstance(ass, Precomp) and ass.id == name:
                return ass
        return None

    def _on_prepare_layer(self, layer):
        if layer.in_point is None:
            layer.in_point = self.in_point
        if layer.out_point is None:
            layer.out_point = self.out_point

    def tgs_sanitize(self):
        """!
        Cleans up some things to ensure it works as a telegram sticker
        """
        if self.width != 512 or self.height != 512:
            scale = min(512/self.width, 512/self.height)
            self.width = self.height = 512

            for layer in self.layers:
                if layer.parent_index:
                    continue

                if layer.transform.scale.animated:
                    for kf in layer.transform.scale.keyframes:
                        if kf.start is not None:
                            kf.start *= scale
                        if kf.end is not None:
                            kf.end *= scale
                else:
                    layer.transform.scale.value *= scale

                if layer.transform.position.animated:
                    for kf in layer.transform.position.keyframes:
                        if kf.start is not None:
                            kf.start *= scale
                        if kf.end is not None:
                            kf.end *= scale
                else:
                    layer.transform.position.value *= scale

        if self.frame_rate < 45:
            self.frame_rate = 30
        else:
            self.frame_rate = 60

    def _fixup(self):
        super()._fixup()
        if self.assets:
            for ass in self.assets:
                if isinstance(ass, Precomp):
                    ass.animation = self
                    ass._fixup()

    def __str__(self):
        return self.name or super().__str__()
