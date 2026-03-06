import zipfile
import warnings
from xml.etree import ElementTree

from .base import importer
from ..parsers.svg.importer import SvgParser
from .. import objects

ns = "{%s}" % "http://www.calligra.org/DTD/krita"


def _ns(string):
    return string.format(ns=ns)


def _import_layers(zf, animation, xml_parent, svg_parser, parent):
    for xml_layer in xml_parent.findall(_ns("./{ns}layers/{ns}layer")):
        nodetype = xml_layer.attrib["nodetype"]

        if nodetype == "grouplayer":
            layer = animation.add_layer(objects.NullLayer())
            _import_layers(zf, animation, xml_layer, svg_parser, layer)
        elif nodetype == "shapelayer":
            filename = "%s/layers/%s.shapelayer/content.svg" % (animation.name, xml_layer.attrib["filename"])
            with zf.open(filename) as svg_tree:
                layer = svg_parser.etree_to_layer(animation, ElementTree.parse(svg_tree))
        else:
            warnings.warn("Unsupported krita layer %s" % nodetype)
            continue

        layer.name = xml_layer.attrib["name"]
        if xml_layer.attrib["visible"] == 0:
            layer.transform.opacity.value = 0
        layer.parent = parent


@importer("Krita", ["kra"])
def import_krita(file):
    with zipfile.ZipFile(file) as zf:
        with zf.open("maindoc.xml") as main:
            main_xml = ElementTree.parse(main)

        image = main_xml.find(_ns("./{ns}IMAGE"))
        fps = float(main_xml.find(_ns("./{ns}IMAGE/{ns}animation/{ns}framerate")).attrib["value"])
        framerange = main_xml.find(_ns("./{ns}IMAGE/{ns}animation/{ns}range")).attrib

        animation = objects.Animation(int(framerange["to"]), fps)
        animation.in_point = int(framerange["from"])
        animation.width = int(image.attrib["width"])
        animation.height = int(image.attrib["height"])
        animation.name = image.attrib["name"]

        parser = SvgParser()
        parser.dpi = int(image.attrib["x-res"])

        _import_layers(zf, animation, image, parser, None)

    return animation
