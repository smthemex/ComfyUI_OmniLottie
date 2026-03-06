from .. import objects


class RestructuredLayer:
    def __init__(self, lottie):
        self.lottie = lottie
        self.children_pre = []
        self.children_post = []
        self.structured = False
        self.shapegroup = None
        self.matte_target = False
        self.matte_source = None
        self.matte_id = None

    def add(self, child):
        c = self.children_pre if self.structured else self.children_post
        c.insert(0, child)


class RestructuredShapeGroup:
    def __init__(self, lottie):
        self.lottie = lottie
        self.children = []
        self.fill = None
        self.stroke = None
        self.layer = False
        self.paths = None
        self.stroke_above = False

    def empty(self):
        return not self.children

    def finalize(self, thresh=6):
        for g in self.subgroups:
            if g.layer:
                self.layer = True
                for gg in self.subgroups:
                    gg.layer = True
                return
        nchild = len(self.children)
        self.layer = nchild > thresh and self.lottie.name

    @property
    def subgroups(self):
        for g in self.children:
            if isinstance(g, RestructuredShapeGroup):
                yield g

    def add(self, child):
        self.children.insert(0, child)


class RestructuredModifier:
    def __init__(self, lottie, child):
        self.child = child
        self.lottie = lottie


class RestructuredPathMerger:
    def __init__(self):
        self.paths = []

    def append(self, path):
        self.paths.append(path)


class RestructuredAnimation:
    def __init__(self):
        self.layers = []
        self.precomp = {}


class AbstractBuilder:
    merge_paths = False

    def _on_animation(self, animation):
        raise NotImplementedError()

    def _on_shapegroup(self, shapegroup, out_parent):
        raise NotImplementedError()

    def _on_shape(self, shape, shapegroup, out_parent):
        raise NotImplementedError()

    def _on_merged_path(self, shape, shapegroup, out_parent):
        raise NotImplementedError()

    def _on_shape_modifier(self, shape, shapegroup, out_parent):
        raise NotImplementedError()

    def process(self, animation: objects.Animation):
        out_parent = self._on_animation(animation)

        restructured = self.restructure_animation(animation, self.merge_paths)
        for id, layers in restructured.precomp.items():
            self._on_precomp(id, out_parent, layers)

        for asset in animation.assets or []:
            self._on_asset(asset)

        for layer_builder in restructured.layers:
            self.process_layer(layer_builder, out_parent)

    def _on_layer(self, layer_builder, out_parent):
        raise NotImplementedError()

    def _on_precomp(self, id, out_parent, layers):
        raise NotImplementedError()

    def _on_asset(self, asset):
        pass

    def process_layer(self, layer_builder, out_parent):
        out_layer = self._on_layer(layer_builder, out_parent)

        if out_layer is None:
            return

        for c in layer_builder.children_pre:
            self.process_layer(c, out_layer)

        shapegroup = getattr(layer_builder, "shapegroup", None)
        if shapegroup:
            self.shapegroup_process_children(shapegroup, out_layer)

        for c in layer_builder.children_post:
            self.process_layer(c, out_layer)

        self._on_layer_end(out_layer)

    def _on_layer_end(self, out_layer):
        pass

    def shapegroup_process_child(self, shape, shapegroup, out_parent):
        if isinstance(shape, RestructuredShapeGroup):
            return self._on_shapegroup(shape, out_parent)
        elif isinstance(shape, RestructuredPathMerger):
            return self._on_merged_path(shape, shapegroup, out_parent)
        elif isinstance(shape, RestructuredModifier):
            return self._on_shape_modifier(shape, shapegroup, out_parent)
        else:
            return self._on_shape(shape, shapegroup, out_parent)

    def shapegroup_process_children(self, shapegroup, out_parent):
        for shape in shapegroup.children:
            self.shapegroup_process_child(shape, shapegroup, out_parent)

    def restructure_animation(self, animation, merge_paths):
        restr = RestructuredAnimation()
        restr.layers = self.restructure_layer_list(animation.layers, merge_paths)
        if animation.assets:
            for asset in animation.assets:
                if isinstance(asset, objects.Precomp):
                    restr.precomp[asset.id] = self.restructure_layer_list(asset.layers, merge_paths)
        return restr

    def restructure_layer_list(self, layer_list, merge_paths):
        layers = {}
        flat_layers = []
        prev = None
        for layer in layer_list:
            laybuilder = RestructuredLayer(layer)
            flat_layers.append(laybuilder)

            if layer.index is not None:
                layers[layer.index] = laybuilder

            if isinstance(layer, objects.ShapeLayer):
                laybuilder.shapegroup = RestructuredShapeGroup(layer)
                laybuilder.layer = True
                for shape in layer.shapes:
                    self.restructure_shapegroup(shape, laybuilder.shapegroup, merge_paths)
                laybuilder.shapegroup.finalize()

            if layer.matte_mode not in {None, objects.MatteMode.Normal}:
                laybuilder.matte_source = prev
                if prev:
                    prev.matte_target = laybuilder

            prev = laybuilder

        top_layers = []
        for layer in flat_layers:
            layer.structured = True
            if layer.lottie.parent_index is not None:
                layers[layer.lottie.parent_index].add(layer)
            else:
                top_layers.insert(0, layer)

        return top_layers

    def restructure_shapegroup(self, shape, shape_group, merge_paths):
        if isinstance(shape, (objects.Fill, objects.GradientFill)):
            if not shape_group.fill:
                shape_group.fill = shape
        elif isinstance(shape, objects.BaseStroke):
            if not shape_group.stroke or shape_group.stroke.width.get_value(0) < shape.width.get_value(0):
                shape_group.stroke = shape
                if not shape_group.fill:
                    shape_group.stroke_above = True
        elif isinstance(shape, (objects.Path)):
            if merge_paths:
                if not shape_group.paths:
                    shape_group.paths = RestructuredPathMerger()
                    shape_group.add(shape_group.paths)
                shape_group.paths.append(shape)
            else:
                shape_group.add(shape)
        elif isinstance(shape, (objects.Group)):
            subgroup = RestructuredShapeGroup(shape)
            shape_group.add(subgroup)
            merge_paths = self.merge_paths and not any(isinstance(p, objects.Group) for p in shape.shapes)
            for subshape in shape.shapes:
                self.restructure_shapegroup(subshape, subgroup, merge_paths)
            subgroup.finalize()
        elif isinstance(shape, (objects.Modifier)):
            if shape_group.children:
                ch = shape_group.children.pop(0)
                shape_group.add(RestructuredModifier(shape, ch))
        elif isinstance(shape, (objects.ShapeElement)):
            shape_group.add(shape)
        elif isinstance(shape, (objects.base.CustomObject)):
            if self._custom_object_supported(shape):
                shape_group.add(shape)
            else:
                self.restructure_shapegroup(shape.wrapped, shape_group, self.merge_paths)

    def _custom_object_supported(self, shape):
        return False
