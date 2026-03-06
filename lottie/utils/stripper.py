from ..objects.base import LottieObject, ObjectVisitor
from ..objects.bezier import Bezier
from ..objects.helpers import Transform
from ..nvector import NVector


class Strip(ObjectVisitor):
    def __init__(self, float_round, remove_attributes={}):
        self.float_round = float_round
        self.remove_attributes = remove_attributes

    def round(self, fl):
        return round(fl, self.float_round)

    def nvector(self, value):
        value.components = list(map(self.round, value.components))
        return value

    def visit_property(self, object, property, value):
        if isinstance(value, Bezier):
            for l in ["vertices", "in_tangents", "out_tangents"]:
                try:
                    setattr(value, l, [self.nvector(NVector(p.x, p.y)) for p in getattr(value, l)])
                except:
                    print("An exception occurred")
        elif property.lottie in self.remove_attributes:
            property.set(object, None)
        elif isinstance(value, float):
            property.set(object, round(value, 3))
        elif isinstance(value, NVector):
            self.nvector(value)


class TransformStip(Strip):
    def visit(self, object):
        if isinstance(object, Transform):
            self.transform_unset(object, "anchor_point", NVector(0, 0))
            self.transform_unset(object, "position", NVector(0, 0))
            #self.transform_unset(object, "scale", NVector(100, 100))
            self.transform_unset(object, "rotation", 0)
            #self.transform_unset(object, "opacity", 100)
            self.transform_unset(object, "skew", 0)
            self.transform_unset(object, "skew_axis", 0)

    def transform_unset(self, object, prop_name, value):
        prop = getattr(object, prop_name)
        if not prop.animated and prop.value == value:
            setattr(object, prop_name, None)


heavy_strip = TransformStip(3, {"ind", "ix", "nm", "mn"})
float_strip = Strip(3)
