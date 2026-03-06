import math
from .base import LottieObject, LottieProp, LottieEnum
from .properties import MultiDimensional, Value, NVector, ShapeProperty, PositionValue


## @ingroup Lottie
class Transform(LottieObject):
    """!
    Layer transform
    """
    _props = [
        LottieProp("anchor_point", "a", MultiDimensional, False),
        LottieProp("position", "p", PositionValue, False),
        LottieProp("scale", "s", MultiDimensional, False),
        LottieProp("rotation", "r", Value, False),
        LottieProp("opacity", "o", Value, False),
        #LottieProp("position_x", "px", Value, False),
        #LottieProp("position_y", "py", Value, False),
        #LottieProp("position_z", "pz", Value, False),
        LottieProp("skew", "sk", Value, False),
        LottieProp("skew_axis", "sa", Value, False),
    ]

    def __init__(self):
        ## Transform Anchor Point
        self.anchor_point = MultiDimensional(NVector(0, 0))
        ## Transform Position
        self.position = PositionValue(NVector(0, 0))
        ## Transform Scale
        self.scale = MultiDimensional(NVector(100, 100))
        ## Transform Rotation
        self.rotation = Value(0)
        ## Transform Opacity
        self.opacity = Value(100)

        """
        # Transform Position X
        #self.position_x = Value()
        ## Transform Position Y
        #self.position_y = Value()
        ## Transform Position Z
        #self.position_z = Value()
        """

        ## Transform Skew
        self.skew = Value(0)
        ## Transform Skew Axis.
        ## An angle, if 0 skews on the X axis, if 90 skews on the Y axis
        self.skew_axis = Value(0)

    def to_matrix(self, time, auto_orient=False):
        from ..utils.transform import TransformMatrix
        mat = TransformMatrix()

        anchor = self.anchor_point.get_value(time) if self.anchor_point else NVector(0, 0)
        mat.translate(-anchor.x, -anchor.y)

        scale = self.scale.get_value(time) if self.scale else NVector(100, 100)
        mat.scale(scale.x / 100, scale.y / 100)

        skew = (self.skew.get_value(time) * math.pi / 180) if self.skew else 0
        if skew != 0:
            axis = (self.skew_axis.get_value(time) * math.pi / 180) if self.skew_axis else 0
            mat.skew_from_axis(-skew, axis)

        rot = (self.rotation.get_value(time) * math.pi / 180) if self.rotation else 0
        if rot:
            mat.rotate(-rot)

        if auto_orient:
            if self.position and self.position.animated:
                ao_angle = self.position.get_tangent_angle(time)
                mat.rotate(-ao_angle)

        pos = self.position.get_value(time) if self.position else NVector(0, 0)
        mat.translate(pos.x, pos.y)

        return mat


## @ingroup Lottie
class MaskMode(LottieEnum):
    """!
    How masks interact with each other
    @see https://helpx.adobe.com/after-effects/using/alpha-channels-masks-mattes.html
    """
    No = "n"
    Add = "a"
    Subtract = "s"
    Intersect = "i"
    ## @note Not in lottie web
    Lightent = "l"
    ## @note Not in lottie web
    Darken = "d"
    ## @note Not in lottie web
    Difference = "f"


## @ingroup Lottie
## @todo Implement SVG/SIF I/O
class Mask(LottieObject):
    _props = [
        LottieProp("inverted", "inv", bool, False),
        LottieProp("name", "nm", str, False),
        LottieProp("shape", "pt", ShapeProperty, False),
        LottieProp("opacity", "o", Value, False),
        LottieProp("mode", "mode", MaskMode, False),
        LottieProp("dilate", "x", Value, False),
    ]

    def __init__(self, bezier=None):
        ## Inverted Mask flag
        self.inverted = False
        ## Mask name. Used for expressions and effects.
        self.name = None
        ## Mask vertices
        self.shape = ShapeProperty(bezier)
        ## Mask opacity.
        self.opacity = Value(100)
        ## Mask mode. Not all mask types are supported.
        self.mode = MaskMode.Intersect
        self.dilate = Value(0)

    def __str__(self):
        return self.name or super().__str__()
