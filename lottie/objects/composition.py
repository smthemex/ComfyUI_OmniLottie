from .base import LottieObject, Index, LottieProp
from .layers import Layer


## @ingroup Lottie
class Composition(LottieObject):
    """!
    Base class for layer holders
    """
    _props = [
        LottieProp("layers", "layers", Layer, True),
    ]

    def __init__(self):
        ## List of Composition Layers
        self.layers = [] # ShapeLayer, SolidLayer, CompLayer, ImageLayer, NullLayer, TextLayer

        self._index_gen = Index()

    def layer(self, index):
        for layer in self.layers:
            if layer.index == index:
                return layer
        raise IndexError("No layer %s" % index)

    def add_layer(self, layer: Layer):
        """!
        @brief Appends a layer to the composition
        @see insert_layer
        """
        return self.insert_layer(len(self.layers), layer)

    @classmethod
    def load(cls, lottiedict):
        obj = super().load(lottiedict)
        obj._fixup()
        return obj

    def _fixup(self):
        for layer in self.layers:
            layer.composition = self

    def insert_layer(self, index, layer: Layer):
        """!
        @brief Inserts a layer to the composition
        @note Layers added first will be rendered on top of later layers
        """
        self.layers.insert(index, layer)
        self.prepare_layer(layer)
        return layer

    def prepare_layer(self, layer: Layer):
        layer.composition = self
        if layer.index is None:
            layer.index = next(self._index_gen)
        self._on_prepare_layer(layer)

    def _on_prepare_layer(self, layer):
        raise NotImplementedError

    def clone(self):
        c = super().clone()
        c._index_gen._i = self._index_gen._i
        return c

    def remove_layer(self, layer: Layer):
        """!
        @brief Removes a layer (and all of its children) from this composition
        @param layer    Layer to be removed
        """
        if layer.composition is not self:
            return

        children = list(layer.children)

        layer.composition = None
        self.layers.remove(layer)

        for c in children:
            self.remove_layer(c)
