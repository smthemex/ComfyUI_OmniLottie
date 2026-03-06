from xml.dom import minidom
import enum
from uuid import uuid4

from ....nvector import NVector
from ..xml.utils import xml_text, str_to_bool
from ..xml.utils import xml_child_elements, value_from_xml_string, xml_make_text, value_to_xml_string
from .frame_time import FrameTime


class ObjectRegistry:
    def __init__(self):
        self.registry = {}

    def register_as(self, object, key):
        self.registry[key] = object

    def register(self, object):
        guid = getattr(object, "guid", None)
        if guid is None:
            guid = self.guid()
            object.guid = guid
        self.registry[guid] = object

    @classmethod
    def guid(cls):
        return str(uuid4()).replace("-", "").upper()

    def get_object(self, guid):
        return self.registry[guid]


def noop(x):
    return x


class TypeDescriptor:
    _type_tag_names = {
        "bone_object": "bone"
    }

    def __init__(self, typename, default=None, type_wrapper=noop):
        self.typename = typename
        self.type_wrapper = type_wrapper
        self.default_value = default

    def value_to_xml_element(self, value, dom: minidom.Document):
        element = dom.createElement(self.tag_name)

        if self.typename == "vector":
            element.appendChild(xml_make_text(dom, "x", str(value.x)))
            element.appendChild(xml_make_text(dom, "y", str(value.y)))
            if hasattr(value, "guid"):
                element.setAttribute("guid", value.guid)
        elif self.typename == "color":
            element.appendChild(xml_make_text(dom, "r", str(value[0])))
            element.appendChild(xml_make_text(dom, "g", str(value[1])))
            element.appendChild(xml_make_text(dom, "b", str(value[2])))
            element.appendChild(xml_make_text(dom, "a", str(value[3])))
            if hasattr(value, "guid"):
                element.setAttribute("guid", value.guid)
        elif self.typename == "gradient":
            for point in value:
                element.appendChild(point.to_dom(dom))
        elif self.typename == "bool":
            element.setAttribute("value", "true" if value else "false")
        elif self.typename == "bone_object":
            element.setAttribute("guid", value.guid)
            element.setAttribute("type", self.typename)
        elif self.typename == "string":
            element.appendChild(dom.createTextNode(value))
        else:
            if isinstance(value, enum.Enum):
                value = value.value
            element.setAttribute("value", str(value))

        return element

    @property
    def tag_name(self):
        return self._type_tag_names.get(self.typename, self.typename)

    def value_from_xml_element(self, xml: minidom.Element, registry: ObjectRegistry):
        if xml.tagName != self.tag_name:
            raise ValueError("Wrong value type (%s instead of %s)" % (xml.tagName, self.tag_name))

        guid = xml.getAttribute("guid")
        if guid and guid in registry.registry:
            value = registry.registry[guid]
        elif self.typename == "vector":
            value = NVector(
                float(xml_text(xml.getElementsByTagName("x")[0])),
                float(xml_text(xml.getElementsByTagName("y")[0]))
            )
            if xml.getAttribute("guid"):
                value.guid = xml.getAttribute("guid")
                registry.register(value)
        elif self.typename == "color":
            value = NVector(
                float(xml_text(xml.getElementsByTagName("r")[0])),
                float(xml_text(xml.getElementsByTagName("g")[0])),
                float(xml_text(xml.getElementsByTagName("b")[0])),
                float(xml_text(xml.getElementsByTagName("a")[0]))
            )
        elif self.typename == "gradient":
            value = [
                GradientPoint.from_dom(sub, registry)
                for sub in xml_child_elements(xml, GradientPoint.type.typename)
            ]
        elif self.typename == "real" or self.typename == "angle":
            value = float(xml.getAttribute("value"))
        elif self.typename == "integer":
            value = int(xml.getAttribute("value"))
        elif self.typename == "time":
            value = FrameTime.parse_string(xml.getAttribute("value"), registry)
        elif self.typename == "bool":
            value = str_to_bool(xml.getAttribute("value"))
        elif self.typename == "string":
            return xml_text(xml)
        elif self.typename == "bone_object":
            # Already done above but this forces the guid to be present
            return registry.get_object(xml.getAttribute("guid"))
        else:
            raise ValueError("Unsupported type %s" % self.typename)

        return self.type_wrapper(value)


class GradientPoint:
    type = TypeDescriptor("color")

    def __init__(self, pos: float, color: NVector):
        self.pos = pos
        self.color = color

    def to_dom(self, dom: minidom.Document):
        element = self.type.value_to_xml_element(self.color, dom)
        element.setAttribute("pos", value_to_xml_string(self.pos, float))
        return element

    @classmethod
    def from_dom(cls, xml: minidom.Element, registry: ObjectRegistry):
        return GradientPoint(
            value_from_xml_string(xml.getAttribute("pos"), float, registry),
            cls.type.value_from_xml_element(xml, registry)
        )

    def __repr__(self):
        return "<GradientPoint %s %s>" % (self.pos, self.color)


class SifNodeMeta(type):
    def __new__(cls, name, bases, attr):
        props = []
        for base in bases:
            if type(base) == cls:
                props += base._nodes
        attr["_nodes"] = props + attr.get("_nodes", [])
        if "_tag" not in attr:
            attr["_tag"] = name.lower()
        attr["_nodemap"] = {
            node.att_name: node
            for node in attr["_nodes"]
        }
        return super().__new__(cls, name, bases, attr)
