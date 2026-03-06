from xml.dom import minidom
from distutils.util import strtobool

from ....nvector import NVector
from ..sif.frame_time import FrameTime


class _tag:
    def __init__(self, type):
        self.type = type

    def __call__(self, v):
        return self.type(v)


bool_str = _tag(bool)


def str_to_bool(strval):
    return bool(strtobool(strval))


def value_from_xml_string(xml_str, type, registry):
    if type in (bool_str, bool):
        return str_to_bool(xml_str)
    elif type is NVector:
        return NVector(*map(float, xml_str.split()))
    if type is FrameTime:
        return FrameTime.parse_string(xml_str, registry)
    return type(xml_str)


def value_to_xml_string(value, type):
    if type is bool:
        return "1" if value else "0"
    if type is bool_str:
        return "true" if value else "false"
    elif type is NVector:
        return " ".join(map(str, value))
    return str(value)


def value_isinstance(value, type):
    if isinstance(type, _tag):
        type = type.type
    return isinstance(value, type)


def xml_text(node):
    return "".join(
        x.nodeValue
        for x in node.childNodes
        if x.nodeType in {minidom.Node.TEXT_NODE, minidom.Node.CDATA_SECTION_NODE}
    )


def xml_make_text(dom: minidom.Document, tag_name, text):
    e = dom.createElement(tag_name)
    e.appendChild(dom.createTextNode(text))
    return e


def xml_element_matches(ch: minidom.Node, tagname=None):
    if ch.nodeType != minidom.Node.ELEMENT_NODE:
        return False

    if tagname is not None and ch.tagName != tagname:
        return False

    return True


def xml_child_elements(xml: minidom.Node, tagname=None):
    for ch in xml.childNodes:
        if xml_element_matches(ch, tagname):
            yield ch


def xml_first_element_child(xml: minidom.Node, tagname=None, allow_none=False):
    for ch in xml_child_elements(xml, tagname):
        return ch

    if allow_none:
        return None
    raise ValueError("No %s in %s" % (tagname or "child element", getattr(xml, "tagName", "node")))
