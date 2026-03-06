from xml.dom import minidom
import enum

from ....nvector import NVector
from ..ast_impl.base import SifAstNode, TypeDescriptor, ObjectRegistry
from ..xml.animatable import XmlAnimatable
from ..xml.wrappers import XmlBoneReference, XmlSifElement, XmlList
from ..sif.nodes import Segment, WeightedVector, Bline
from ..sif.enums import Smooth
from ..sif.core import SifNodeMeta, FrameTime


class SifAstComplex(SifAstNode, metaclass=SifNodeMeta):
    _nodes = []

    def __init__(self, **kw):
        for node in self._nodes:
            node.initialize_object(kw, self)

    @classmethod
    def from_dom(cls, xml: minidom.Element, param: TypeDescriptor, registry: ObjectRegistry):
        outcls = cls.get_class_from_dom(xml, param, registry)
        instance = outcls()
        for node in outcls._nodes:
            node.from_xml(instance, xml, registry)
        return instance

    @classmethod
    def get_class_from_dom(cls, xml: minidom.Element, param: TypeDescriptor, registry: ObjectRegistry):
        return cls

    def to_dom(self, dom: minidom.Document, param: TypeDescriptor):
        element = self._prepare_to_dom(dom, param)
        for node in self._nodes:
            node.to_xml(self, element, dom, param)
        return element


class SifAstBoneLink(SifAstComplex):
    _tag = "bone_link"

    _nodes = [
        XmlBoneReference("bone"),
        XmlAnimatable("base_value", "vector", NVector(0, 0)),
        XmlAnimatable("translate", "bool", True),
        XmlAnimatable("rotate", "bool", True),
        XmlAnimatable("skew", "bool", True),
        XmlAnimatable("scale_x", "bool", True),
        XmlAnimatable("scale_y", "bool", True),
    ]


class SifAstBoneInfluence(SifAstComplex):
    _tag = "boneinfluence"

    _nodes = [
        # TODO bone_weight_list
        XmlAnimatable("link", "vector", NVector(0, 0)),
    ]


class SifSegCalcTangent(SifAstComplex):
    _tag = "segcalctangent"

    _nodes = [
        XmlSifElement("segment", Segment),
        XmlAnimatable("amount", "real", .5),
    ]


class SifSegCalcVertex(SifAstComplex):
    _tag = "segcalcvertex"

    _nodes = [
        XmlSifElement("segment", Segment),
        XmlAnimatable("amount", "real", .5),
    ]


class WeightedAverage(SifAstComplex):
    _tag = "weighted_average"

    _nodes = [
        XmlList(WeightedVector, "vectors", "entry"),
    ]

    def _prepare_to_dom(self, dom: minidom.Document, param: TypeDescriptor):
        element = dom.createElement(self._tag)
        element.setAttribute("type", "weighted_vector")
        return element


class SifAdd(SifAstComplex):
    _tag = "add"

    _nodes = [
        XmlAnimatable("lhs", "_recurse"),
        XmlAnimatable("rhs", "_recurse"),
        XmlAnimatable("scalar", "real", 1.),
    ]


class SifAnimatedFile(SifAstComplex):
    _tag = "animated_file"

    _nodes = [
        XmlAnimatable("filename", "string"),
    ]


class Accuracy(enum.Enum):
    Rough = 0
    Normal = 1
    Fine = 2
    Extreme = 3


class DerivativeOrder:
    FirstDerivative = 0
    SecondDerivative = 1


class SifDerivative(SifAstComplex):
    _tag = "derivative"

    _nodes = [
        XmlAnimatable("link", "_recurse"),
        XmlAnimatable("interval", "real", 0.01),
        XmlAnimatable("accuracy", "integer", Accuracy.Normal, Accuracy),
        XmlAnimatable("order", "integer", DerivativeOrder.FirstDerivative, DerivativeOrder),
    ]


class SifDynamic(SifAstComplex):
    _tag = "dynamic"

    _nodes = [
        XmlAnimatable("tip_static", "vector", NVector(0, 0)),
        XmlAnimatable("origin", "vector", NVector(0, 0)),
        XmlAnimatable("force", "vector", NVector(0, 0)),
        XmlAnimatable("torque", "real", 0.),
        XmlAnimatable("damping", "real", 0.4),
        XmlAnimatable("friction", "real", 0.4),
        XmlAnimatable("spring", "real", 30.),
        XmlAnimatable("torsion", "real", 30.),
        XmlAnimatable("mass", "real", 0.3),
        XmlAnimatable("inertia", "real", 0.3),
        XmlAnimatable("spring_rigid", "bool", False),
        XmlAnimatable("torsion_rigid", "bool", False),
        XmlAnimatable("origin_drags_tip", "bool", True),
    ]


class SifGreyed(SifAstComplex):
    _tag = "greyed"

    _nodes = [
        XmlAnimatable("link", "_recurse"),
    ]


class SifLinear(SifAstComplex):
    _tag = "linear"

    _nodes = [
        XmlAnimatable("slope", "vector", NVector(0, 0)),
        XmlAnimatable("offset", "vector", NVector(0, 0)),
    ]


class SifRadialComposite(SifAstComplex):
    _tag = "radial_composite"

    _nodes = [
        XmlAnimatable("radius", "real", 0.),
        XmlAnimatable("theta", "angle", 0.),
    ]


class SifComposite(SifAstComplex):
    _tag = "composite"

    @classmethod
    def get_class_from_dom(cls, xml: minidom.Element, param: TypeDescriptor, registry: ObjectRegistry):
        type = xml.getAttribute("type")
        if type == "vector":
            return SifVectorComposite
        return None

    def _prepare_to_dom(self, dom: minidom.Document, param: TypeDescriptor):
        element = dom.createElement("composite")
        element.setAttribute("type", param.typename)
        return element


class SifVectorComposite(SifComposite):
    _type = "vector"

    _nodes = [
        XmlAnimatable("x", "real", 0.),
        XmlAnimatable("y", "real", 0.),
    ]


class SifRandom(SifAstComplex):
    _tag = "random"

    _nodes = [
        XmlAnimatable("link", "_recurse"),
        XmlAnimatable("radius", "real", 0.),
        XmlAnimatable("seed", "integer", 0),
        XmlAnimatable("speed", "real", 1.),
        XmlAnimatable("smooth", "integer", Smooth.Cubic, Smooth),
        XmlAnimatable("loop", "real", 0.),
    ]


class SifReference(SifAstComplex):
    _tag = "link"

    _nodes = [
        XmlAnimatable("reference", "_recurse"),
    ]


class SifScale(SifAstComplex):
    _tag = "scale"

    _nodes = [
        XmlAnimatable("link", "_recurse"),
        XmlAnimatable("scalar", "real", 1.),
    ]


class SifStep(SifAstComplex):
    _tag = "step"

    _nodes = [
        XmlAnimatable("link", "_recurse"),
        XmlAnimatable("duration", "time", FrameTime(1, FrameTime.Unit.Seconds)),
        XmlAnimatable("start_time", "time", FrameTime(0, FrameTime.Unit.Seconds)),
        XmlAnimatable("intersection", "real", 0.5),
    ]


class SifSubtract(SifAstComplex):
    _tag = "subtract"

    _nodes = [
        XmlAnimatable("lhs", "_recurse"),
        XmlAnimatable("rhs", "_recurse"),
        XmlAnimatable("scalar", "real", 1.),
    ]


class SifSwitch(SifAstComplex):
    _tag = "switch"

    _nodes = [
        XmlAnimatable("link_off", "_recurse"),
        XmlAnimatable("link_on", "_recurse"),
        XmlAnimatable("switch", "bool", False),
    ]


class SifTimedSwap(SifAstComplex):
    _tag = "timed_swap"

    _nodes = [
        XmlAnimatable("before", "_recurse"),
        XmlAnimatable("after", "_recurse"),
        XmlAnimatable("time", "time", FrameTime(0, FrameTime.Unit.Seconds)),
        XmlAnimatable("length", "time", FrameTime(0, FrameTime.Unit.Seconds)),
    ]


class SifTimeLoop(SifAstComplex):
    _tag = "timeloop"

    _nodes = [
        XmlAnimatable("link", "_recurse"),
        XmlAnimatable("link_time", "time", FrameTime(0, FrameTime.Unit.Seconds)),
        XmlAnimatable("local_time", "time", FrameTime(0, FrameTime.Unit.Seconds)),
        XmlAnimatable("duration", "time", FrameTime(0, FrameTime.Unit.Seconds)),
    ]


class SifPower(SifAstComplex):
    _tag = "power"

    _nodes = [
        XmlAnimatable("base", "real", 1.),
        XmlAnimatable("power", "real", 1.),
        XmlAnimatable("epsilon", "real", 0.000001),
        XmlAnimatable("infinite", "real", 999999.),
    ]


class SifBlineCalcTangent(SifAstComplex):
    _tag = "blinecalctangent"

    _nodes = [
        XmlSifElement("bline", Bline),
        XmlAnimatable("loop", "bool", False),
        XmlAnimatable("amount", "real", 0.5),
        XmlAnimatable("offset", "angle", 0.),
        XmlAnimatable("scale", "real", 1.),
        XmlAnimatable("fixed_length", "bool", False),
        XmlAnimatable("homogeneous", "bool", False),
    ]


class SifBlineCalcVertex(SifAstComplex):
    _tag = "blinecalcvertex"

    _nodes = [
        XmlSifElement("bline", Bline),
        XmlAnimatable("loop", "bool", False),
        XmlAnimatable("amount", "real", 0.5),
        XmlAnimatable("homogeneous", "bool", False),
    ]
