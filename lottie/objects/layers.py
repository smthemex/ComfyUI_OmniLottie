import warnings
from .base import LottieObject, LottieProp, PseudoBool, LottieEnum
from .effects import Effect
from .helpers import Transform, Mask
from .shapes import ShapeElement
from .text import TextAnimatorData
from .properties import Value


## @ingroup Lottie
class BlendMode(LottieEnum):
    Normal = 0
    Multiply = 1
    Screen = 2
    Overlay = 3
    Darken = 4
    Lighten = 5
    ColorDodge = 6
    ColorBurn = 7
    HardLight = 8
    SoftLight = 9
    Difference = 10
    Exclusion = 11
    Hue = 12
    Saturation = 13
    Color = 14
    Luminosity = 15


## @ingroup Lottie
## @todo SVG masks
class MatteMode(LottieEnum):
    Normal = 0
    Alpha = 1
    InvertedAlpha = 2
    Luma = 3
    InvertedLuma = 4


## @ingroup Lottie
class Layer(LottieObject):
    _props = [
        LottieProp("threedimensional", "ddd", PseudoBool, False),
        LottieProp("hidden", "hd", bool, False),
        LottieProp("type", "ty", int, False),
        LottieProp("name", "nm", str, False),
        LottieProp("parent_index", "parent", int, False),

        LottieProp("stretch", "sr", float, False),
        LottieProp("transform", "ks", Transform, False),
        LottieProp("auto_orient", "ao", PseudoBool, False),

        LottieProp("in_point", "ip", float, False),
        LottieProp("out_point", "op", float, False),
        LottieProp("start_time", "st", float, False),
        LottieProp("blend_mode", "bm", BlendMode, False),

        LottieProp("matte_mode", "tt", MatteMode, False),
        LottieProp("index", "ind", int, False),
        #LottieProp("css_class", "cl", str, False),
        LottieProp("layer_html_id", "ln", str, False),
        LottieProp("has_masks", "hasMask", bool, False),
        LottieProp("masks", "masksProperties", Mask, True),
        LottieProp("effects", "ef", Effect, True),
        LottieProp("matte_target", "td", int, False),
    ]
    ## %Layer type.
    ## @see https://github.com/bodymovin/bodymovin-extension/blob/master/bundle/jsx/enums/layerTypes.jsx
    type = None
    _classses = {}

    @property
    def has_masks(self):
        """!
        Whether the layer has some masks applied
        """
        return bool(self.masks) if getattr(self, "masks") is not None else None

    def __init__(self):
        ## Transform properties
        self.transform = Transform()
        ## Auto-Orient along path AE property.
        self.auto_orient = False
        ## 3d layer flag
        self.threedimensional = False
        ## Hidden layer
        self.hidden = None
        ## Layer index in AE. Used for parenting and expressions.
        self.index = None

        """
        # Parsed layer name used as html class on SVG/HTML renderer
        #self.css_class = ""
        # Parsed layer name used as html id on SVG/HTML renderer
        #self.layer_html_id = ""
        """
        ## In Point of layer. Sets the initial frame of the layer.
        self.in_point = None
        ## Out Point of layer. Sets the final frame of the layer.
        self.out_point = None
        ## Start Time of layer. Sets the start time of the layer.
        self.start_time = 0
        ## After Effects Layer Name. Used for expressions.
        self.name = None
        ## List of Effects
        self.effects = None
        ## Layer Time Stretching
        self.stretch = 1
        ## Layer Parent. Uses ind of parent.
        self.parent_index = None
        ## List of Masks
        self.masks = None
        ## Blend Mode
        self.blend_mode = BlendMode.Normal
        ## Matte mode, the layer will inherit the transparency from the layer above
        self.matte_mode = None
        self.matte_target = None
        ## Composition owning the layer, set by add_layer
        self.composition = None

    def add_child(self, layer):
        if not self.composition or self.index is None:
            raise Exception("Must set composition / index first")
        self._child_inout_auto(layer)
        self.composition.add_layer(layer)
        layer.parent_index = self.index
        return layer

    def _child_inout_auto(self, layer):
        if layer.in_point is None:
            layer.in_point = self.in_point
        if layer.out_point is None:
            layer.out_point = self.out_point

    @property
    def parent(self):
        if self.parent_index is None:
            return None
        return self.composition.layer(self.parent_index)

    @parent.setter
    def parent(self, layer):
        if layer is None:
            self.parent_index = None
        else:
            self.parent_index = layer.index
            layer._child_inout_auto(self)

    @property
    def children(self):
        for layer in self.composition.layers:
            if layer.parent_index == self.index:
                yield layer

    @classmethod
    def _load_get_class(cls, lottiedict):
        if not Layer._classses:
            Layer._classses = {
                sc.type: sc
                for sc in Layer.__subclasses__()
            }
        type_id = lottiedict["ty"]
        if type_id not in Layer._classses:
            warnings.warn("Unknown layer type: %s" % type_id)
            return Layer
        return Layer._classses[type_id]

    def __repr__(self):
        return "<%s %s %s>" % (type(self).__name__, self.index, self.name)

    def __str__(self):
        return "%s %s" % (
            self.name or super().__str__(),
            self.index if self.index is not None else ""
        )

    def remove(self):
        """!
        @brief Removes this layer from the componsitin
        """
        self.composition.remove_layer(self)


## @ingroup Lottie
class NullLayer(Layer):
    """!
    Layer with no data, useful to group layers together
    """
    ## %Layer type.
    type = 3

    def __init__(self):
        Layer.__init__(self)


## @ingroup Lottie
class TextLayer(Layer):
    _props = [
        LottieProp("data", "t", TextAnimatorData, False),
    ]
    ## %Layer type.
    type = 5

    def __init__(self):
        Layer.__init__(self)
        ## Text Data
        self.data = TextAnimatorData()


## @ingroup Lottie
class ShapeLayer(Layer):
    """!
    Layer containing ShapeElement objects
    """
    _props = [
        LottieProp("shapes", "shapes", ShapeElement, True),
    ]
    ## %Layer type.
    type = 4

    def __init__(self):
        Layer.__init__(self)
        ## Shape list of items
        self.shapes = [] # ShapeElement

    def add_shape(self, shape):
        self.shapes.append(shape)
        return shape

    def insert_shape(self, index, shape):
        self.shapes.insert(index, shape)
        return shape


## @ingroup Lottie
## @todo SIF I/O
class ImageLayer(Layer):
    _props = [
        LottieProp("image_id", "refId", str, False),
    ]
    ## %Layer type.
    type = 2

    def __init__(self, image_id=""):
        Layer.__init__(self)
        ## id pointing to the source image defined on 'assets' object
        self.image_id = image_id


## @ingroup Lottie
class PreCompLayer(Layer):
    _props = [
        LottieProp("reference_id", "refId", str, False),
        LottieProp("time_remapping", "tm", Value, False),
        LottieProp("width", "w", int, False),
        LottieProp("height", "h", int, False),
    ]
    ## %Layer type.
    type = 0

    def __init__(self, reference_id=""):
        Layer.__init__(self)
        ## id pointing to the source composition defined on 'assets' object
        self.reference_id = reference_id
        ## Comp's Time remapping
        self.time_remapping = None
        ## Width
        self.width = 512
        ## Height
        self.height = 512


## @ingroup Lottie
class SolidColorLayer(Layer):
    """!
    Layer with a solid color rectangle
    """
    _props = [
        LottieProp("color", "sc", str, False),
        LottieProp("height", "sh", float, False),
        LottieProp("width", "sw", float, False),
    ]
    ## %Layer type.
    type = 1

    def __init__(self, color="", width=512, height=512):
        Layer.__init__(self)
        ## Color of the layer as a @c \#rrggbb hex
        # @todo Convert NVector to string
        self.color = color
        ## Height of the layer.
        self.height = height
        ## Width of the layer.
        self.width = width
