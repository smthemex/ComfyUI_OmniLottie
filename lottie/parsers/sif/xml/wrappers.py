from .utils import *
from .core_nodes import XmlDescriptor, ObjectRegistry


class XmlParamSif(XmlDescriptor):
    def __init__(self, name, child_node, default_ctor=None):
        super().__init__(name)
        self.child_node = child_node
        self.default_ctor = default_ctor or child_node

    def from_xml(self, obj, parent: minidom.Element, registry: ObjectRegistry):
        for cn in xml_child_elements(parent, "param"):
            if cn.getAttribute("name") == self.name:
                value = self.child_node.from_dom(xml_first_element_child(cn), registry)
                break
        else:
            value = self.default()

        setattr(obj, self.att_name, value)

    def to_xml(self, obj, parent: minidom.Element, dom: minidom.Document):
        param = parent.appendChild(dom.createElement("param"))
        param.setAttribute("name", self.name)
        param.appendChild(getattr(obj, self.att_name).to_dom(dom))
        return param

    def clean(self, value):
        if not isinstance(value, self.child_node):
            raise ValueError("%s isn't a valid value for %s" % (value, self.name))
        return value

    def default(self):
        return self.default_ctor()


class SifNodeList:
    def __init__(self, type):
        self._items = []
        self._type = type

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, name):
        return self._items[name]

    def __getslice__(self, i, j):
        return self._items[i:j]

    def __setitem__(self, key, value: "Layer"):
        self.validate(value)
        self._items[key] = value

    def append(self, value: "Layer"):
        self.validate(value)
        self._items.append(value)

    def __str__(self):
        return str(self._items)

    def __repr__(self):
        return "<SifNodeList %s>" % self._items

    def validate(self, value):
        if not isinstance(value, self._type):
            raise ValueError("Not a valid object: %s" % value)


class XmlSifElement(XmlDescriptor):
    def __init__(self, name, child_node, nested=True):
        super().__init__(name)
        self.child_node = child_node
        self.nested = nested

    def default(self):
        return self.child_node()

    def from_python(self, value):
        if not isinstance(value, self.child_node):
            raise ValueError("Invalid value for %s: %s" % (self.name, value))
        return value

    def from_xml(self, obj, parent: minidom.Element, registry: ObjectRegistry):
        cn = xml_first_element_child(parent, self.name, allow_none=True)
        if cn:
            if self.nested:
                element = xml_first_element_child(cn)
            else:
                element = cn
            value = self.child_node.from_dom(element, registry)
        else:
            value = self.default()

        setattr(obj, self.att_name, value)

    def to_xml(self, obj, parent: minidom.Element, dom: minidom.Document):
        value = getattr(obj, self.att_name)
        if self.nested:
            node = dom.createElement(self.name)
            parent.appendChild(node)
        else:
            node = parent
        node.appendChild(value.to_dom(dom))


class XmlList(XmlDescriptor):
    def __init__(self, child_node, name=None, wrapper_tag=None, tags=None):
        super().__init__(wrapper_tag or child_node._tag)
        self.child_node = child_node
        self.att_name = self.att_name + "s" if name is None else name
        self.wrapper_tag = wrapper_tag
        if tags is None:
            self.tags = {self.name}
        else:
            self.tags = tags

    def default(self):
        return SifNodeList(self.child_node)

    def clean(self, value):
        return value

    def from_xml(self, obj, parent: minidom.Element, registry: ObjectRegistry):
        values = self.default()
        for cn in xml_child_elements(parent):
            if cn.tagName in self.tags:
                value_node = cn
                if self.wrapper_tag:
                    value_node = xml_first_element_child(cn)
                values.append(self.child_node.from_dom(value_node, registry))

        setattr(obj, self.att_name, values)

    def to_xml(self, obj, parent: minidom.Element, dom: minidom.Document):
        for value in getattr(obj, self.att_name):
            value_node = value.to_dom(dom)
            if self.wrapper_tag:
                wrapper = dom.createElement(self.wrapper_tag)
                wrapper.appendChild(value_node)
                value_node = wrapper
            parent.appendChild(value_node)


class XmlWrapper(XmlDescriptor):
    def __init__(self, name, wrapped: XmlDescriptor):
        super().__init__(name)
        self.wrapped = wrapped

    def to_xml(self, obj, parent: minidom.Element, dom: minidom.Document):
        wrapper = parent.appendChild(dom.createElement(self.name))
        self.wrapped.to_xml(obj, wrapper, dom)

    def from_xml(self, obj, parent: minidom.Element, registry: ObjectRegistry):
        wrapper = xml_first_element_child(parent, self.name, True)
        if wrapper:
            return self.wrapped.from_xml(obj, wrapper, registry)
        return self.default()

    def from_python(self, value):
        return self.wrapped.from_python(value)

    def initialize_object(self, dict, obj):
        return self.wrapped.initialize_object(dict, obj)

    def clean(self, value):
        return self.wrapped.clean(value)

    def default(self):
        return self.wrapped.default()


class XmlWrapperParam(XmlWrapper):
    def to_xml(self, obj, parent: minidom.Element, dom: minidom.Document):
        wrapper = parent.appendChild(dom.createElement("param"))
        wrapper.setAttribute("name", self.name)
        self.wrapped.to_xml(obj, wrapper, dom)

    def from_xml(self, obj, parent: minidom.Element, registry: ObjectRegistry):
        for wrapper in xml_child_elements(parent, "param"):
            if wrapper.getAttribute("name") == self.name:
                return self.wrapped.from_xml(obj, wrapper, registry)
        return self.default()


class XmlBoneReference(XmlDescriptor):
    def __init__(self, name):
        super().__init__(name)

    def to_xml(self, obj, parent: minidom.Element, dom: minidom.Document):
        value = getattr(obj, self.name, None)
        if not value:
            return

        node = parent.appendChild(dom.createElement(self.name))
        value_node = node.appendChild(dom.createElement("bone_valuenode"))
        value_node.setAttribute("type", value.type)
        value_node.setAttribute("guid", value.guid)

        return node

    def from_xml(self, obj, parent: minidom.Element, registry: ObjectRegistry):
        node = xml_first_element_child(parent, self.name, True)
        value = None
        if node:
            value_node = xml_first_element_child(node, "bone_valuenode", True)
            if value_node:
                value = registry.get_object(value_node.getAttribute("guid"))
                if value.type != value_node.getAttribute("type"):
                    raise ValueError("Bone type %s is not %s" % (value.type, value_node.getAttribute("type")))

        setattr(obj, self.att_name, value)

    def from_python(self, value):
        return value
