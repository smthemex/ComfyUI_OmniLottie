import math
from xml.dom import minidom

from ... import objects
from ...nvector import NVector
from ...utils import restructure
from . import api, ast


blend_modes = {
    objects.BlendMode.Normal: api.BlendMethod.Composite,
    objects.BlendMode.Multiply: api.BlendMethod.Multiply,
    objects.BlendMode.Screen: api.BlendMethod.Screen,
    objects.BlendMode.Overlay: api.BlendMethod.Overlay,
    objects.BlendMode.Darken: api.BlendMethod.Darken,
    objects.BlendMode.Lighten: api.BlendMethod.Lighten,
    objects.BlendMode.HardLight: api.BlendMethod.HardLight,
    objects.BlendMode.Difference: api.BlendMethod.Difference,
    objects.BlendMode.Hue: api.BlendMethod.Hue,
    objects.BlendMode.Saturation: api.BlendMethod.Saturation,
    objects.BlendMode.Color: api.BlendMethod.Color,
    objects.BlendMode.Luminosity: api.BlendMethod.Luminosity,
    objects.BlendMode.Exclusion: api.BlendMethod.Difference,
    objects.BlendMode.SoftLight: api.BlendMethod.Multiply,
    objects.BlendMode.ColorDodge: api.BlendMethod.Composite,
    objects.BlendMode.ColorBurn: api.BlendMethod.Composite,
}


class SifBuilder(restructure.AbstractBuilder):
    def __init__(self, gamma=1.0):
        """
        @todo Add gamma option to lottie_convert.py
        """
        super().__init__()
        self.canvas = api.Canvas()
        self.canvas.version = "1.2"
        self.canvas.gamma_r = self.canvas.gamma_g = self.canvas.gamma_b = gamma
        self.autoid = objects.base.Index()

    def _on_animation(self, animation: objects.Animation):
        if animation.name:
            self.canvas.name = animation.name
        self.canvas.width = animation.width
        self.canvas.height = animation.height
        self.canvas.xres = animation.width
        self.canvas.yres = animation.height
        self.canvas.view_box = NVector(0, 0, animation.width, animation.height)
        self.canvas.fps = animation.frame_rate
        self.canvas.begin_time = api.FrameTime.frame(animation.in_point)
        self.canvas.end_time = api.FrameTime.frame(animation.out_point)
        self.canvas.antialias = True
        return self.canvas

    def _on_precomp(self, id, dom_parent, layers):
        g = dom_parent.add_layer(api.GroupLayer())
        g.desc = id
        for layer_builder in layers:
            self.process_layer(layer_builder, g)

    def _on_layer(self, layer_builder, dom_parent):
        layer = self.layer_from_lottie(api.GroupLayer, layer_builder.lottie, dom_parent)
        if not layer_builder.lottie.name:
            layer.desc = layer_builder.lottie.__class__.__name__

        bm = getattr(layer_builder.lottie, "blend_mode", None)
        if bm is None:
            bm = objects.BlendMode.Normal
        layer.blend_method = blend_modes[bm]

        layer.time_drilation = getattr(layer_builder.lottie, "stretch", 1) or 1

        in_point = getattr(layer_builder.lottie, "in_point", 0)
        layer.time_offset.value = api.FrameTime.frame(in_point)

        #layer.canvas.end_time = api.FrameTime.frame(out_point)
        return layer

    def layer_from_lottie(self, type, lottie, dom_parent):
        g = dom_parent.add_layer(type())
        if lottie.name:
            g.desc = lottie.name
        g.active = not lottie.hidden
        transf = getattr(lottie, "transform", None)
        if transf:
            self.set_transform(g, transf)

        if isinstance(lottie, objects.NullLayer):
            g.amount.value = 1

        return g

    def _get_scale(self, transform):
        def func(keyframe):
            t = keyframe.time if keyframe else 0
            scale_x, scale_y = transform.scale.get_value(t)[:2]
            scale_x /= 100
            scale_y /= 100
            skew = transform.skew.get_value(t) if transform.skew else 0
            c = math.cos(skew * math.pi / 180)
            if c != 0:
                scale_y *= 1 / c
            return NVector(scale_x, scale_y)
        return func

    def set_transform(self, group, transform):
        composite = group.transformation

        if transform.position:
            composite.offset = self.process_vector(transform.position)

        if transform.scale:
            keyframes = self._merge_keyframes([transform.scale, transform.skew])
            composite.scale = self.process_vector_ext(keyframes, self._get_scale(transform))

        composite.skew_angle = self.process_scalar(transform.skew or objects.Value(0))

        if transform.rotation:
            composite.angle = self.process_scalar(transform.rotation)

        if transform.opacity:
            group.amount = self.process_scalar(transform.opacity, 1/100)

        if transform.anchor_point:
            group.origin = self.process_vector(transform.anchor_point)

        # TODO get z_depth from position
        composite.z_depth = 0

    def process_vector(self, multidim):
        def getter(keyframe):
            if keyframe is None:
                v = multidim.value
            else:
                v = keyframe.start
            return NVector(v[0], v[1])

        return self.process_vector_ext(multidim.keyframes, getter)

    def process_vector_ext(self, kframes, getter):
        if kframes is not None:
            wrap = ast.SifAnimated()
            for i in range(len(kframes)):
                keyframe = kframes[i]
                waypoint = wrap.add_keyframe(getter(keyframe), api.FrameTime.frame(keyframe.time))

                if i > 0:
                    prev = kframes[i-1]
                    if prev.jump:
                        waypoint.before = api.Interpolation.Constant
                    elif prev.in_value and prev.in_value.x < 1:
                        waypoint.before = api.Interpolation.Ease
                    else:
                        waypoint.before = api.Interpolation.Linear
                else:
                    waypoint.before = api.Interpolation.Linear

                if keyframe.jump:
                    waypoint.after = api.Interpolation.Constant
                elif keyframe.out_value and keyframe.out_value.x > 0:
                    waypoint.after = api.Interpolation.Ease
                else:
                    waypoint.after = api.Interpolation.Linear
        else:
            wrap = api.SifValue(getter(None))

        return wrap

    def process_scalar(self, value, mult=None):
        def getter(keyframe):
            if keyframe is None:
                v = value.value
            else:
                v = keyframe.start[0]
            if mult is not None:
                v *= mult
            return v
        return self.process_vector_ext(value.keyframes, getter)

    def _on_shape(self, shape, group, dom_parent):
        layers = []
        if not hasattr(shape, "to_bezier"):
            return []

        if group.stroke:
            sif_shape = self.build_path(api.OutlineLayer, shape.to_bezier(), dom_parent, shape)
            self.apply_group_stroke(sif_shape, group.stroke)
            layers.append(sif_shape)

        if group.fill:
            sif_shape = self.build_path(api.RegionLayer, shape.to_bezier(), dom_parent, shape)
            layers.append(sif_shape)
            self.apply_group_fill(sif_shape, group.fill)

        return layers

    def _merge_keyframes(self, props):
        keyframes = {}
        for prop in props:
            if prop is not None and prop.animated:
                keyframes.update({kf.time: kf for kf in prop.keyframes})
        return list(sorted(keyframes.values(), key=lambda kf: kf.time)) or None

    def apply_origin(self, sif_shape, lottie_shape):
        if hasattr(lottie_shape, "position"):
            sif_shape.origin.value = lottie_shape.position.get_value()
        else:
            sif_shape.origin.value = lottie_shape.bounding_box().center()

    def apply_group_fill(self, sif_shape, fill):
        ## @todo gradients?
        if hasattr(fill, "colors"):
            return

        def getter(keyframe):
            if keyframe is None:
                v = fill.color.value
            else:
                v = keyframe.start
            return self.canvas.make_color(*v)

        sif_shape.color = self.process_vector_ext(fill.color.keyframes, getter)

        def get_op(keyframe):
            if keyframe is None:
                v = fill.opacity.value
            else:
                v = keyframe.start[0]
            v /= 100
            return v

        sif_shape.amount = self.process_vector_ext(fill.opacity.keyframes, get_op)

    def apply_group_stroke(self, sif_shape, stroke):
        self.apply_group_fill(sif_shape, stroke)
        sif_shape.sharp_cusps.value = stroke.line_join == objects.LineJoin.Miter
        round_cap = stroke.line_cap == objects.LineCap.Round
        sif_shape.round_tip_0.value = round_cap
        sif_shape.round_tip_1.value = round_cap
        sif_shape.width = self.process_scalar(stroke.width, 0.5)

    def build_path(self, type, path, dom_parent, lottie_shape):
        layer = self.layer_from_lottie(type, lottie_shape, dom_parent)
        self.apply_origin(layer, lottie_shape)
        startbez = path.shape.get_value()
        layer.bline.loop = startbez.closed
        nverts = len(startbez.vertices)
        for point in range(nverts):
            self.bezier_point(path, point, layer.bline, layer.origin.value)
        return layer

    def bezier_point(self, lottie_path, point_index, sif_parent, offset):
        composite = api.BlinePoint()

        def get_point(keyframe):
            if keyframe is None:
                bezier = lottie_path.shape.value
            else:
                bezier = keyframe.start
            if not bezier:
                #elem.parentNode.parentNode.removeChild(elem.parentNode)
                return
            vert = bezier.vertices[point_index]
            return NVector(vert[0], vert[1]) - offset

        composite.point = self.process_vector_ext(lottie_path.shape.keyframes, get_point)
        composite.split.value = True
        composite.split_radius.value = True
        composite.split_angle.value = True

        def get_tangent(keyframe):
            if keyframe is None:
                bezier = lottie_path.shape.value
            else:
                bezier = keyframe.start
            if not bezier:
                #elem.parentNode.parentNode.removeChild(elem.parentNode)
                return

            inp = getattr(bezier, which_point)[point_index]
            return NVector(inp.x, inp.y) * 3 * mult

        mult = -1
        which_point = "in_tangents"
        composite.t1 = self.process_vector_ext(lottie_path.shape.keyframes, get_tangent)

        mult = 1
        which_point = "out_tangents"
        composite.t2 = self.process_vector_ext(lottie_path.shape.keyframes, get_tangent)
        sif_parent.points.append(composite)

    def _on_shapegroup(self, shape_group, dom_parent):
        if shape_group.empty():
            return

        layer = self.layer_from_lottie(api.GroupLayer, shape_group.lottie, dom_parent)

        self.shapegroup_process_children(shape_group, layer)

    def _modifier_inner_group(self, modifier, shapegroup, dom_parent):
        layer = dom_parent.add_layer(api.GroupLayer())
        self.shapegroup_process_child(modifier.child, shapegroup, layer)
        return layer

    def _on_shape_modifier(self, modifier, shapegroup, dom_parent):
        layer = dom_parent.add_layer(api.GroupLayer())
        if modifier.lottie.name:
            layer.desc = modifier.lottie.name

        inner = self._modifier_inner_group(modifier, shapegroup, layer)
        if isinstance(modifier.lottie, objects.Repeater):
            self.build_repeater(modifier.lottie, inner, layer)

    def _build_repeater_defs(self, shape, name_id):
        dup = api.Duplicate()
        dup.id = name_id
        self.canvas.defs.append(dup)
        self.canvas.register_as(dup, name_id)

        def getter(keyframe):
            if keyframe is None:
                v = shape.copies.value
            else:
                v = keyframe.start[0]

            return v - 1

        setattr(dup, "from", self.process_vector_ext(shape.copies.keyframes, getter))
        dup.to.value = 0
        dup.step.value = -1
        return dup

    def _build_repeater_transform_scale_component(self, shape, name_id, comp, scalecomposite):
        power = ast.SifPower()
        setattr(scalecomposite, "xy"[comp], power)

        def getter(keyframe):
            if keyframe is None:
                v = shape.transform.scale.value
            else:
                v = keyframe.start
            v = v[comp] / 100
            return v

        power.base = self.process_vector_ext(shape.transform.scale.keyframes, getter)

        # HACK work around an issue in Synfig
        power.power = ast.SifAdd()
        power.power.lhs.value = api.ValueReference(name_id)
        power.power.rhs.value = 0.000001

    def _build_repeater_transform(self, shape, inner, name_id):
        offset_id = name_id + "_origin"
        origin = api.ExportedValue(offset_id, self.process_vector(shape.transform.anchor_point), "vector")
        self.canvas.defs.append(origin)
        self.canvas.register_as(origin, offset_id)
        inner.origin = origin

        composite = inner.transformation

        composite.offset = ast.SifAdd()
        composite.offset.rhs.value = api.ValueReference(offset_id)
        composite.offset.lhs = ast.SifScale()
        composite.offset.lhs.scalar.value = api.ValueReference(name_id)
        composite.offset.lhs.link = self.process_vector(shape.transform.position)

        composite.angle = ast.SifScale()
        composite.angle.scalar.value = api.ValueReference(name_id)
        composite.angle.link = self.process_scalar(shape.transform.rotation)

        composite.scale = ast.SifVectorComposite()
        self._build_repeater_transform_scale_component(shape, name_id, 0, composite.scale)
        self._build_repeater_transform_scale_component(shape, name_id, 1, composite.scale)

    def _build_repeater_amount(self, shape, inner, name_id):
        inner.amount = ast.SifSubtract()
        inner.amount.lhs = self.process_scalar(shape.transform.start_opacity, 0.01)

        inner.amount.rhs = ast.SifScale()
        inner.amount.rhs.scalar.value = api.ValueReference(name_id)

        def getter(keyframe):
            if keyframe is None:
                t = 0
                end = shape.transform.end_opacity.value
            else:
                t = keyframe.time
                end = keyframe.start[0]
            start = shape.transform.start_opacity.get_value(t)
            n = shape.copies.get_value(t)
            v = (start - end) / (n - 1) / 100 if n > 0 else 0
            return v
        inner.amount.rhs.link = self.process_vector_ext(shape.transform.end_opacity.keyframes, getter)

    def build_repeater(self, shape, inner, dom_parent):
        name_id = "duplicate_%s" % next(self.autoid)
        dup = self._build_repeater_defs(shape, name_id)
        self._build_repeater_transform(shape, inner, name_id)
        self._build_repeater_amount(shape, inner, name_id)
        inner.desc = "Transformation for " + (dom_parent.desc or "duplicate")

        # duplicate layer
        duplicate = dom_parent.add_layer(api.DuplicateLayer())
        duplicate.index = dup
        duplicate.desc = shape.name


def to_sif(animation):
    builder = SifBuilder()
    builder.process(animation)
    return builder.canvas
