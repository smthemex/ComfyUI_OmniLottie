from xml.dom import minidom
import enum
from ..sif.core import TypeDescriptor, ObjectRegistry, SifNodeMeta, FrameTime
from ..xml.utils import xml_child_elements, xml_first_element_child


class SifAstNode:
    _subclasses = None
    _tag = None

    @staticmethod
    def from_dom(xml: minidom.Element, param: TypeDescriptor, registry: ObjectRegistry):
        if xml.tagName == param.typename:
            return SifValue.from_dom(xml, param, registry)

        xmltype = xml.getAttribute("type")
        if xmltype != param.typename and xmltype != "weighted_" + param.typename:
            raise ValueError("Invalid type %s (should be %s)" % (xmltype, param.typename))

        return SifAstNode.ast_node_types()[xml.tagName].from_dom(xml, param, registry)

    @staticmethod
    def ast_node_types():
        if SifAstNode._subclasses is None:
            from . import nodes
            SifAstNode._subclasses = {}
            SifAstNode._gather_ast_types(SifAstNode)
        return SifAstNode._subclasses

    @staticmethod
    def _gather_ast_types(cls):
        for subcls in cls.__subclasses__():
            if subcls._tag:
                SifAstNode._subclasses[subcls._tag] = subcls
            SifAstNode._gather_ast_types(subcls)

    def _prepare_to_dom(self, dom: minidom.Document, param: TypeDescriptor):
        element = dom.createElement(self._tag)
        element.setAttribute("type", param.typename)
        return element


class SifValue(SifAstNode):
    def __init__(self, value=None):
        self.value = value

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.value)

    @classmethod
    def from_dom(cls, xml: minidom.Element, param: TypeDescriptor, registry: ObjectRegistry):
        return SifValue(param.value_from_xml_element(xml, registry))

    def to_dom(self, dom: minidom.Document, param: TypeDescriptor):
        return param.value_to_xml_element(self.value, dom)


class Interpolation(enum.Enum):
    Auto = "auto"
    Linear = "linear"
    Clamped = "clamped"
    Ease = "halt"
    Constant = "constant"


class SifKeyframe:
    def __init__(self, value, time: FrameTime, before=Interpolation.Clamped, after=Interpolation.Clamped):
        self.value = value
        self.time = time
        self.before = before
        self.after = after

    @classmethod
    def from_dom(cls, xml: minidom.Element, param: TypeDescriptor, registry: ObjectRegistry):
        return cls(
            param.value_from_xml_element(xml_first_element_child(xml), registry),
            FrameTime.parse_string(xml.getAttribute("time"), registry),
            Interpolation(xml.getAttribute("before")),
            Interpolation(xml.getAttribute("after"))
        )

    def to_dom(self, dom: minidom.Document, param: TypeDescriptor):
        element = dom.createElement("waypoint")
        element.setAttribute("time", str(self.time))
        element.setAttribute("before", self.before.value)
        element.setAttribute("after", self.after.value)
        element.appendChild(param.value_to_xml_element(self.value, dom))
        return element

    def __repr__(self):
        return "<SifKeyframe %s %s>" % (self.time, self.value)


class SifAnimated(SifAstNode):
    _tag = "animated"

    def __init__(self):
        self.keyframes = []

    @classmethod
    def from_dom(cls, xml: minidom.Element, param: TypeDescriptor, registry: ObjectRegistry):
        obj = SifAnimated()
        for waypoint in xml_child_elements(xml, "waypoint"):
            obj.keyframes.append(SifKeyframe.from_dom(waypoint, param, registry))
        return obj

    def to_dom(self, dom: minidom.Document, param: TypeDescriptor):
        element = self._prepare_to_dom(dom, param)
        for kf in self.keyframes:
            element.appendChild(kf.to_dom(dom, param))
        return element

    def add_keyframe(self, *args, **kwargs):
        if not kwargs and len(args) == 1 and isinstance(args[0], SifKeyframe):
            keyframe = args[0]
        else:
            keyframe = SifKeyframe(*args, **kwargs)

        self.keyframes.append(keyframe)
        return keyframe
