import re
import math
from xml.etree import ElementTree

from .handler import SvgHandler, NameMode
from ... import objects
from ...nvector import NVector
from ...utils import restructure
from ...utils.transform import TransformMatrix
try:
    from ...utils import font
    has_font = True
except ImportError:
    has_font = False


class PrecompTime:
    def __init__(self, pcl: objects.PreCompLayer):
        self.pcl = pcl

    def get_time_offset(self, time, lot):
        remap = time
        if self.pcl.time_remapping:
            remapf = self.pcl.time_remapping.get_value(time)
            remap = lot.in_point * (1-remapf) + lot.out_point * remapf

        return remap - self.pcl.start_time


class SvgBuilder(SvgHandler, restructure.AbstractBuilder):
    merge_paths = True
    namestart = (
        r":_A-Za-z\xC0-\xD6\xD8-\xF6\xF8-\u02FF\u0370-\u037D\u037F-\u1FFF" +
        r"\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF" +
        r"\uFDF0-\uFFFD\U00010000-\U000EFFFF"
    )
    namenostart = r"-.0-9\xB7\u0300-\u036F\u203F-\u2040"
    id_re = re.compile("^[%s][%s%s]*$" % (namestart, namenostart, namestart))

    def __init__(self, time=0):
        super().__init__()
        self.svg = ElementTree.Element("svg")
        self.dom = ElementTree.ElementTree(self.svg)
        self.svg.attrib["xmlns"] = self.ns_map["svg"]
        self.ids = set()
        self.idc = 0
        self.name_mode = NameMode.Inkscape
        self.actual_time = time
        self.precomp_times = []
        self._precomps = {}
        self._assets = {}
        self._current_layer = []

    @property
    def time(self):
        time = self.actual_time
        if self.precomp_times:
            for pct in self.precomp_times:
                time = pct.get_time_offset(time, self._current_layer[-1])
        return time

    def gen_id(self, prefix="id"):
        while True:
            self.idc += 1
            id = "%s_%s" % (prefix, self.idc)
            if id not in self.ids:
                break
        self.ids.add(id)
        return id

    def set_clean_id(self, dom, n):
        idn = n.replace(" ", "_")
        if self.id_re.match(idn) and idn not in self.ids:
            self.ids.add(idn)
        else:
            idn = self.gen_id(dom.tag)

        dom.attrib["id"] = idn
        return idn

    def set_id(self, dom, lottieobj, inkscape_qual=None, force=False):
        n = getattr(lottieobj, "name", None)
        if n is None or self.name_mode == NameMode.NoName:
            if force:
                id = self.gen_id(dom.tag)
                dom.attrib["id"] = id
                return id
            return None

        idn = self.set_clean_id(dom, n)
        if inkscape_qual is None:
            inkscape_qual = self.qualified("inkscape", "label")
        if inkscape_qual:
            dom.attrib[inkscape_qual] = n
        return idn

    def _on_animation(self, animation: objects.Animation):
        self.svg.attrib["width"] = str(animation.width)
        self.svg.attrib["height"] = str(animation.height)
        self.svg.attrib["viewBox"] = "0 0 %s %s" % (animation.width, animation.height)
        self.svg.attrib["version"] = "1.1"
        self.set_id(self.svg, animation, self.qualified("sodipodi", "docname"))
        self.defs = ElementTree.SubElement(self.svg, "defs")
        if self.name_mode == NameMode.Inkscape:
            self.svg.attrib[self.qualified("inkscape", "export-xdpi")] = "96"
            self.svg.attrib[self.qualified("inkscape", "export-ydpi")] = "96"
            namedview = ElementTree.SubElement(self.svg, self.qualified("sodipodi", "namedview"))
            namedview.attrib[self.qualified("inkscape", "pagecheckerboard")] = "true"
            namedview.attrib["borderlayer"] = "true"
            namedview.attrib["bordercolor"] = "#666666"
            namedview.attrib["pagecolor"] = "#ffffff"
        self.svg.attrib["style"] = "fill: none; stroke: none"

        self._current_layer = [animation]
        return self.svg

    def _mask_to_def(self, mask):
        svgmask = ElementTree.SubElement(self.defs, "mask")
        mask_id = self.gen_id()
        svgmask.attrib["id"] = mask_id
        svgmask.attrib["mask-type"] = "alpha"
        path = ElementTree.SubElement(svgmask, "path")
        path.attrib["d"] = self._bezier_to_d(mask.shape.get_value(self.time))
        path.attrib["fill"] = "#fff"
        path.attrib["fill-opacity"] = str(mask.opacity.get_value(self.time) / 100)
        return mask_id

    def _matte_source_to_def(self, layer_builder):
        svgmask = ElementTree.SubElement(self.defs, "mask")
        if not layer_builder.matte_id:
            layer_builder.matte_id = self.gen_id()
        svgmask.attrib["id"] = layer_builder.matte_id
        matte_mode = layer_builder.matte_target.lottie.matte_mode

        mask_type = "alpha"
        if matte_mode == objects.MatteMode.Luma:
            mask_type = "luminance"
        svgmask.attrib["mask-type"] = mask_type
        return svgmask

    def _on_masks(self, masks):
        if len(masks) == 1:
            return self._mask_to_def(masks[0])
        mask_ids = list(map(self._mask_to_def, masks))
        mask_def = ElementTree.SubElement(self.defs, "mask")
        mask_id = self.gen_id()
        mask_def.attrib["id"] = mask_id
        g = mask_def
        for mid in mask_ids:
            g = ElementTree.SubElement(g, "g")
            g.attrib["mask"] = "url(#%s)" % mid
        full = ElementTree.SubElement(g, "rect")
        full.attrib["fill"] = "#fff"
        full.attrib["width"] = self.svg.attrib["width"]
        full.attrib["height"] = self.svg.attrib["height"]
        full.attrib["x"] = "0"
        full.attrib["y"] = "0"
        return mask_id

    def _on_layer(self, layer_builder, dom_parent):
        lot = layer_builder.lottie
        self._current_layer.append(lot)

        if not self.precomp_times and (lot.in_point > self.time or lot.out_point < self.time):
            self._current_layer.pop()
            return None

        if layer_builder.matte_target:
            dom_parent = self._matte_source_to_def(layer_builder)

        g = self.group_from_lottie(lot, dom_parent, True)

        if lot.masks:
            g.attrib["mask"] = "url(#%s)" % self._on_masks(lot.masks)
        elif layer_builder.matte_source:
            matte_id = layer_builder.matte_source.matte_id
            if not matte_id:
                matte_id = layer_builder.matte_source.matte_id = self.gen_id()
            g.attrib["mask"] = "url(#%s)" % matte_id

        if isinstance(lot, objects.PreCompLayer):
            self.precomp_times.append(PrecompTime(lot))

            for layer in self._precomps.get(lot.reference_id, []):
                self.process_layer(layer, g)

            self.precomp_times.pop()
        elif isinstance(lot, objects.NullLayer):
            g.attrib["opacity"] = "1"
        elif isinstance(lot, objects.ImageLayer):
            use = ElementTree.SubElement(g, "use")
            use.attrib[self.qualified("xlink", "href")] = "#" + self._assets[lot.image_id]
        elif isinstance(lot, objects.TextLayer):
            self._on_text_layer(g, lot)
        elif isinstance(lot, objects.SolidColorLayer):
            rect = ElementTree.SubElement(g, "rect")
            rect.attrib["width"] = str(lot.width)
            rect.attrib["height"] = str(lot.height)
            rect.attrib["fill"] = lot.color

        if not lot.name:
            g.attrib[self.qualified("inkscape", "label")] = lot.__class__.__name__
        if layer_builder.shapegroup:
            g.attrib["style"] = self.group_to_style(layer_builder.shapegroup)
            self._split_stroke(layer_builder.shapegroup, g, dom_parent)
        #if lot.hidden:
            #g.attrib.setdefault("style", "")
            #g.attrib["style"] += "display: none;"

        return g

    def _on_text_layer(self, g, lot):
        text = ElementTree.SubElement(g, "text")
        doc = lot.data.get_value(self.time)
        if doc:
            text.attrib["font-family"] = doc.font_family
            text.attrib["font-size"] = str(doc.font_size)
            if doc.line_height:
                text.attrib["line-height"] = "%s%%" % doc.line_height
            if doc.justify == objects.text.TextJustify.Left:
                text.attrib["text-align"] = "start"
            elif doc.justify == objects.text.TextJustify.Center:
                text.attrib["text-align"] = "center"
            elif doc.justify == objects.text.TextJustify.Right:
                text.attrib["text-align"] = "end"

            text.attrib["fill"] = color_to_css(doc.color)
            text.text = doc.text

    def _on_layer_end(self, out_layer):
        self._current_layer.pop()

    def _on_precomp(self, id, dom_parent, layers):
        self._precomps[id] = layers

    def _on_asset(self, asset):
        if isinstance(asset, objects.assets.Image):
            img = ElementTree.SubElement(self.defs, "image")
            xmlid = self.set_clean_id(img, asset.id)
            self._assets[asset.id] = xmlid
            if asset.is_embedded:
                url = asset.image
            else:
                url = asset.image_path + asset.image
            img.attrib[self.qualified("xlink", "href")] = url
            img.attrib["width"] = str(asset.width)
            img.attrib["height"] = str(asset.height)

    def _get_value(self, prop, default=NVector(0, 0)):
        if prop:
            v = prop.get_value(self.time)
        else:
            v = default

        if v is None:
            return default
        if isinstance(v, NVector):
            return v.clone()
        return v

    def set_transform(self, dom, transform, auto_orient=False):
        mat = transform.to_matrix(self.time, auto_orient)
        dom.attrib["transform"] = mat.to_css_2d()

        if transform.opacity is not None:
            op = transform.opacity.get_value(self.time)
            if op != 100:
                dom.attrib["opacity"] = str(op/100)

    def _get_group_stroke(self, group):
        style = {}
        if group.stroke:
            if isinstance(group.stroke, objects.GradientStroke):
                style["stroke"] = "url(#%s)" % self.process_gradient(group.stroke)
            else:
                style["stroke"] = color_to_css(group.stroke.color.get_value(self.time))

            style["stroke-opacity"] = group.stroke.opacity.get_value(self.time) / 100
            style["stroke-width"] = group.stroke.width.get_value(self.time)
            if group.stroke.miter_limit is not None:
                style["stroke-miterlimit"] = group.stroke.miter_limit

            if group.stroke.line_cap == objects.LineCap.Round:
                style["stroke-linecap"] = "round"
            elif group.stroke.line_cap == objects.LineCap.Butt:
                style["stroke-linecap"] = "butt"
            elif group.stroke.line_cap == objects.LineCap.Square:
                style["stroke-linecap"] = "square"

            if group.stroke.line_join == objects.LineJoin.Round:
                style["stroke-linejoin"] = "round"
            elif group.stroke.line_join == objects.LineJoin.Bevel:
                style["stroke-linejoin"] = "bevel"
            elif group.stroke.line_join == objects.LineJoin.Miter:
                style["stroke-linejoin"] = "miter"

            if group.stroke.dashes:
                dasharray = []
                last = 0
                last_mode = objects.StrokeDashType.Dash
                for dash in group.stroke.dashes:
                    if last_mode == dash.type:
                        last += dash.length.get_value(self.time)
                    else:
                        if last_mode != objects.StrokeDashType.Offset:
                            dasharray.append(str(last))
                            last = 0
                        last_mode = dash.type
                style["stroke-dasharray"] = " ".join(dasharray)
        return style

    def _style_to_css(self, style):
        return ";".join(map(
            lambda x: ":".join(map(str, x)),
            style.items()
        ))

    def _split_stroke(self, group, fill_layer, out_parent):
        if not group.stroke:# or group.stroke_above:
            return

        style = self._get_group_stroke(group)
        if style.get("stroke-width", 0) <= 0 or style["stroke-opacity"] <= 0:
            return

        if group.stroke_above:
            if fill_layer.attrib.get("style", ""):
                fill_layer.attrib["style"] += ";"
            else:
                fill_layer.attrib["style"] = ""
            fill_layer.attrib["style"] += self._style_to_css(style)
            return fill_layer

        g = ElementTree.Element("g")
        self.set_clean_id(g, "stroke")
        use = ElementTree.Element("use")
        for i, e in enumerate(out_parent):
            if e is fill_layer:
                out_parent.insert(i, g)
                out_parent.remove(fill_layer)
                break
        else:
            return

        g.append(use)
        g.append(fill_layer)

        use.attrib[self.qualified("xlink", "href")] = "#" + fill_layer.attrib["id"]
        use.attrib["style"] = self._style_to_css(style)
        return g

    def group_to_style(self, group):
        style = {}
        if group.fill:
            style["fill-opacity"] = group.fill.opacity.get_value(self.time) / 100
            if isinstance(group.fill, objects.GradientFill):
                style["fill"] = "url(#%s)" % self.process_gradient(group.fill)
            else:
                style["fill"] = color_to_css(group.fill.color.get_value(self.time))

            if group.fill.fill_rule:
                style["fill-rule"] = "evenodd" if group.fill.fill_rule == objects.FillRule.EvenOdd else "nonzero"

        if group.lottie.hidden:
            style["display"] = "none"
        #if group.stroke_above:
            #style.update(self._get_group_stroke(group))

        return self._style_to_css(style)

    def process_gradient(self, gradient):
        spos = gradient.start_point.get_value(self.time)
        epos = gradient.end_point.get_value(self.time)

        if gradient.gradient_type == objects.GradientType.Linear:
            dom = ElementTree.SubElement(self.defs, "linearGradient")
            dom.attrib["x1"] = str(spos[0])
            dom.attrib["y1"] = str(spos[1])
            dom.attrib["x2"] = str(epos[0])
            dom.attrib["y2"] = str(epos[1])
        elif gradient.gradient_type == objects.GradientType.Radial:
            dom = ElementTree.SubElement(self.defs, "radialGradient")
            dom.attrib["cx"] = str(spos[0])
            dom.attrib["cy"] = str(spos[1])
            dom.attrib["r"] = str((epos-spos).length)
            a = gradient.highlight_angle.get_value(self.time) * math.pi / 180
            l = gradient.highlight_length.get_value(self.time)
            dom.attrib["fx"] = str(spos[0] + math.cos(a) * l)
            dom.attrib["fy"] = str(spos[1] + math.sin(a) * l)

        id = self.set_id(dom, gradient, force=True)
        dom.attrib["gradientUnits"] = "userSpaceOnUse"

        for off, color in gradient.colors.stops_at(self.time):
            stop = ElementTree.SubElement(dom, "stop")
            stop.attrib["offset"] = "%s%%" % (off * 100)
            stop.attrib["stop-color"] = color_to_css(color[:3])
            if len(color) > 3:
                stop.attrib["stop-opacity"] = str(color[3])

        return id

    def group_from_lottie(self, lottie, dom_parent, layer):
        g = ElementTree.SubElement(dom_parent, "g")
        if layer and self.name_mode == NameMode.Inkscape:
            g.attrib[self.qualified("inkscape", "groupmode")] = "layer"
        self.set_id(g, lottie, force=True)
        self.set_transform(g, lottie.transform, getattr(lottie, "auto_orient", False))
        return g

    def _on_shapegroup(self, group, dom_parent):
        if group.empty():
            return

        if len(group.children) == 1 and isinstance(group.children[0], restructure.RestructuredPathMerger):
            path = self.build_path(group.paths.paths, dom_parent)
            self.set_id(path, group.paths.paths[0], force=True)
            path.attrib["style"] = self.group_to_style(group)
            self.set_transform(path, group.lottie.transform)
            return self._split_stroke(group, path, dom_parent)

        g = self.group_from_lottie(group.lottie, dom_parent, group.layer)
        g.attrib["style"] = self.group_to_style(group)
        self.shapegroup_process_children(group, g)
        return self._split_stroke(group, g, dom_parent)

    def _on_merged_path(self, shape, shapegroup, out_parent):
        path = self.build_path(shape.paths, out_parent)
        self.set_id(path, shape.paths[0])
        path.attrib["style"] = self.group_to_style(shapegroup)
        #self._split_stroke(shapegroup, path, out_parent)
        return path

    def _on_shape(self, shape, shapegroup, out_parent):
        if isinstance(shape, objects.Rect):
            svgshape = self.build_rect(shape, out_parent)
        elif isinstance(shape, objects.Ellipse):
            svgshape = self.build_ellipse(shape, out_parent)
        elif isinstance(shape, objects.Star):
            svgshape = self.build_path([shape.to_bezier()], out_parent)
        elif isinstance(shape, objects.Path):
            svgshape = self.build_path([shape], out_parent)
        elif has_font and isinstance(shape, font.FontShape):
            svgshape = self.build_text(shape, out_parent)
        else:
            return
        self.set_id(svgshape, shape, force=True)
        if "style" not in svgshape.attrib:
            svgshape.attrib["style"] = ""
        svgshape.attrib["style"] += self.group_to_style(shapegroup)
        #self._split_stroke(shapegroup, svgshape, out_parent)

        if shape.hidden:
            svgshape.attrib["style"] += "display: none;"
        return svgshape

    def build_rect(self, shape, parent):
        rect = ElementTree.SubElement(parent, "rect")
        size = shape.size.get_value(self.time)
        pos = shape.position.get_value(self.time)
        rect.attrib["width"] = str(size[0])
        rect.attrib["height"] = str(size[1])
        rect.attrib["x"] = str(pos[0] - size[0] / 2)
        rect.attrib["y"] = str(pos[1] - size[1] / 2)
        rect.attrib["rx"] = str(shape.rounded.get_value(self.time))
        return rect

    def build_ellipse(self, shape, parent):
        ellipse = ElementTree.SubElement(parent, "ellipse")
        size = shape.size.get_value(self.time)
        pos = shape.position.get_value(self.time)
        ellipse.attrib["rx"] = str(size[0] / 2)
        ellipse.attrib["ry"] = str(size[1] / 2)
        ellipse.attrib["cx"] = str(pos[0])
        ellipse.attrib["cy"] = str(pos[1])
        return ellipse

    def build_path(self, shapes, parent):
        path = ElementTree.SubElement(parent, "path")
        d = ""
        for shape in shapes:
            bez = shape.shape.get_value(self.time)
            if isinstance(bez, list):
                bez = bez[0]
            if not bez.vertices:
                continue
            if d:
                d += "\n"
            d += self._bezier_to_d(bez)

        path.attrib["d"] = d
        return path

    def _bezier_tangent(self, tangent):
        _tangent_threshold = 0.5
        if tangent.length < _tangent_threshold:
            return NVector(0, 0)
        return tangent

    def _bezier_to_d(self, bez):
        d = "M %s,%s " % tuple(bez.vertices[0].components[:2])
        for i in range(1, len(bez.vertices)):
            qfrom = bez.vertices[i-1]
            h1 = self._bezier_tangent(bez.out_tangents[i-1]) + qfrom
            qto = bez.vertices[i]
            h2 = self._bezier_tangent(bez.in_tangents[i]) + qto

            d += "C %s,%s %s,%s %s,%s " % (
                h1[0], h1[1],
                h2[0], h2[1],
                qto[0], qto[1],
            )
        if bez.closed:
            qfrom = bez.vertices[-1]
            h1 = self._bezier_tangent(bez.out_tangents[-1]) + qfrom
            qto = bez.vertices[0]
            h2 = self._bezier_tangent(bez.in_tangents[0]) + qto
            d += "C %s,%s %s,%s %s,%s Z" % (
                h1[0], h1[1],
                h2[0], h2[1],
                qto[0], qto[1],
            )

        return d

    def _on_shape_modifier(self, shape, shapegroup, out_parent):
        if isinstance(shape.lottie, objects.Repeater):
            svgshape = self.build_repeater(shape.lottie, shape.child, shapegroup, out_parent)
        elif isinstance(shape.lottie, objects.RoundedCorners):
            svgshape = self.build_rouded_corners(shape.lottie, shape.child, shapegroup, out_parent)
        elif isinstance(shape.lottie, objects.Trim):
            svgshape = self.build_trim_path(shape.lottie, shape.child, shapegroup, out_parent)
        else:
            return self.shapegroup_process_child(shape.child, shapegroup, out_parent)
        return svgshape

    def build_repeater(self, shape, child, shapegroup, out_parent):
        original = self.shapegroup_process_child(child, shapegroup, out_parent)
        if not original:
            return

        ncopies = int(round(shape.copies.get_value(self.time)))
        if ncopies == 1:
            return

        out_parent.remove(original)

        g = ElementTree.SubElement(out_parent, "g")
        self.set_clean_id(g, "repeater")

        for copy in range(ncopies-1):
            use = ElementTree.SubElement(g, "use")
            use.attrib[self.qualified("xlink", "href")] = "#" + original.attrib["id"]

        orig_wrapper = ElementTree.SubElement(g, "g")
        orig_wrapper.append(original)

        transform = objects.Transform()
        so = shape.transform.start_opacity.get_value(self.time)
        eo = shape.transform.end_opacity.get_value(self.time)
        position = shape.transform.position.get_value(self.time)
        rotation = shape.transform.rotation.get_value(self.time)
        anchor_point = shape.transform.anchor_point.get_value(self.time)
        for i in range(ncopies-1, -1, -1):
            of = i / (ncopies-1)
            transform.opacity.value = so * of + eo * (1 - of)
            self.set_transform(g[i], transform)
            transform.position.value += position
            transform.rotation.value += rotation
            transform.anchor_point.value += anchor_point

        return g

    def build_rouded_corners(self, shape, child, shapegroup, out_parent):
        round_amount = shape.radius.get_value(self.time)
        return self._modifier_process(child, shapegroup, out_parent, self._build_rouded_corners_shape, round_amount)

    def _build_rouded_corners_shape(self, shape, round_amount):
        if not isinstance(shape, objects.Shape):
            return [shape]
        path = shape.to_bezier()
        bezier = path.shape.get_value(self.time).rounded(round_amount)
        path.shape.clear_animation(bezier)
        return [path]

    def build_trim_path(self, shape, child, shapegroup, out_parent):
        start = max(0, min(1, shape.start.get_value(self.time) / 100))
        end = max(0, min(1, shape.end.get_value(self.time) / 100))
        offset = shape.offset.get_value(self.time) / 360 % 1

        multidata = {}
        length = 0

        if shape.multiple == objects.TrimMultipleShapes.Individually:
            for visishape in reversed(list(self._modifier_foreach_shape(child))):
                bez = visishape.to_bezier().shape.get_value(self.time)
                local_length = bez.rough_length()
                multidata[visishape] = (bez, length, local_length)
                length += local_length

        return self._modifier_process(
            child, shapegroup, out_parent, self._build_trim_path_shape,
            start+offset, end+offset, multidata, length
        )

    def _modifier_foreach_shape(self, shape):
        if isinstance(shape, restructure.RestructuredShapeGroup):
            for child in shape.children:
                for chsh in self._modifier_foreach_shape(child):
                    yield chsh
        elif isinstance(shape, restructure.RestructuredPathMerger):
            for p in shape.paths:
                yield p
        elif isinstance(shape, objects.Shape):
            yield shape

    def _modifier_process(self, child, shapegroup, out_parent, callback, *args):
        children = self._modifier_process_child(child, shapegroup, out_parent, callback, *args)
        return [self.shapegroup_process_child(ch, shapegroup, out_parent) for ch in children]

    def _trim_offlocal(self, t, local_start, local_length, total_length):
        gt = (t * total_length - local_start) / local_length
        return max(0, min(1, gt))

    def _build_trim_path_shape(self, shape, start, end, multidata, total_length):
        if not isinstance(shape, objects.Shape):
            return [shape]

        if multidata:
            bezier, local_start, local_length = multidata[shape]
            if end > 1:
                lstart = self._trim_offlocal(start, local_start, local_length, total_length)
                lend = self._trim_offlocal(end-1, local_start, local_length, total_length)
                out = []
                if lstart < 1:
                    out.append(objects.Path(bezier.segment(lstart, 1)))
                if lend > 0:
                    out.append(objects.Path(bezier.segment(0, lend)))
                return out

            lstart = self._trim_offlocal(start, local_start, local_length, total_length)
            lend = self._trim_offlocal(end, local_start, local_length, total_length)
            if lend <= 0 or lstart >= 1:
                return []
            if lstart <= 0 and lend >= 1:
                return [objects.Path(bezier)]
            seg = bezier.segment(lstart, lend)
            return [objects.Path(seg)]

        path = shape.to_bezier()
        bezier = path.shape.get_value(self.time)
        if end > 1:
            bez1 = bezier.segment(start, 1)
            bez2 = bezier.segment(0, end-1)
            return [objects.Path(bez1), objects.Path(bez2)]
        else:
            seg = bezier.segment(start, end)
            return [objects.Path(seg)]

    def _modifier_process_children(self, shapegroup, out_parent, callback, *args):
        children = []
        for shape in shapegroup.children:
            children.extend(self._modifier_process_child(shape, shapegroup, out_parent, callback, *args))
        shapegroup.children = children

    def _modifier_process_child(self, shape, shapegroup, out_parent, callback, *args):
        if isinstance(shape, restructure.RestructuredShapeGroup):
            self._modifier_process_children(shape, out_parent, callback, *args)
            return [shape]
        elif isinstance(shape, restructure.RestructuredPathMerger):
            paths = []
            for p in shape.paths:
                paths.extend(callback(p, *args))
            shape.paths = paths
            if paths:
                return [shape]
            return []
        else:
            return callback(shape, *args)

    def _custom_object_supported(self, shape):
        if has_font and isinstance(shape, font.FontShape):
            return True
        return False

    def build_text(self, shape, parent):
        text = ElementTree.SubElement(parent, "text")
        if "family" in shape.query:
            text.attrib["font-family"] = shape.query["family"]
        if "weight" in shape.query:
            text.attrib["font-weight"] = str(shape.query.weight_to_css())
        slant = int(shape.query.get("slant", 0))
        if slant > 0 and slant < 110:
            text.attrib["font-style"] = "italic"
        elif slant >= 110:
            text.attrib["font-style"] = "oblique"

        text.attrib["font-size"] = str(shape.size)

        text.attrib["white-space"] = "pre"

        pos = shape.style.position
        text.attrib["x"] = str(pos.x)
        text.attrib["y"] = str(pos.y)
        text.text = shape.text

        return text


def color_to_css(color):
    #if len(color) == 4:
        #return ("rgba(%s, %s, %s" % tuple(map(lambda c: int(round(c*255)), color[:3]))) + ", %s)" % color[3]
    return "rgb(%s, %s, %s)" % tuple(map(lambda c: int(round(c*255)), color[:3]))


def to_svg(animation, time):
    builder = SvgBuilder(time)
    builder.process(animation)
    return builder.dom
