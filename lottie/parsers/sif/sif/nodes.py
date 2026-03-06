import enum
from .core import SifNodeMeta, FrameTime
from .enums import Smooth
from ..xml.utils import *
from ..xml.core_nodes import *
from ..xml.animatable import *
from ..xml.wrappers import *


class SifNode(metaclass=SifNodeMeta):
    def __init__(self, **kw):
        for node in self._nodes:
            node.initialize_object(kw, self)

    def __setattr__(self, name, value):
        if name in self._nodemap:
            value = self._nodemap[name].clean(value)
        return super().__setattr__(name, value)

    @staticmethod
    def static_from_dom(cls, xml: minidom.Element, registry: ObjectRegistry):
        instance = cls()
        for node in cls._nodes:
            node.from_xml(instance, xml, registry)
        return instance

    @classmethod
    def from_dom(cls, xml: minidom.Element, registry: ObjectRegistry):
        return SifNode.static_from_dom(cls, xml, registry)

    def to_dom(self, dom: minidom.Document):
        element = dom.createElement(self._tag)
        for node in self._nodes:
            node.to_xml(self, element, dom)
        return element


class AbstractTransform(SifNode):
    _nodes = [
        XmlFixedAttribute("type", "transformation")
    ]

    @classmethod
    def from_dom(cls, xml: minidom.Element, registry: ObjectRegistry):
        if xml.tagName == "bone_link":
            return SifNode.static_from_dom(BoneLinkTransform, xml, registry)

        if xml.tagName != "composite":
            raise ValueError("Invalid transform element: %s" % xml.tagName)
        return SifNode.static_from_dom(SifTransform, xml, registry)


class SifTransform(AbstractTransform):
    _tag = "composite"

    _nodes = [
        XmlAnimatable("offset", "vector", NVector(0, 0)),
        XmlAnimatable("angle", "angle", 0.),
        XmlAnimatable("skew_angle", "angle", 0.),
        XmlAnimatable("scale", "vector", NVector(1, 1)),
    ]


class BlinePoint(SifNode):
    _tag = "composite"

    _nodes = [
        XmlFixedAttribute("type", "bline_point"),
        XmlAnimatable("point", "vector", NVector(0, 0)),
        XmlAnimatable("width", "real", 1.),
        XmlAnimatable("origin", "real", .5),
        XmlAnimatable("split", "bool", False),
        XmlAnimatable("t1", "vector"),
        XmlAnimatable("t2", "vector"),
        XmlAnimatable("split_radius", "bool", True),
        XmlAnimatable("split_angle", "bool", False),
    ]


class Bline(SifNode):
    _nodes = [
        XmlAttribute("loop", bool_str, False),
        XmlFixedAttribute("type", "bline_point"),
        XmlList(BlinePoint, "points", "entry"),
    ]


class BlendMethod(enum.Enum):
    Composite = 0
    Straight = 1
    Onto = 13
    StraightOnto = 21
    Behind = 12
    Screen = 16
    Overlay = 20
    HardLight = 17
    Multiply = 6
    Divide = 7
    Add = 4
    Subtract = 5
    Difference = 18
    Lighten = 2
    Darken = 3
    Color = 8
    Hue = 9
    Saturation = 10
    Luminosity = 11
    AlphaOver = 19
    AlphaBrighten = 14
    AlphaDarken = 15
    Alpha = 23


class BlurType(enum.Enum):
    Box = 0
    FastGaussian = 1
    CrossHatch = 2
    Gaussian = 3
    Disc = 4


class WindingStyle(enum.Enum):
    NonZero = 0
    EvenOdd = 1


class Def(SifNode):
    _nodes = [
        XmlAttribute("guid", str),
        XmlAttribute("id", str),
    ]
    _subclasses = None

    @classmethod
    def from_dom(cls, xml: minidom.Element, registry: ObjectRegistry):
        actual_class = cls
        if cls == Def:
            actual_class = Def.def_types()[xml.tagName]

        obj = SifNode.static_from_dom(actual_class, xml, registry)
        if obj.id:
            registry.register_as(obj, obj.id)
        if obj.guid:
            registry.register(obj)
        return obj

    @staticmethod
    def tags():
        return list(Def.def_types().keys())

    @staticmethod
    def def_types():
        if Def._subclasses is None:
            Def._subclasses = {}
            Def._gather_def_types(Def)
        return Def._subclasses

    @staticmethod
    def _gather_def_types(cls):
        for subcls in cls.__subclasses__():
            Def._subclasses[subcls._tag] = subcls
            Def._gather_def_types(subcls)


class Duplicate(Def):
    _nodes = [
        XmlFixedAttribute("type", "real"),
        XmlAnimatable("from", "real", 1.),
        XmlAnimatable("to", "real", 1.),
        XmlAnimatable("step", "real", 1.),
    ]

    @property
    def from_(self):
        return getattr(self, "from")

    @from_.setter
    def from_(self, value):
        setattr(self, "from", value)


class ExportedValue(Def):
    def __init__(self, id, value, typename):
        self.id = id
        self.value = value
        self.type = TypeDescriptor(typename)

    def to_dom(self, dom: minidom.Document):
        element = self.value.to_dom(dom, self.type)
        element.setAttribute("id", self.id)
        return element


class Layer(SifNode):
    _types = None

    _version = "0.1"
    _layer_type = None

    _nodes = [
        XmlAttribute("type", str),
        XmlAttribute("active", bool_str, True),
        XmlAttribute("version", str),
        XmlAttribute("exclude_from_rendering", bool_str, False),
        XmlAttribute("desc", str, ""),
    ]

    def __init__(self, **kw):
        kw.setdefault("version", self._version)
        super().__init__(**kw)
        self.type = self._layer_type

    def __repr__(self):
        return "<%s.%s %r>" % (__name__, self.__class__.__name__, self.desc or self.type)

    def to_dom(self, dom: minidom.Document):
        element = dom.createElement("layer")
        for node in self._nodes:
            node.to_xml(self, element, dom)
        return element

    @classmethod
    def from_dom(cls, xml: minidom.Element, registry: ObjectRegistry):
        actual_class = cls
        if cls == Layer:
            type = xml.getAttribute("type")
            actual_class = Layer.layer_types().get(type, Layer)

        return SifNode.static_from_dom(actual_class, xml, registry)

    @staticmethod
    def layer_types():
        if Layer._types is None:
            Layer._types = {}
            Layer._gather_layer_types(Layer)
        return Layer._types

    @staticmethod
    def _gather_layer_types(cls):
        for subcls in cls.__subclasses__():
            if subcls._layer_type:
                Layer._types[subcls._layer_type] = subcls
            Layer._gather_layer_types(subcls)


class DrawableLayer(Layer):
    _nodes = [
        XmlParam("z_depth", "real", 0.),
        XmlParam("amount", "real", 1.),
        XmlParam("blend_method", "integer", BlendMethod.Composite, BlendMethod, static=True),
    ]


class GroupLayerBase(DrawableLayer):
    _nodes = [
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParamSif("transformation", AbstractTransform, SifTransform),
        XmlWrapperParam("canvas", XmlWrapper("canvas", XmlList(Layer))),

        XmlParam("time_dilation", "real", 1.),
        XmlParam("time_offset", "time", FrameTime(0, FrameTime.Unit.Frame)),
        XmlParam("children_lock", "bool", False, static=True),
        XmlParam("outline_grow", "real", 0.),
    ]

    def add_layer(self, layer: Layer):
        self.layers.append(layer)
        return layer


class FilterGroupLayer(GroupLayerBase):
    _layer_type = "filter_group"

    _nodes = [
    ]


class GroupLayer(GroupLayerBase):
    _layer_type = "group"
    _version = "0.3"

    _nodes = [
        XmlParam("z_range", "bool", False, static=True),
        XmlParam("z_range_position", "real", 0.),
        XmlParam("z_range_depth", "real", 0.),
        XmlParam("z_range_blur", "real", 0.),
    ]


class SwitchLayer(GroupLayerBase):
    _layer_type = "switch"

    _nodes = [
        XmlParam("layer_name", "string"),
        XmlParam("layer_depth", "integer", -1),
    ]


class RectangleLayer(DrawableLayer):
    _layer_type = "rectangle"

    _nodes = [
        XmlParam("color", "color", NVector(0, 0, 0, 1)),
        XmlParam("point1", "vector", NVector(0, 0)),
        XmlParam("point2", "vector", NVector(0, 0)),
        XmlParam("expand", "real", 0.),
        XmlParam("invert", "bool", False),
        XmlParam("feather_x", "real", 0.),
        XmlParam("feather_y", "real", 0.),
        XmlParam("bevel", "real", 0.),
        XmlParam("bevCircle", "bool", True),
    ]


class CircleLayer(DrawableLayer):
    _layer_type = "circle"

    _nodes = [
        XmlParam("color", "color", NVector(0, 0, 0, 1)),
        XmlParam("radius", "real", 0.),
        XmlParam("feather", "real", 0.),
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParam("invert", "bool", False),
    ]


class SimpleCircleLayer(DrawableLayer):
    _layer_type = "simple_circle"

    _nodes = [
        XmlParam("color", "color", NVector(0, 0, 0, 1)),
        XmlParam("radius", "real", 0.),
        XmlParam("center", "vector", NVector(0, 0)),
    ]


class ComplexShape(DrawableLayer):
    _nodes = [
        XmlParam("color", "color", NVector(0, 0, 0, 1)),
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParam("invert", "bool", False),
        XmlParam("antialias", "bool", True),
        XmlParam("feather", "real", 0.),
        XmlParam("blurtype", "integer", BlurType.FastGaussian, BlurType),
        XmlParam("winding_style", "integer", WindingStyle.NonZero, WindingStyle),
    ]


class StarLayer(ComplexShape):
    _layer_type = "star"

    _nodes = [
        XmlParam("radius1", "real", 0.),
        XmlParam("radius2", "real", 0.),
        XmlParam("angle", "angle", 0.),
        XmlParam("points", "integer", 5),
        XmlParam("regular_polygon", "bool", False),
    ]


class LineCap(enum.Enum):
    Rounded = 1
    Squared = 2
    Peak = 3
    Flat = 4
    InnerRounded = 5
    OffPeak = 6


class CuspStyle(enum.Enum):
    Miter = 0
    Round = 1
    Bevel = 2


class AbstractOutline(ComplexShape):
    _nodes = [
        XmlParam("width", "real", 0.1),
        XmlParam("expand", "real", 0.),
        XmlParamSif("bline", Bline),
    ]


class OutlineLayer(AbstractOutline):
    _layer_type = "outline"

    _nodes = [
        XmlParam("sharp_cusps", "bool", True),
        XmlParam("round_tip[0]", "bool", True),
        XmlParam("round_tip[1]", "bool", True),
        XmlParam("homogeneous_width", "bool", True),
    ]

    @property
    def start_tip(self):
        return LineCap.Rounded if self.round_tip_0 else LineCap.Flat

    @property
    def end_tip(self):
        return LineCap.Rounded if self.round_tip_1 else LineCap.Flat

    @property
    def cusp_type(self):
        return CuspStyle.Miter if self.sharp_cusps else CuspStyle.Round


class AdvancedOutlineLayer(AbstractOutline):
    _layer_type = "advanced_outline"

    _nodes = [
        XmlParam("start_tip", "integer", LineCap.Rounded, LineCap),
        XmlParam("end_tip", "integer", LineCap.Rounded, LineCap),
        XmlParam("cusp_type", "integer", CuspStyle.Miter, CuspStyle),
        XmlParam("smoothness", "real", 1.),
        XmlParam("homogeneous", "bool", False),
        # TODO wplist
    ]


class PolygonLayer(ComplexShape):
    _layer_type = "polygon"

    _nodes = [
        XmlDynamicListParam("vector_list", "vector", "points"),
    ]


class RegionLayer(ComplexShape):
    _layer_type = "region"

    _nodes = [
        XmlParamSif("bline", Bline),
    ]


class FontStyle(enum.Enum):
    Normal = 0
    Oblique = 1
    Italic = 2


class TextLayer(DrawableLayer):
    _layer_type = "text"

    _nodes = [
        XmlParam("text", "string"),
        XmlParam("color", "color", NVector(0, 0, 0, 1)),
        XmlParam("family", "string"),
        XmlParam("style", "integer", FontStyle.Normal, FontStyle),
        XmlParam("weight", "integer", 400),
        XmlParam("compress", "real", 1.),
        XmlParam("vcompress", "real", 1.),
        XmlParam("size", "vector", NVector(1, 1)),
        XmlParam("orient", "vector", NVector(.5, .5)),
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParam("use_kerning", "bool", False),
        XmlParam("grid_fit", "bool", False),
        XmlParam("invert", "bool", False),
    ]


class TransformDown(Layer):
    pass


class TranslateLayer(TransformDown):
    _layer_type = "translate"

    _nodes = [
        XmlParam("origin", "vector", NVector(0, 0)),
    ]


class RotateLayer(TransformDown):
    _layer_type = "rotate"

    _nodes = [
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParam("amount", "angle", 0.),
    ]


class ScaleLayer(TransformDown):
    _layer_type = "zoom"

    _nodes = [
        XmlParam("center", "vector", NVector(0, 0)),
        XmlParam("amount", "real", 0.),
    ]


class GradientLayer(DrawableLayer):
    _nodes = [
        XmlParam("gradient", "gradient", []),
        XmlParam("loop", "bool", False),
        XmlParam("zigzag", "bool", False),
    ]


class RadialGradient(GradientLayer):
    _layer_type = "radial_gradient"

    _nodes = [
        XmlParam("center", "vector", NVector(0, 0)),
        XmlParam("radius", "real", 1),
    ]


class LinearGradient(GradientLayer):
    _layer_type = "linear_gradient"

    _nodes = [
        XmlParam("p1", "vector", NVector(0, 0)),
        XmlParam("p2", "vector", NVector(0, 0)),
    ]


class ConicalLinearGradient(DrawableLayer):
    _layer_type = "conical_gradient"

    _nodes = [
        XmlParam("gradient", "gradient", []),
        XmlParam("symmetric", "bool", False),
        XmlParam("center", "vector", NVector(0, 0)),
        XmlParam("angle", "angle", 0.),
    ]


class CurveGradient(GradientLayer):
    _layer_type = "curve_gradient"

    _nodes = [
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParam("width", "real", 0.0833333358),
        XmlParamSif("bline", Bline),
        XmlParam("perpendicular", "bool", False),
        XmlParam("fast", "bool", True),
    ]


class NoiseLayer(DrawableLayer):
    _layer_type = "noise"

    _nodes = [
        XmlParam("gradient", "gradient", []),
        XmlParam("seed", "integer", 0),
        XmlParam("size", "vector", NVector(1, 1)),
        XmlParam("smooth", "integer", Smooth.Cosine, Smooth),
        XmlParam("detail", "integer", 4),
        XmlParam("speed", "integer", 0.),
        XmlParam("turbulent", "bool", False),
        XmlParam("do_alpha", "bool", False),
        XmlParam("super_sample", "bool", False),
    ]


class SpiralGradient(DrawableLayer):
    _layer_type = "spiral_gradient"

    _nodes = [
        XmlParam("gradient", "gradient", []),
        XmlParam("center", "vector", NVector(0, 0)),
        XmlParam("radius", "real", 0.5),
        XmlParam("angle", "real", 0),
        XmlParam("clockwise", "bool", False),
    ]


class BoneRoot(SifNode):
    _tag = "bone_root"

    _nodes = [
        XmlFixedAttribute("type", "bone_object"),
        XmlAttribute("guid", str)
    ]

    @classmethod
    def from_dom(cls, xml: minidom.Element, registry: ObjectRegistry):
        if xml.tagName == "bone_root":
            val = SifNode.static_from_dom(BoneRoot, xml, registry)
        else:
            val = SifNode.static_from_dom(Bone, xml, registry)
        registry.register(val)
        return val

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.guid)


class Bone(BoneRoot):
    _tag = "bone"

    _nodes = [
        XmlWrapper("name", XmlSimpleElement("string", att_name="name")),
        XmlBoneReference("parent"),
        XmlAnimatable("origin", "vector", NVector(0, 0)),
        XmlAnimatable("angle", "angle", 0.),
        XmlAnimatable("scalelx", "real", 1.),
        XmlAnimatable("width", "real", .1),
        XmlAnimatable("scalex", "real", 1.),
        XmlAnimatable("tipwidth", "real", .1),
        XmlAnimatable("bone_depth", "real", 0.),
        XmlAnimatable("length", "real", 1.),
    ]


class BoneLinkTransform(AbstractTransform):
    _tag = "bone_link"

    _nodes = [
        XmlBoneReference("bone"),
        XmlSifElement("base_value", SifTransform),
        XmlAnimatable("translate", "bool", True),
        XmlAnimatable("rotate", "bool", True),
        XmlAnimatable("skew", "bool", True),
        XmlAnimatable("scale_x", "bool", True),
        XmlAnimatable("scale_y", "bool", True),
    ]


class SkeletonLayer(Layer):
    _layer_type = "skeleton"

    _nodes = [
        XmlParam("z_depth", "real", 0.),
        XmlParam("amount", "real", 1.),
        XmlParam("name", "string"),
        XmlStaticListParam("bones", "bone_object")
    ]


class SubsamplingType(enum.Enum):
    Constant = 0
    Linear = 1
    Hyperbolic = 2


class MotionBlurLayer(Layer):
    _layer_type = "MotionBlur"

    _nodes = [
        XmlParam("aperture", "time", FrameTime(1, FrameTime.Unit.Seconds)),
        XmlParam("subsamples_factor", "real", 1.),
        XmlParam("subsampling_type", "integer", SubsamplingType.Hyperbolic, SubsamplingType),
        XmlParam("subsample_start", "real", 0.),
        XmlParam("subsample_end", "real", 1.),
    ]


class BlurLayer(DrawableLayer):
    _layer_type = "blur"

    _nodes = [
        XmlParam("size", "vector", NVector(1, 1)),
        XmlParam("type", "integer", BlurType.FastGaussian, BlurType),
    ]


class RadialBlurLayer(DrawableLayer):
    _layer_type = "radial_blur"

    _nodes = [
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParam("size", "real", .2),
        XmlParam("fade_out", "bool", False),
    ]


class CurveWarpLayer(Layer):
    _layer_type = "curve_warp"

    _nodes = [
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParam("perp_width", "real", 1.),
        XmlParam("start_point", "vector", NVector(0, 0)),
        XmlParam("end_point", "vector", NVector(0, 0)),
        XmlParamSif("bline", Bline),
        XmlParam("fast", "bool", True),
    ]


class InsideOutLayer(Layer):
    _layer_type = "inside_out"

    _nodes = [
        XmlParam("origin", "vector", NVector(0, 0)),
    ]


class NoiseDistortLayer(DrawableLayer):
    _layer_type = "noise_distort"

    _nodes = [
        XmlParam("displacement", "vector", NVector(0.25, 0.25)),
        XmlParam("size", "vector", NVector(1, 1)),
        XmlParam("seed", "integer", 0),
        XmlParam("smooth", "integer", Smooth.Cosine, Smooth),
        XmlParam("detail", "integer", 4),
        XmlParam("speed", "real", 0.),
        XmlParam("turbulent", "bool", False),
    ]


class SkeletonDeformationLayer(DrawableLayer):
    _layer_type = "skeleton_deformation"

    _nodes = [
        XmlParam("displacement", "vector", NVector(0.25, 0.25)),
        XmlParam("point1", "vector", NVector(0, 0)),
        XmlParam("point2", "vector", NVector(0, 0)),
        XmlParam("x_subdivisions", "integer", 32),
        XmlParam("y_subdivisions", "integer", 32),
        # TODO bones (pair_bone_object_bone_object)
    ]


class DistortType(enum.Enum):
    Spherize = 0
    VerticalBar = 1
    HorizontalBar = 2


class SpherizeLayer(Layer):
    _layer_type = "spherize"

    _nodes = [
        XmlParam("center", "vector", NVector(0., 0.)),
        XmlParam("radius", "real", 1.),
        XmlParam("amount", "real", 1.),
        XmlParam("clip", "bool", False),
        XmlParam("type", "integer", DistortType.Spherize, DistortType),
    ]


class StretchLayer(Layer):
    _layer_type = "stretch"

    _nodes = [
        XmlParam("amount", "vector", NVector(1., 1.)),
        XmlParam("center", "vector", NVector(0., 0.)),
    ]


class TwirlLayer(Layer):
    _layer_type = "twirl"

    _nodes = [
        XmlParam("center", "vector", NVector(0., 0.)),
        XmlParam("radius", "real", 1.),
        XmlParam("rotations", "real", 0.),
        XmlParam("distort_inside", "bool", True),
        XmlParam("distort_outside", "bool", False),
    ]


class WarpLayer(Layer):
    _layer_type = "warp"

    _nodes = [
        XmlParam("src_tl", "vector", NVector(0., 0.)),
        XmlParam("src_br", "vector", NVector(0., 0.)),
        XmlParam("dest_tl", "vector", NVector(0., 0.)),
        XmlParam("dest_tr", "vector", NVector(0., 0.)),
        XmlParam("dest_bl", "vector", NVector(0., 0.)),
        XmlParam("dest_br", "vector", NVector(0., 0.)),
        XmlParam("clip", "bool", True),
        XmlParam("interpolation", "integer", Smooth.Cubic, Smooth),
    ]


class MetaballsLayer(DrawableLayer):
    _layer_type = "metaballs"

    _nodes = [
        XmlParam("gradient", "gradient", []),
        XmlDynamicListParam("centers", "vector"),
        XmlDynamicListParam("radii", "real"),
        XmlDynamicListParam("weights", "real"),
        XmlParam("threshold", "real", 0.),
        XmlParam("threshold1", "real", 1.),
        XmlParam("positive", "bool", False),
    ]


class ClampLayer(Layer):
    _layer_type = "clamp"

    _nodes = [
        XmlParam("invert_negative", "bool", False),
        XmlParam("clamp_ceiling", "bool", False),
        XmlParam("ceiling", "real", 1.),
        XmlParam("floor", "real", 0.),
    ]


class ColorCorrectLayer(Layer):
    _layer_type = "colorcorrect"

    _nodes = [
        XmlParam("hue_adjust", "angle", 0.),
        XmlParam("brightness", "real", 0.),
        XmlParam("contrast", "real", 1.),
        XmlParam("exposure", "real", 0.),
        XmlParam("gamma", "real", 1.),
    ]


class HalftoneType(enum.Enum):
    Symmetric = 0
    LightOnDark = 2
    Diamond = 3
    Stripe = 4


class Halftone2Layer(DrawableLayer):
    _layer_type = "halftone2"

    _nodes = [
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParam("angle", "angle", 0.),
        XmlParam("size", "vector", NVector(0.25, 0.25)),
        XmlParam("color_light", "color", NVector(1, 1, 1, 1)),
        XmlParam("color_dark", "color", NVector(0, 0, 0, 1)),
        XmlParam("type", "integer", HalftoneType.Symmetric, HalftoneType),
    ]


class Halftone3Layer(DrawableLayer):
    _layer_type = "halftone3"

    _nodes = [
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParam("size", "vector", NVector(0.25, 0.25)),
        XmlParam("type", "integer", HalftoneType.Symmetric, HalftoneType),
        XmlParam("subtractive", "bool", True),

        XmlParam("color[0]", "color", NVector(0, 1, 1, 1)),
        XmlParam("tone[0].origin", "vector", NVector(0, 0)),
        XmlParam("tone[0].angle", "angle", 0.),

        XmlParam("color[1]", "color", NVector(1, 0, 1, 1)),
        XmlParam("tone[1].origin", "vector", NVector(0, 0)),
        XmlParam("tone[1].angle", "angle", 30.),

        XmlParam("color[2]", "color", NVector(1, 1, 0, 1)),
        XmlParam("tone[2].origin", "vector", NVector(0, 0)),
        XmlParam("tone[2].angle", "angle", 60.),
    ]


class LumakeyLayer(DrawableLayer):
    _layer_type = "lumakey"

    _nodes = [
    ]


class JuliaLayer(DrawableLayer):
    _layer_type = "julia"

    _nodes = [
        XmlParam("icolor", "color", NVector(0, 0, 0, 1)),
        XmlParam("ocolor", "color", NVector(0, 0, 0, 1)),
        XmlParam("color_shift", "real", 0.),
        XmlParam("iterations", "integer", 32),
        XmlParam("seed", "vector", NVector(0, 0)),
        XmlParam("bailout", "real", 2.),
        XmlParam("distort_inside", "bool", True),
        XmlParam("shade_inside", "bool", True),
        XmlParam("solid_inside", "bool", False),
        XmlParam("invert_inside", "bool", False),
        XmlParam("color_inside", "bool", True),
        XmlParam("distort_outside", "bool", True),
        XmlParam("shade_outside", "bool", True),
        XmlParam("solid_outside", "bool", False),
        XmlParam("invert_outside", "bool", False),
        XmlParam("color_outside", "bool", False),
        XmlParam("color_cycle", "bool", False),
        XmlParam("smooth_outside", "bool", True),
        XmlParam("broken", "bool", False),
    ]


class MandelbrotLayer(Layer):
    _layer_type = "mandelbrot"

    _nodes = [
        XmlParam("iterations", "integer", 32),
        XmlParam("bailout", "real", 2.),
        XmlParam("broken", "bool", False),
        XmlParam("distort_inside", "bool", True),
        XmlParam("shade_inside", "bool", True),
        XmlParam("solid_inside", "bool", False),
        XmlParam("invert_inside", "bool", False),
        XmlParam("distort_outside", "bool", True),
        XmlParam("shade_outside", "bool", True),
        XmlParam("solid_outside", "bool", False),
        XmlParam("invert_outside", "bool", False),
        XmlParam("smooth_outside", "bool", True),

        XmlParam("gradient_inside", "gradient", []),
        XmlParam("gradient_offset_inside", "real", 0.),
        XmlParam("gradient_loop_inside", "bool", True),

        XmlParam("gradient_outside", "gradient", []),
        XmlParam("gradient_offset_outside", "real", 0.),
        XmlParam("gradient_loop_outside", "bool", True),
        XmlParam("gradient_scale_outside", "real", 1.),
    ]


class CheckerboardLayer(DrawableLayer):
    _layer_type = "checker_board"

    _nodes = [
        XmlParam("color", "color", NVector(0, 0, 0, 1)),
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParam("size", "vector", NVector(0.25, 0.25)),
        XmlParam("antialias", "bool", True),
    ]


class SolidColorLayer(DrawableLayer):
    _layer_type = "SolidColor"

    _nodes = [
        XmlParam("color", "color", NVector(0, 0, 0, 1)),
    ]


class DuplicateLayer(DrawableLayer):
    _layer_type = "duplicate"

    _nodes = [
        XmlParam("index", "real"),
    ]


class ImportedImageLayer(DrawableLayer):
    _layer_type = "import"

    _nodes = [
        XmlParam("tl", "vector", NVector(0, 0)),
        XmlParam("br", "vector", NVector(0, 0)),
        XmlParam("c", "integer", Smooth.Linear, Smooth),
        XmlParam("gamma_adjust", "real", 1.),
        XmlParam("filename", "string"),
        XmlParam("time_offset", "time", FrameTime(0, FrameTime.Unit.Frame)),
    ]


class PlantLayer(DrawableLayer):
    _layer_type = "plant"

    _nodes = [
        XmlParamSif("bline", Bline),
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParam("gradient", "gradient", []),
        XmlParam("split_angle", "angle", 10.),
        XmlParam("gravity", "vector", NVector(0, -.1)),
        XmlParam("velocity", "real", .3),
        XmlParam("perp_velocity", "real", 0.),
        XmlParam("size", "real", 0.015),
        XmlParam("size_as_alpha", "bool", False),
        XmlParam("reverse", "bool", True),
        XmlParam("step", "real", 0.01),
        XmlParam("seed", "integer", 0),
        XmlParam("splits", "integer", 5),
        XmlParam("sprouts", "integer", 5),
        XmlParam("random_factor", "real", 0.2),
        XmlParam("drag", "real", 0.1),
        XmlParam("use_width", "bool", True),
    ]


class SoundLayer(Layer):
    _layer_type = "sound"

    _nodes = [
        XmlParam("z_depth", "real", 0.),
        XmlParam("filename", "string"),
        XmlParam("delay", "time", FrameTime(0, FrameTime.Unit.Seconds)),
        XmlParam("volume", "real", 1.),
    ]


class SuperSampleLayer(Layer):
    _layer_type = "super_sample"

    _nodes = [
        XmlParam("width", "integer", 2),
        XmlParam("height", "integer", 2),
        XmlParam("scanline", "bool", False),
        XmlParam("alpha_aware", "bool", True),
    ]


class XorPatternLayer(DrawableLayer):
    _layer_type = "xor_pattern"

    _nodes = [
        XmlParam("origin", "vecor", NVector(0, 0)),
        XmlParam("size", "vecor", NVector(0.25, 0.25)),
    ]


class BevelLayer(DrawableLayer):
    _layer_type = "bevel"

    _nodes = [
        XmlParam("type", "integer", BlurType.FastGaussian, BlurType),
        XmlParam("color1", "color", NVector(1, 1, 1, 1)),
        XmlParam("color2", "color", NVector(0, 0, 0, 1)),
        XmlParam("angle", "angle", 135.),
        XmlParam("depth", "real", .2),
        XmlParam("softness", "real", .1),
        XmlParam("use_luma", "bool", False),
        XmlParam("solid", "bool", False),
    ]


class ShadeLayer(DrawableLayer):
    _layer_type = "shade"

    _nodes = [
        XmlParam("type", "integer", BlurType.FastGaussian, BlurType),
        XmlParam("color", "color", NVector(1, 1, 1, 1)),
        XmlParam("origin", "vector", NVector(0, 0)),
        XmlParam("size", "vector", NVector(0.1, 0.1)),
        XmlParam("invert", "bool", False),
    ]


class FreeTimeLayer(Layer):
    _layer_type = "freetime"

    _nodes = [
        XmlParam("z_depth", "real", 0.),
        XmlParam("time", "time", FrameTime(0, FrameTime.Unit.Seconds)),
    ]


class StroboscopeLayer(Layer):
    _layer_type = "stroboscope"

    _nodes = [
        XmlParam("z_depth", "real", 0.),
        XmlParam("frequency", "real", 2.),
    ]


class TimeLoopLayer(Layer):
    _layer_type = "timeloop"

    _nodes = [
        XmlParam("z_depth", "real", 0.),
        XmlParam("link_time", "time", FrameTime(0, FrameTime.Unit.Seconds), static=True),
        XmlParam("local_time", "time", FrameTime(0, FrameTime.Unit.Seconds), static=True),
        XmlParam("duration", "time", FrameTime(0, FrameTime.Unit.Seconds), static=True),
        XmlParam("only_for_positive_duration", "bool", False, static=True),
        XmlParam("symmetrical", "bool", True, static=True),
    ]


class Keyframe(SifNode):
    _nodes = [
        XmlAttribute("active", bool_str, True),
        XmlAttribute("time", FrameTime, FrameTime(0, FrameTime.Unit.Frame)),
    ]


class Canvas(SifNode, ObjectRegistry):
    _nodes = [
        XmlAttribute("version"),
        XmlAttribute("width", float, 512),
        XmlAttribute("height", float, 512),
        XmlAttribute("xres", float, 2834.645752),
        XmlAttribute("yres", float, 2834.645752),
        XmlAttribute("gamma-r", float, 1.),
        XmlAttribute("gamma-g", float, 1.),
        XmlAttribute("gamma-b", float, 1.),
        XmlAttribute("view-box", NVector),
        XmlAttribute("antialias", bool, True),
        XmlAttribute("fps", float, 60),
        XmlAttribute("begin-time", FrameTime, FrameTime(0, FrameTime.Unit.Frame)),
        XmlAttribute("end-time", FrameTime, FrameTime(3, FrameTime.Unit.Seconds)),
        XmlAttribute("bgcolor", NVector, NVector(0, 0, 0, 0)),
        XmlSimpleElement("name"),
        XmlMeta("background_first_color", NVector, NVector(0.88, 0.88, 0.88)),
        XmlMeta("background_rendering", bool, False),
        XmlMeta("background_second_color", NVector, NVector(0.65, 0.65, 0.65)),
        XmlMeta("background_size", NVector, NVector(15, 15)),
        XmlMeta("grid_color", NVector, NVector(0.62, 0.62, 0.62)),
        XmlMeta("grid_show", bool, False),
        XmlMeta("grid_size", NVector, NVector(0.25, 0.25)),
        XmlMeta("grid_snap", bool, False),
        XmlMeta("guide_color", NVector, NVector(0.4, 0.4, 1)),
        XmlMeta("guide_show", bool, True),
        XmlMeta("guide_snap", bool, False),
        XmlMeta("jack_offset", float, 0),
        XmlMeta("onion_skin", bool, False),
        XmlMeta("onion_skin_future", int, 0),
        XmlMeta("onion_skin_past", int, 1),
        XmlList(Keyframe),
        XmlWrapper("defs", XmlList(Def, "defs", None, Def.tags())),
        XmlWrapper("bones", XmlList(BoneRoot, "bones", None, {"bone", "bone_root"})),
        XmlList(Layer),
    ]

    def __init__(self, **kw):
        SifNode.__init__(self, **kw)
        ObjectRegistry.__init__(self)

    def to_xml(self):
        dom = minidom.Document()
        dom.appendChild(self.to_dom(dom))
        return dom

    @classmethod
    def from_xml_file(cls, xml):
        if isinstance(xml, str):
            with open(xml, "r") as file:
                return cls.from_xml(minidom.parse(file))
        return cls.from_xml(minidom.parse(xml))

    @classmethod
    def from_xml_string(cls, xml):
        return cls.from_xml(minidom.parseString(xml))

    @classmethod
    def from_xml(cls, xml: minidom.Document):
        obj = cls.from_dom(xml.documentElement, None)
        xml.unlink()
        return obj

    @classmethod
    def from_dom(cls, xml: minidom.Element, registry: ObjectRegistry = None):
        instance = cls()
        for node in cls._nodes:
            node.from_xml(instance, xml, instance)
        return instance

    def time_to_frames(self, time: FrameTime):
        if time.unit == FrameTime.Unit.Frame:
            return time.value
        elif time.unit == FrameTime.Unit.Seconds:
            return time.value * self.fps

    def add_layer(self, layer: Layer):
        self.layers.append(layer)
        return layer

    def make_color(self, r, g, b, a=1):
        """
        Applies Gamma to the rgb values
        """
        return NVector(
            r ** self.gamma_r,
            g ** self.gamma_g,
            b ** self.gamma_b,
            a
        )


class Segment(SifNode):
    _nodes = [
        XmlAnimatable("p1", "vector"),
        XmlAnimatable("t1", "vector"),
        XmlAnimatable("p2", "vector"),
        XmlAnimatable("t2", "vector")
    ]


class WeightedVector(SifNode):
    _tag = "weighted_vector"

    _nodes = [
        XmlAnimatable("weight", "real", 1.),
        XmlAnimatable("value", "vector"),
    ]
