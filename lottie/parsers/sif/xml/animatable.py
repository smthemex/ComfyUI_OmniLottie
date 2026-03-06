from xml.dom import minidom
import copy
import enum

from .core_nodes import XmlDescriptor, XmlSimpleElement, ValueReference
from .utils import *
from ....nvector import NVector
from ..ast_impl.base import SifAstNode, SifValue
from ..sif.core import ObjectRegistry, TypeDescriptor, noop


class XmlAnimatable(XmlDescriptor):
    def __init__(self, name, typename, default=None, type_wrapper=noop):
        super().__init__(name)
        self.type = TypeDescriptor(typename, default, type_wrapper)

    def from_xml(self, obj, parent: minidom.Element, registry: ObjectRegistry, param: TypeDescriptor = None):
        cn = xml_first_element_child(parent, self.name)
        if cn:
            value = SifAstNode.from_dom(xml_first_element_child(cn), self.type_for(param), registry)
        else:
            value = self.default()

        setattr(obj, self.att_name, value)

    def to_xml(self, obj, parent: minidom.Element, dom: minidom.Document, type: TypeDescriptor = None):
        value = getattr(obj, self.att_name)
        if isinstance(value, SifValue) and isinstance(value.value, ValueReference):
            parent.setAttribute(self.name, ":" + value.value.id)
            return
        param = parent.appendChild(dom.createElement(self.name))
        param.appendChild(value.to_dom(dom, self.type_for(type)))
        return param

    def from_python(self, value):
        if not isinstance(value, SifAstNode):
            raise ValueError("%s isn't a valid value for %s" % (value, self.name))
        return value

    def default(self):
        return SifValue(copy.deepcopy(self.type.default_value))

    def type_for(self, param: TypeDescriptor):
        if param is not None and self.type.typename == "_recurse":
            return param
        return self.type


class XmlParam(XmlDescriptor):
    def __init__(self, name, typename, default=None, type_wrapper=noop, static=False):
        super().__init__(name)
        self.type = TypeDescriptor(typename, default, type_wrapper)
        self.static = static

    def _def(self):
        from ..api import Def
        return Def

    def from_xml(self, obj, parent: minidom.Element, registry: ObjectRegistry):
        for cn in xml_child_elements(parent, "param"):
            if cn.getAttribute("name") == self.name:
                use = cn.getAttribute("use")
                if use:
                    value = registry.get_object(use)
                else:
                    value_node = xml_first_element_child(cn)
                    if self.static:
                        value = self.type.value_from_xml_element(value_node, registry)
                    else:
                        value = SifAstNode.from_dom(value_node, self.type, registry)
                break
        else:
            value = self.default()

        setattr(obj, self.att_name, value)

    def to_xml(self, obj, parent: minidom.Element, dom: minidom.Document):
        param = parent.appendChild(dom.createElement("param"))
        param.setAttribute("name", self.name)
        value = getattr(obj, self.att_name)
        if isinstance(value, self._def()):
            param.setAttribute("use", ":" + value.id)
        else:
            if self.static:
                elem = self.type.value_to_xml_element(value, dom)
            else:
                elem = value.to_dom(dom, self.type)
            param.appendChild(elem)
        return param

    def from_python(self, value):
        if self.static:
            return self.type.type_wrapper(value)
        if not isinstance(value, (SifAstNode, self._def())):
            raise ValueError("%s isn't a valid value for %s" % (value, self.name))
        return value

    def default(self):
        if self.static:
            return copy.deepcopy(self.type.default_value)
        return SifValue(copy.deepcopy(self.type.default_value))


class XmlDynamicListParam(XmlDescriptor):
    _tag = "dynamic_list"

    def __init__(self, name, typename, att_name=None):
        super().__init__(name)
        self.type = TypeDescriptor(typename)
        if att_name is not None:
            self.att_name = att_name

    def to_xml(self, obj, parent: minidom.Element, dom: minidom.Document):
        param = parent.appendChild(dom.createElement("param"))
        param.setAttribute("name", self.name)
        dyl = param.appendChild(dom.createElement(self._tag))
        dyl.setAttribute("type", self.type.typename)
        values = getattr(obj, self.att_name)
        for val in values:
            entry = dyl.appendChild(dom.createElement("entry"))
            entry.appendChild(self._value_to_dom(val, dom))

    def _value_to_dom(self, val, dom: minidom.Document):
        return val.to_dom(dom, self.type)

    def from_xml(self, obj, parent: minidom.Element, registry: ObjectRegistry):
        values = []

        for cn in xml_child_elements(parent, "param"):
            if cn.getAttribute("name") == self.name:
                list = xml_first_element_child(cn)
                if list.getAttribute("type") != self.type.typename:
                    raise ValueError(
                        "Wrong type for %s: got %s instead of %s" %
                        (self.name, self.type.typename, list.getAttribute("type"))
                    )
                for entry in xml_child_elements(list, "entry"):
                    values.append(self._value_from_dom(xml_first_element_child(entry), registry))
                break

        setattr(obj, self.att_name, values)

    def _value_from_dom(self, element, registry):
        return SifAstNode.from_dom(element, self.type, registry)

    def from_python(self, value):
        return value

    def default(self):
        return []


class XmlStaticListParam(XmlDynamicListParam):
    _tag = "static_list"

    def _value_to_dom(self, val, dom: minidom.Document):
        return self.type.value_to_xml_element(val, dom)

    def _value_from_dom(self, element: minidom.Element, registry: ObjectRegistry):
        return self.type.value_from_xml_element(element, registry)
