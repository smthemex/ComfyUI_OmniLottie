import re
import math
import colorsys
from xml.etree import ElementTree
from ... import objects
from ...nvector import NVector
from .svgdata import color_table, css_atrrs
from .handler import SvgHandler, NameMode
from ...utils.ellipse import Ellipse
from ...utils.transform import TransformMatrix
from ...utils.color import Color

try:
    from ...utils import font
    has_font = True
except ImportError:
    has_font = False

nocolor = {"none"}


class SvgGradientCoord:
    def __init__(self, name, comp, value, percent):
        self.name = name
        self.comp = comp
        self.value = value
        self.percent = percent

    def to_value(self, bbox, default=None):
        if self.value is None:
            return default

        if not self.percent:
            return self.value

        if self.comp == "w":
            return (bbox.x2 - bbox.x1) * self.value

        if self.comp == "x":
            return bbox.x1 + (bbox.x2 - bbox.x1) * self.value

        return bbox.y1 + (bbox.y2 - bbox.y1) * self.value

    def parse(self, attr, default_percent):
        if attr is None:
            return
        if attr.endswith("%"):
            self.percent = True
            self.value = float(attr[:-1])/100
        else:
            self.percent = default_percent
            self.value = float(attr)


class SvgGradient:
    def __init__(self):
        self.colors = []
        self.coords = []
        self.matrix = TransformMatrix()

    def add_color(self, offset, color):
        self.colors.append((offset, color[:4]))

    def to_lottie(self, gradient_shape, shape, time=0):
        """!
        @param gradient_shape   Should be a GradientFill or GradientStroke
        @param shape            ShapeElement to apply the gradient to
        @param time             Time to fetch properties from @p shape

        """
        for off, col in self.colors:
            gradient_shape.colors.add_color(off, col)

    def add_coord(self, value):
        setattr(self, value.name, value)
        self.coords.append(value)

    def parse_attrs(self, attrib):
        relunits = attrib.get("gradientUnits", "") != "userSpaceOnUse"
        for c in self.coords:
            c.parse(attrib.get(c.name, None), relunits)


class SvgLinearGradient(SvgGradient):
    def __init__(self):
        super().__init__()
        self.add_coord(SvgGradientCoord("x1", "x", 0, True))
        self.add_coord(SvgGradientCoord("y1", "y", 0, True))
        self.add_coord(SvgGradientCoord("x2", "x", 1, True))
        self.add_coord(SvgGradientCoord("y2", "y", 0, True))

    def to_lottie(self, gradient_shape, shape, time=0):
        bbox = shape.bounding_box(time)
        gradient_shape.start_point.value = self.matrix.apply(NVector(
            self.x1.to_value(bbox),
            self.y1.to_value(bbox),
        ))
        gradient_shape.end_point.value = self.matrix.apply(NVector(
            self.x2.to_value(bbox),
            self.y2.to_value(bbox),
        ))
        gradient_shape.gradient_type = objects.GradientType.Linear

        super().to_lottie(gradient_shape, shape, time)


class SvgRadialGradient(SvgGradient):
    def __init__(self):
        super().__init__()
        self.add_coord(SvgGradientCoord("cx", "x", 0.5, True))
        self.add_coord(SvgGradientCoord("cy", "y", 0.5, True))
        self.add_coord(SvgGradientCoord("fx", "x", None, True))
        self.add_coord(SvgGradientCoord("fy", "y", None, True))
        self.add_coord(SvgGradientCoord("r", "w", 0.5, True))

    def to_lottie(self, gradient_shape, shape, time=0):
        bbox = shape.bounding_box(time)
        cx = self.cx.to_value(bbox)
        cy = self.cy.to_value(bbox)
        gradient_shape.start_point.value = self.matrix.apply(NVector(cx, cy))
        r = self.r.to_value(bbox)
        gradient_shape.end_point.value = self.matrix.apply(NVector(cx+r, cy))

        fx = self.fx.to_value(bbox, cx) - cx
        fy = self.fy.to_value(bbox, cy) - cy
        gradient_shape.highlight_angle.value = math.atan2(fy, fx) * 180 / math.pi
        gradient_shape.highlight_length.value = math.hypot(fx, fy)

        gradient_shape.gradient_type = objects.GradientType.Radial

        super().to_lottie(gradient_shape, shape, time)


def parse_color(color, current_color=Color(0, 0, 0, 1)):
    """!
    Parses CSS colors

    @see https://www.w3.org/wiki/CSS/Properties/color
    """
    # #fff
    if re.match(r"^#[0-9a-fA-F]{6}$", color):
        return Color(int(color[1:3], 16) / 0xff, int(color[3:5], 16) / 0xff, int(color[5:7], 16) / 0xff, 1)
    # #112233
    if re.match(r"^#[0-9a-fA-F]{3}$", color):
        return Color(int(color[1], 16) / 0xf, int(color[2], 16) / 0xf, int(color[3], 16) / 0xf, 1)
    # rgba(123, 123, 123, 0.7)
    match = re.match(r"^rgba\s*\(\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9.eE]+)\s*\)$", color)
    if match:
        return Color(int(match[1])/255, int(match[2])/255, int(match[3])/255, float(match[4]))
    # rgb(123, 123, 123)
    match = re.match(r"^rgb\s*\(\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\s*\)$", color)
    if match:
        return Color(int(match[1])/255, int(match[2])/255, int(match[3])/255, 1)
    # rgb(60%, 30%, 20%)
    match = re.match(r"^rgb\s*\(\s*([0-9]+)%\s*,\s*([0-9]+)%\s*,\s*([0-9]+)%\s*\)$", color)
    if match:
        return Color(int(match[1])/100, int(match[2])/100, int(match[3])/100, 1)
    # rgba(60%, 30%, 20%, 0.7)
    match = re.match(r"^rgba\s*\(\s*([0-9]+)%\s*,\s*([0-9]+)%\s*,\s*([0-9]+)%\s*,\s*([0-9.eE]+)\s*\)$", color)
    if match:
        return Color(int(match[1])/100, int(match[2])/100, int(match[3])/100, float(match[4]))
    # transparent
    if color == "transparent":
        return Color(0, 0, 0, 0)
    # hsl(60, 30%, 20%)
    match = re.match(r"^hsl\s*\(\s*([0-9]+)\s*,\s*([0-9]+)%\s*,\s*([0-9]+)%\s*\)$", color)
    if match:
        return Color(*(colorsys.hls_to_rgb(int(match[1])/360, int(match[3])/100, int(match[2])/100) + (1,)))
    # hsla(60, 30%, 20%, 0.7)
    match = re.match(r"^hsla\s*\(\s*([0-9]+)\s*,\s*([0-9]+)%\s*,\s*([0-9]+)%\s*,\s*([0-9.eE]+)\s*\)$", color)
    if match:
        return Color(*(colorsys.hls_to_rgb(int(match[1])/360, int(match[3])/100, int(match[2])/100) + (float(match[4]),)))
    # currentColor
    if color in {"currentColor", "inherit"}:
        return current_color.clone()
    # red
    return Color(*color_table[color])


class SvgDefsParent:
    def __init__(self):
        self.items = {}

    def insert(self, dummy, shape):
        self.items[shape.name] = shape

    def __getitem__(self, key):
        return self.items[key]

    def __setitem__(self, key, value):
        self.items[key] = value

    def __contains__(self, key):
        return key in self.items

    @property
    def shapes(self):
        return self


class SvgParser(SvgHandler):
    def __init__(self, name_mode=NameMode.Inkscape):
        self.init_etree()
        self.name_mode = name_mode
        self.current_color = Color(0, 0, 0, 1)
        self.gradients = {}
        self.max_time = 0
        self.defs = SvgDefsParent()
        self.dpi = 96

    def _get_name(self, element, inkscapequal):
        if self.name_mode == NameMode.Inkscape:
            return element.attrib.get(inkscapequal, element.attrib.get("id"))
        return self._get_id(element)

    def _get_id(self, element):
        if self.name_mode != NameMode.NoName:
            return element.attrib.get("id")
        return None

    def parse_etree(self, etree, layer_frames=0, *args, **kwargs):
        animation = objects.Animation(*args, **kwargs)
        self.animation = animation
        self.max_time = 0
        self.document = etree

        svg = etree.getroot()

        self._get_dpi(svg)

        if "width" in svg.attrib and "height" in svg.attrib:
            animation.width = int(round(self._parse_unit(svg.attrib["width"])))
            animation.height = int(round(self._parse_unit(svg.attrib["height"])))
        else:
            _, _, animation.width, animation.height = map(int, svg.attrib["viewBox"].split(" "))
        animation.name = self._get_name(svg, self.qualified("sodipodi", "docname"))

        if layer_frames:
            for frame in svg:
                if self.unqualified(frame.tag) == "g":
                    layer = objects.ShapeLayer()
                    layer.in_point = self.max_time
                    animation.add_layer(layer)
                    self._parseshape_g(frame, layer, {})
                    self.max_time += layer_frames
                    layer.out_point = self.max_time
        else:
            self._svg_to_layer(animation, svg)

        if self.max_time:
            animation.out_point = self.max_time

        self._fix_viewbox(svg, (layer for layer in animation.layers if not layer.parent_index))

        return animation

    def etree_to_layer(self, animation, etree):
        svg = etree.getroot()
        self._get_dpi(svg)
        layer = self._svg_to_layer(animation, svg)
        self._fix_viewbox(svg, [layer])
        return layer

    def _get_dpi(self, svg):
        self.dpi = float(svg.attrib.get(self.qualified("inkscape", "export-xdpi"), self.dpi))

    def _svg_to_layer(self, animation, svg):
        self.animation = animation
        layer = objects.ShapeLayer()
        animation.add_layer(layer)
        self.parse_children(svg, layer, self.parse_style(svg, {}))
        if self.max_time:
            for sublayer in layer.find_all(objects.Layer):
                sublayer.out_point = self.max_time
        return layer

    def _fix_viewbox(self, svg, layers):
        if "viewBox" in svg.attrib:
            vbx, vby, vbw, vbh = map(float, svg.attrib["viewBox"].split())
            if vbx != 0 or vby != 0 or vbw != self.animation.width or vbh != self.animation.height:
                for layer in layers:
                    layer.transform.position.value = -NVector(vbx, vby)
                    layer.transform.scale.value = NVector(self.animation.width / vbw, self.animation.height / vbh) * 100

    def _parse_unit(self, value):
        if not isinstance(value, str):
            return value

        mult = 1
        cmin = 2.54
        if value.endswith("px"):
            value = value[:-2]
        elif value.endswith("vw"):
            value = value[:-2]
            mult = self.animation.width * 0.01
        elif value.endswith("vh"):
            value = value[:-2]
            mult = self.animation.height * 0.01
        elif value.endswith("vmin"):
            value = value[:-4]
            mult = min(self.animation.width, self.animation.height) * 0.01
        elif value.endswith("vmax"):
            value = value[:-4]
            mult = max(self.animation.width, self.animation.height) * 0.01
        elif value.endswith("in"):
            value = value[:-2]
            mult = self.dpi
        elif value.endswith("pc"):
            value = value[:-2]
            mult = self.dpi / 6
        elif value.endswith("pt"):
            value = value[:-2]
            mult = self.dpi / 72
        elif value.endswith("cm"):
            value = value[:-2]
            mult = self.dpi / cmin
        elif value.endswith("mm"):
            value = value[:-2]
            mult = self.dpi / cmin / 10
        elif value.endswith("Q"):
            value = value[:-1]
            mult = self.dpi / cmin / 40

        return float(value) * mult

    def parse_color(self, color):
        return parse_color(color, self.current_color)

    def parse_transform(self, element, group, dest_trans):
        bb = group.bounding_box()
        if not bb.isnull():
            itcx = self.qualified("inkscape", "transform-center-x")
            if itcx in element.attrib:
                cx = float(element.attrib[itcx])
                cy = float(element.attrib[self.qualified("inkscape", "transform-center-y")])
                bbx, bby = bb.center()
                cx += bbx
                cy = bby - cy
                dest_trans.anchor_point.value = NVector(cx, cy)
                dest_trans.position.value = NVector(cx, cy)
            #else:
                #c = bb.center()
                #dest_trans.anchor_point.value = c
                #dest_trans.position.value = c.clone()

        if "transform" not in element.attrib:
            return

        matrix = TransformMatrix()
        read_matrix = False

        for t in re.finditer(r"([a-zA-Z]+)\s*\(([^\)]*)\)", element.attrib["transform"]):
            name = t[1]
            params = list(map(float, t[2].strip().replace(",", " ").split()))
            if name == "translate":
                dest_trans.position.value += NVector(
                    params[0],
                    (params[1] if len(params) > 1 else 0),
                )
            elif name == "scale":
                xfac = params[0]
                dest_trans.scale.value[0] = (dest_trans.scale.value[0] / 100 * xfac) * 100
                yfac = params[1] if len(params) > 1 else xfac
                dest_trans.scale.value[1] = (dest_trans.scale.value[1] / 100 * yfac) * 100
            elif name == "rotate":
                ang = params[0]
                x = y = 0
                if len(params) > 2:
                    x = params[1]
                    y = params[2]
                    ap = NVector(x, y)
                    dap = ap - dest_trans.position.value
                    dest_trans.position.value += dap
                    dest_trans.anchor_point.value += dap
                dest_trans.rotation.value = ang
            else:
                read_matrix = True
                self._apply_transform_element_to_matrix(matrix, t)

        if read_matrix:
            dest_trans.position.value -= dest_trans.anchor_point.value
            dest_trans.anchor_point.value = NVector(0, 0)
            trans = matrix.extract_transform()
            dest_trans.skew_axis.value = math.degrees(trans["skew_axis"])
            dest_trans.skew.value = -math.degrees(trans["skew_angle"])
            dest_trans.position.value += trans["translation"]
            dest_trans.rotation.value -= math.degrees(trans["angle"])
            dest_trans.scale.value *= trans["scale"]

    def parse_style(self, element, parent_style):
        style = parent_style.copy()
        for att in css_atrrs & set(element.attrib.keys()):
            if att in element.attrib:
                style[att] = element.attrib[att]
        if "style" in element.attrib:
            style.update(**dict(map(
                lambda x: map(lambda y: y.strip(), x.split(":")),
                filter(bool, element.attrib["style"].split(";"))
            )))
        return style

    def apply_common_style(self, style, transform):
        opacity = float(style.get("opacity", 1))
        transform.opacity.value = opacity * 100

    def apply_visibility(self, style, object):
        if style.get("display", "inline") == "none" or style.get("visibility", "visible") == "hidden":
            object.hidden = True

    def add_shapes(self, element, shapes, shape_parent, parent_style):
        style = self.parse_style(element, parent_style)

        group = objects.Group()
        self.apply_common_style(style, group.transform)
        self.apply_visibility(style, group)
        group.name = self._get_name(element, self.qualified("inkscape", "label"))

        shape_parent.shapes.insert(0, group)
        for shape in shapes:
            group.add_shape(shape)

        self._add_style_shapes(style, group)

        self.parse_transform(element, group, group.transform)

        return group

    def _add_style_shapes(self, style, group):
        stroke_color = style.get("stroke", "none")
        if stroke_color not in nocolor:
            if stroke_color.startswith("url"):
                stroke = self.get_color_url(stroke_color, objects.GradientStroke, group)
                opacity = 1
            else:
                stroke = objects.Stroke()
                color = self.parse_color(stroke_color)
                stroke.color.value = color
                opacity = color[3]
            group.add_shape(stroke)

            stroke.opacity.value = opacity * float(style.get("stroke-opacity", 1)) * 100

            stroke.width.value = self._parse_unit(style.get("stroke-width", 1))

            linecap = style.get("stroke-linecap")
            if linecap == "round":
                stroke.line_cap = objects.shapes.LineCap.Round
            elif linecap == "butt":
                stroke.line_cap = objects.shapes.LineCap.Butt
            elif linecap == "square":
                stroke.line_cap = objects.shapes.LineCap.Square

            linejoin = style.get("stroke-linejoin")
            if linejoin == "round":
                stroke.line_join = objects.shapes.LineJoin.Round
            elif linejoin == "bevel":
                stroke.line_join = objects.shapes.LineJoin.Bevel
            elif linejoin in {"miter", "arcs", "miter-clip"}:
                stroke.line_join = objects.shapes.LineJoin.Miter

            stroke.miter_limit = self._parse_unit(style.get("stroke-miterlimit", 0))

            dash_array = style.get("stroke-dasharray")
            if dash_array and dash_array != "none":
                values = list(map(self._parse_unit, dash_array.replace(",", " ").split()))
                if len(values) % 2:
                    values += values

                stroke.dashes = []
                for i in range(0, len(values), 2):
                    stroke.dashes.append(objects.StrokeDash(values[i], objects.StrokeDashType.Dash))
                    stroke.dashes.append(objects.StrokeDash(values[i+1], objects.StrokeDashType.Gap))

        fill_color = style.get("fill", "inherit")
        if fill_color not in nocolor:
            if fill_color.startswith("url"):
                fill = self.get_color_url(fill_color, objects.GradientFill, group)
                opacity = 1
            else:
                color = self.parse_color(fill_color)
                fill = objects.Fill(color)
                opacity = color[3]
            opacity *= float(style.get("fill-opacity", 1))
            fill.opacity.value = opacity * 100

            if style.get("fill-rule", "") == "evenodd":
                fill.fill_rule = objects.FillRule.EvenOdd

            group.add_shape(fill)

    def _parseshape_use(self, element, shape_parent, parent_style):
        link = element.attrib[self.qualified("xlink", "href")]
        if link.startswith("#"):
            id = link[1:]
            base_element = self.document.find(".//*[@id='%s']" % id)
            use_style = self.parse_style(element, parent_style)
            used = objects.Group()
            shape_parent.add_shape(used)
            used.name = "use"
            used.transform.position.value.x = float(element.attrib.get("x", 0))
            used.transform.position.value.y = float(element.attrib.get("y", 0))
            self.parse_transform(element, used, used.transform)
            self.parse_shape(base_element, used, use_style)
            return used

    def _parseshape_g(self, element, shape_parent, parent_style):
        group = objects.Group()
        shape_parent.shapes.insert(0, group)
        style = self.parse_style(element, parent_style)
        self.apply_common_style(style, group.transform)
        self.apply_visibility(style, group)
        group.name = self._get_name(element, self.qualified("inkscape", "label"))
        self.parse_children(element, group, style)
        self.parse_transform(element, group, group.transform)
        if group.hidden: # Lottie web doesn't seem to support .hd
            group.transform.opacity.value = 0
        return group

    def _parseshape_ellipse(self, element, shape_parent, parent_style):
        ellipse = objects.Ellipse()
        ellipse.position.value = NVector(
            self._parse_unit(element.attrib["cx"]),
            self._parse_unit(element.attrib["cy"])
        )
        ellipse.size.value = NVector(
            self._parse_unit(element.attrib["rx"]) * 2,
            self._parse_unit(element.attrib["ry"]) * 2
        )
        self.add_shapes(element, [ellipse], shape_parent, parent_style)
        return ellipse

    def _parseshape_anim_ellipse(self, ellipse, element, animations):
        self._merge_animations(element, animations, "cx", "cy", "position")
        self._merge_animations(element, animations, "rx", "ry", "size", lambda x, y: NVector(x, y) * 2)
        self._apply_animations(ellipse.position, "position", animations)
        self._apply_animations(ellipse.size, "size", animations)

    def _parseshape_circle(self, element, shape_parent, parent_style):
        ellipse = objects.Ellipse()
        ellipse.position.value = NVector(
            self._parse_unit(element.attrib["cx"]),
            self._parse_unit(element.attrib["cy"])
        )
        r = self._parse_unit(element.attrib["r"]) * 2
        ellipse.size.value = NVector(r, r)
        self.add_shapes(element, [ellipse], shape_parent, parent_style)
        return ellipse

    def _parseshape_anim_circle(self, ellipse, element, animations):
        self._merge_animations(element, animations, "cx", "cy", "position")
        self._apply_animations(ellipse.position, "position", animations)
        self._apply_animations(ellipse.size, "r", animations, lambda r: NVector(r, r) * 2)

    def _parseshape_rect(self, element, shape_parent, parent_style):
        rect = objects.Rect()
        w = self._parse_unit(element.attrib.get("width", 0))
        h = self._parse_unit(element.attrib.get("height", 0))
        rect.position.value = NVector(
            self._parse_unit(element.attrib.get("x", 0)) + w / 2,
            self._parse_unit(element.attrib.get("y", 0)) + h / 2
        )
        rect.size.value = NVector(w, h)
        rx = self._parse_unit(element.attrib.get("rx", 0))
        ry = self._parse_unit(element.attrib.get("ry", 0))
        rect.rounded.value = (rx + ry) / 2
        self.add_shapes(element, [rect], shape_parent, parent_style)
        return rect

    def _parseshape_anim_rect(self, rect, element, animations):
        self._merge_animations(element, animations, "width", "height", "size", lambda x, y: NVector(x, y))
        self._apply_animations(rect.size, "size", animations)
        self._merge_animations(element, animations, "x", "y", "position")
        self._merge_animations(element, animations, "position", "size", "position", lambda p, s: p + s / 2)
        self._apply_animations(rect.position, "position", animations)
        self._merge_animations(element, animations, "rx", "ry", "rounded", lambda x, y: (x + y) / 2)
        self._apply_animations(rect.rounded, "rounded", animations)

    def _parseshape_line(self, element, shape_parent, parent_style):
        line = objects.Path()
        line.shape.value.add_point(NVector(
            self._parse_unit(element.attrib["x1"]),
            self._parse_unit(element.attrib["y1"])
        ))
        line.shape.value.add_point(NVector(
            self._parse_unit(element.attrib["x2"]),
            self._parse_unit(element.attrib["y2"])
        ))
        return self.add_shapes(element, [line], shape_parent, parent_style)

    def _parseshape_anim_line(self, group, element, animations):
        line = group.shapes[0]
        self._merge_animations(element, animations, "x1", "y1", "p1")
        self._merge_animations(element, animations, "x2", "y2", "p2")
        self._apply_animations(line.vertices[0], "p1", animations)
        self._apply_animations(line.vertices[1], "p2", animations)

    def _handle_poly(self, element):
        line = objects.Path()
        coords = list(map(float, element.attrib["points"].replace(",", " ").split()))
        for i in range(0, len(coords), 2):
            line.shape.value.add_point(coords[i:i+2])
        return line

    def _parseshape_polyline(self, element, shape_parent, parent_style):
        line = self._handle_poly(element)
        return self.add_shapes(element, [line], shape_parent, parent_style)

    def _parseshape_polygon(self, element, shape_parent, parent_style):
        line = self._handle_poly(element)
        line.shape.value.close()
        return self.add_shapes(element, [line], shape_parent, parent_style)

    def _parseshape_path(self, element, shape_parent, parent_style):
        d_parser = PathDParser(element.attrib.get("d", ""))
        d_parser.parse()
        paths = []
        for path in d_parser.paths:
            p = objects.Path()
            p.shape.value = path
            paths.append(p)
        #if len(d_parser.paths) > 1:
            #paths.append(objects.shapes.Merge())
        return self.add_shapes(element, paths, shape_parent, parent_style)

    def parse_children(self, element, shape_parent, parent_style):
        for child in element:
            tag = self.unqualified(child.tag)
            if not self.parse_shape(child, shape_parent, parent_style):
                handler = getattr(self, "_parse_" + tag, None)
                if handler:
                    handler(child)

    def parse_shape(self, element, shape_parent, parent_style):
        handler = getattr(self, "_parseshape_" + self.unqualified(element.tag), None)
        if handler:
            out = handler(element, shape_parent, parent_style)
            self.parse_animations(out, element)
            if element.attrib.get("id"):
                self.defs.items[element.attrib["id"]] = out
            return out
        return None

    def _parse_defs(self, element):
        self.parse_children(element, self.defs, {})

    def _apply_transform_element_to_matrix(self, matrix, t):
        name = t[1]
        params = list(map(float, t[2].strip().replace(",", " ").split()))
        if name == "translate":
            matrix.translate(
                params[0],
                (params[1] if len(params) > 1 else 0),
            )
        elif name == "scale":
            xfac = params[0]
            yfac = params[1] if len(params) > 1 else xfac
            matrix.scale(xfac, yfac)
        elif name == "rotate":
            ang = params[0]
            x = y = 0
            if len(params) > 2:
                x = params[1]
                y = params[2]
                matrix.translate(-x, -y)
                matrix.rotate(math.radians(ang))
                matrix.translate(x, y)
            else:
                matrix.rotate(math.radians(ang))
        elif name == "skewX":
            matrix.skew(math.radians(params[0]), 0)
        elif name == "skewY":
            matrix.skew(0, math.radians(params[0]))
        elif name == "matrix":
            m = TransformMatrix()
            m.a, m.b, m.c, m.d, m.tx, m.ty = params
            matrix *= m

    def _transform_to_matrix(self, transform):
        matrix = TransformMatrix()

        for t in re.finditer(r"([a-zA-Z]+)\s*\(([^\)]*)\)", transform):
            self._apply_transform_element_to_matrix(matrix, t)

        return matrix

    def _gradient(self, element, grad):
        grad.matrix = self._transform_to_matrix(element.attrib.get("gradientTransform", ""))

        id = element.attrib["id"]
        if id in self.gradients:
            grad.colors = self.gradients[id].colors
        grad.parse_attrs(element.attrib)
        href = element.attrib.get(self.qualified("xlink", "href"))
        if href:
            srcid = href.strip("#")
            if srcid in self.gradients:
                src = self.gradients[srcid]
            else:
                src = grad.__class__()
                self.gradients[srcid] = src
            grad.colors = src.colors

        for stop in element.findall("./%s" % self.qualified("svg", "stop")):
            off = float(stop.attrib["offset"].strip("%"))
            if stop.attrib["offset"].endswith("%"):
                off /= 100
            style = self.parse_style(stop, {})
            color = self.parse_color(style["stop-color"])
            if "stop-opacity" in style:
                color[3] = float(style["stop-opacity"])
            grad.add_color(off, color)
        self.gradients[id] = grad

    def _parse_linearGradient(self, element):
        self._gradient(element, SvgLinearGradient())

    def _parse_radialGradient(self, element):
        self._gradient(element, SvgRadialGradient())

    def get_color_url(self, color, gradientclass, shape):
        match = re.match(r"""url\(['"]?#([^)'"]+)['"]?\)""", color)
        if not match:
            return None
        id = match[1]
        if id not in self.gradients:
            return None
        grad = self.gradients[id]
        outgrad = gradientclass()
        grad.to_lottie(outgrad, shape)
        if self.name_mode != NameMode.NoName:
            grad.name = id
        return outgrad

    ## @todo Parse single font property, fallback family etc
    def _parse_text_style(self, style, font_style=None):
        if "font-family" in style:
            font_style.query.family(style["font-family"].strip("'\""))

        if "font-style" in style:
            if style["font-style"] == "oblique":
                font_style.query.custom("slant", 110)
            elif style["font-style"] == "italic":
                font_style.query.custom("slant", 100)

        if "font-weight" in style:
            if style["font-weight"] in {"bold", "bolder"}:
                font_style.query.weight(200)
            elif style["font-weight"] == "lighter":
                font_style.query.weight(50)
            elif style["font-weight"].isdigit():
                font_style.query.css_weight(int(style["font-weight"]))

        if "font-size" in style:
            fz = style["font-size"]
            fz_names = {
                "xx-small": 8,
                "x-small": 16,
                "small": 32,
                "medium": 64,
                "large": 128,
                "x-large": 256,
                "xx-large": 512,
            }
            if fz in fz_names:
                font_style.size = fz_names[fz]
            elif fz == "smaller":
                font_style.size /= 2
            elif fz == "larger":
                font_style.size *= 2
            elif fz.endswith("px"):
                font_style.size = float(fz[:-2])
            elif fz.isnumeric():
                font_style.size = float(fz)

        if "text-align" in style:
            ta = style["text-align"]
            if ta in ("left", "start"):
                font_style.justify = font.TextJustify.Left
            elif ta == "center":
                font_style.justify = font.TextJustify.Center
            elif ta in ("right", "end"):
                font_style.justify = font.TextJustify.Right

    def _parse_text_elem(self, element, style, group, parent_style, font_style):
        self._parse_text_style(style, font_style)

        if "x" in element.attrib or "y" in element.attrib:
            font_style.position = NVector(
                float(element.attrib["x"]),
                float(element.attrib["y"]),
            )

        childpos = NVector(0, font_style.position.y)

        if element.text:
            fs = font.FontShape(element.text, font_style)
            fs.refresh()
            group.add_shape(fs)
            childpos.x = fs.wrapped.next_x

        for child in element:
            if child.tag == self.qualified("svg", "tspan"):
                child_style = font_style.clone()
                child_style.position = childpos.clone()
                fs = self._parseshape_text(child, group, parent_style, child_style)
                childpos.x = fs.next_x
            if child.tail:
                child_style = font_style.clone()
                child_style.position = childpos.clone()
                fs = font.FontShape(child.tail, child_style)
                fs.refresh()
                group.add_shape(fs)
                childpos.x = fs.wrapped.next_x

        group.next_x = childpos.x

    def _parseshape_text(self, element, shape_parent, parent_style, font_style=None):
        group = objects.Group()

        style = self.parse_style(element, parent_style)
        self.apply_common_style(style, group.transform)
        self.apply_visibility(style, group)
        group.name = self._get_id(element)

        if has_font:
            if font_style is None:
                font_style = font.FontStyle("", 64)
            self._parse_text_elem(element, style, group, style, font_style)

        style.setdefault("fill", "none")
        self._add_style_shapes(style, group)

        ## @todo text-anchor when it doesn't match text-align
        #if element.tag == self.qualified("svg", "text"):
            #dx = 0
            #dy = 0

            #ta = style.get("text-anchor", style.get("text-align", ""))
            #if ta == "middle":
                #dx -= group.bounding_box().width / 2
            #elif ta == "end":
                #dx -= group.bounding_box().width

            #if dx or dy:
                #ng = objects.Group()
                #ng.add_shape(group)
                #group.transform.position.value.x += dx
                #group.transform.position.value.y += dy
                #group = ng

        shape_parent.shapes.insert(0, group)
        self.parse_transform(element, group, group.transform)
        return group

    def parse_animations(self, lottie, element):
        animations = {}
        for child in element:
            if self.unqualified(child.tag) == "animate":
                att = child.attrib["attributeName"]

                from_val = child.attrib["from"]
                if att == "d":
                    ## @todo
                    continue
                else:
                    from_val = float(from_val)
                    if "to" in child.attrib:
                        to_val = float(child.attrib["to"])
                    elif "by" in child.attrib:
                        to_val = float(child.attrib["by"]) + from_val

                begin = self.parse_animation_time(child.attrib.get("begin", 0)) or 0
                if "dur" in child.attrib:
                    end = (self.parse_animation_time(child.attrib["dur"]) or 0) + begin
                elif "end" in child.attrib:
                    end = self.parse_animation_time(child.attrib["dur"]) or 0
                else:
                    continue

                if att not in animations:
                    animations[att] = {}
                animations[att][begin] = from_val
                animations[att][end] = to_val
                if self.max_time < end:
                    self.max_time = end

        tag = self.unqualified(element.tag)
        handler = getattr(self, "_parseshape_anim_" + tag, None)
        if handler:
            handler(lottie, element, animations)

    def parse_animation_time(self, value):
        """!
        @see https://developer.mozilla.org/en-US/docs/Web/SVG/Content_type#Clock-value
        """
        if not value:
            return None
        try:
            seconds = 0
            if ":" in value:
                mult = 1
                for elem in reversed(value.split(":")):
                    seconds += float(elem) * mult
                    mult *= 60
            elif value.endswith("s"):
                seconds = float(value[:-1])
            elif value.endswith("ms"):
                seconds = float(value[:-2]) / 1000
            elif value.endswith("min"):
                seconds = float(value[:-3]) * 60
            elif value.endswith("h"):
                seconds = float(value[:-1]) * 60 * 60
            else:
                seconds = float(value)
            return seconds * self.animation.frame_rate
        except ValueError:
            pass
        return None

    def _merge_animations(self, element, animations, val1, val2, dest, merge=NVector):
        if val1 not in animations and val2 not in animations:
            return

        dict1 = list(sorted(animations.pop(val1, {}).items()))
        dict2 = list(sorted(animations.pop(val2, {}).items()))

        x = float(element.attrib[val1])
        y = float(element.attrib[val2])
        values = {}
        while dict1 or dict2:
            if not dict1 or (dict2 and dict1[0][0] > dict2[0][0]):
                t, y = dict2.pop(0)
            elif not dict2 or dict1[0][0] < dict2[0][0]:
                t, x = dict1.pop(0)
            else:
                t, x = dict1.pop(0)
                t, y = dict2.pop(0)

            values[t] = merge(x, y)

        animations[dest] = values

    def _apply_animations(self, animatable, name, animations, transform=lambda v: v):
        if name in animations:
            for t, v in animations[name].items():
                animatable.add_keyframe(t, transform(v))


class PathDParser:
    _re = re.compile("|".join((
        r"[a-zA-Z]",
        r"[-+]?[0-9]*\.?[0-9]*[eE][-+]?[0-9]+",
        r"[-+]?[0-9]*\.?[0-9]+",
    )))

    def __init__(self, d_string):
        self.path = objects.properties.Bezier()
        self.paths = []
        self.p = NVector(0, 0)
        self.la = None
        self.la_type = None
        self.tokens = list(map(self.d_subsplit, self._re.findall(d_string)))
        self.add_p = True
        self.implicit = "M"

    def d_subsplit(self, tok):
        if tok.isalpha():
            return tok
        return float(tok)

    def next_token(self):
        if self.tokens:
            self.la = self.tokens.pop(0)
            if isinstance(self.la, str):
                self.la_type = 0
            else:
                self.la_type = 1
        else:
            self.la = None
        return self.la

    def next_vec(self):
        x = self.next_token()
        y = self.next_token()
        return NVector(x, y)

    def cur_vec(self):
        x = self.la
        y = self.next_token()
        return NVector(x, y)

    def parse(self):
        self.next_token()
        while self.la is not None:
            if self.la_type == 0:
                parser = "_parse_" + self.la
                self.next_token()
                getattr(self, parser)()
            else:
                parser = "_parse_" + self.implicit
                getattr(self, parser)()

    def _push_path(self):
        self.path = objects.properties.Bezier()
        self.add_p = True

    def _parse_M(self):
        if self.la_type != 1:
            self.next_token()
            return
        self.p = self.cur_vec()
        self.implicit = "L"
        if not self.add_p:
            self._push_path()
        self.next_token()

    def _parse_m(self):
        if self.la_type != 1:
            self.next_token()
            return
        self.p += self.cur_vec()
        self.implicit = "l"
        if not self.add_p:
            self._push_path()
        self.next_token()

    def _rpoint(self, point, rel=None):
        return (point - (rel or self.p)) if point is not None else NVector(0, 0)

    def _do_add_p(self, outp=None):
        if self.add_p:
            self.paths.append(self.path)
            self.path.add_point(self.p.clone(), NVector(0, 0), self._rpoint(outp))
            self.add_p = False
        elif outp:
            rp = self.path.vertices[-1]
            self.path.out_tangents[-1] = self._rpoint(outp, rp)

    def _parse_L(self):
        if self.la_type != 1:
            self.next_token()
            return
        self._do_add_p()
        self.p = self.cur_vec()
        self.path.add_point(self.p.clone(), NVector(0, 0), NVector(0, 0))
        self.implicit = "L"
        self.next_token()

    def _parse_l(self):
        if self.la_type != 1:
            self.next_token()
            return
        self._do_add_p()
        self.p += self.cur_vec()
        self.path.add_point(self.p.clone(), NVector(0, 0), NVector(0, 0))
        self.implicit = "l"
        self.next_token()

    def _parse_H(self):
        if self.la_type != 1:
            self.next_token()
            return
        self._do_add_p()
        self.p[0] = self.la
        self.path.add_point(self.p.clone(), NVector(0, 0), NVector(0, 0))
        self.implicit = "H"
        self.next_token()

    def _parse_h(self):
        if self.la_type != 1:
            self.next_token()
            return
        self._do_add_p()
        self.p[0] += self.la
        self.path.add_point(self.p.clone(), NVector(0, 0), NVector(0, 0))
        self.implicit = "h"
        self.next_token()

    def _parse_V(self):
        if self.la_type != 1:
            self.next_token()
            return
        self._do_add_p()
        self.p[1] = self.la
        self.path.add_point(self.p.clone(), NVector(0, 0), NVector(0, 0))
        self.implicit = "V"
        self.next_token()

    def _parse_v(self):
        if self.la_type != 1:
            self.next_token()
            return
        self._do_add_p()
        self.p[1] += self.la
        self.path.add_point(self.p.clone(), NVector(0, 0), NVector(0, 0))
        self.implicit = "v"
        self.next_token()

    def _parse_C(self):
        if self.la_type != 1:
            self.next_token()
            return
        pout = self.cur_vec()
        self._do_add_p(pout)
        pin = self.next_vec()
        self.p = self.next_vec()
        self.path.add_point(
            self.p.clone(),
            (pin - self.p),
            NVector(0, 0)
        )
        self.implicit = "C"
        self.next_token()

    def _parse_c(self):
        if self.la_type != 1:
            self.next_token()
            return
        pout = self.p + self.cur_vec()
        self._do_add_p(pout)
        pin = self.p + self.next_vec()
        self.p += self.next_vec()
        self.path.add_point(
            self.p.clone(),
            (pin - self.p),
            NVector(0, 0)
        )
        self.implicit = "c"
        self.next_token()

    def _parse_S(self):
        if self.la_type != 1:
            self.next_token()
            return
        pin = self.cur_vec()
        self._do_add_p()
        handle = self.path.in_tangents[-1]
        self.path.out_tangents[-1] = (-handle)
        self.p = self.next_vec()
        self.path.add_point(
            self.p.clone(),
            (pin - self.p),
            NVector(0, 0)
        )
        self.implicit = "S"
        self.next_token()

    def _parse_s(self):
        if self.la_type != 1:
            self.next_token()
            return
        pin = self.cur_vec() + self.p
        self._do_add_p()
        handle = self.path.in_tangents[-1]
        self.path.out_tangents[-1] = (-handle)
        self.p += self.next_vec()
        self.path.add_point(
            self.p.clone(),
            (pin - self.p),
            NVector(0, 0)
        )
        self.implicit = "s"
        self.next_token()

    def _parse_Q(self):
        if self.la_type != 1:
            self.next_token()
            return
        self._do_add_p()
        pin = self.cur_vec()
        self.p = self.next_vec()
        self.path.add_point(
            self.p.clone(),
            (pin - self.p),
            NVector(0, 0)
        )
        self.implicit = "Q"
        self.next_token()

    def _parse_q(self):
        if self.la_type != 1:
            self.next_token()
            return
        self._do_add_p()
        pin = self.p + self.cur_vec()
        self.p += self.next_vec()
        self.path.add_point(
            self.p.clone(),
            (pin - self.p),
            NVector(0, 0)
        )
        self.implicit = "q"
        self.next_token()

    def _parse_T(self):
        if self.la_type != 1:
            self.next_token()
            return
        self._do_add_p()
        handle = self.p - self.path.in_tangents[-1]
        self.p = self.cur_vec()
        self.path.add_point(
            self.p.clone(),
            (handle - self.p),
            NVector(0, 0)
        )
        self.implicit = "T"
        self.next_token()

    def _parse_t(self):
        if self.la_type != 1:
            self.next_token()
            return
        self._do_add_p()
        handle = -self.path.in_tangents[-1] + self.p
        self.p += self.cur_vec()
        self.path.add_point(
            self.p.clone(),
            (handle - self.p),
            NVector(0, 0)
        )
        self.implicit = "t"
        self.next_token()

    def _parse_A(self):
        if self.la_type != 1:
            self.next_token()
            return
        r = self.cur_vec()
        xrot = self.next_token()
        large = self.next_token()
        sweep = self.next_token()
        dest = self.next_vec()
        self._do_arc(r[0], r[1], xrot, large, sweep, dest)
        self.implicit = "A"
        self.next_token()

    def _do_arc(self, rx, ry, xrot, large, sweep, dest):
        self._do_add_p()
        if self.p == dest:
            return

        if rx == 0 or ry == 0:
            # Straight line
            self.p = dest
            self.path.add_point(
                self.p.clone(),
                NVector(0, 0),
                NVector(0, 0)
            )
            return

        ellipse, theta1, deltatheta = Ellipse.from_svg_arc(self.p, rx, ry, xrot, large, sweep, dest)
        points = ellipse.to_bezier(theta1, deltatheta)

        self._do_add_p()
        self.path.out_tangents[-1] = points[0].out_tangent
        for point in points[1:-1]:
            self.path.add_point(
                point.vertex,
                point.in_tangent,
                point.out_tangent,
            )
        self.path.add_point(
            dest.clone(),
            points[-1].in_tangent,
            NVector(0, 0),
        )
        self.p = dest

    def _parse_a(self):
        if self.la_type != 1:
            self.next_token()
            return
        r = self.cur_vec()
        xrot = self.next_token()
        large = self.next_token()
        sweep = self.next_token()
        dest = self.p + self.next_vec()
        self._do_arc(r[0], r[1], xrot, large, sweep, dest)
        self.implicit = "a"
        self.next_token()

    def _parse_Z(self):
        if self.path.vertices:
            self.p = self.path.vertices[0].clone()
        self.path.close()
        self._push_path()

    def _parse_z(self):
        self._parse_Z()


def parse_svg_etree(etree, layer_frames=0, *args, **kwargs):
    parser = SvgParser()
    return parser.parse_etree(etree, layer_frames, *args, **kwargs)


def parse_svg_file(file, layer_frames=0, *args, **kwargs):
    return parse_svg_etree(ElementTree.parse(file), layer_frames, *args, **kwargs)
