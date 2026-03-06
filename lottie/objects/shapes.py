import math
from .base import LottieObject, LottieProp, LottieEnum, NVector
from .properties import Value, MultiDimensional, GradientColors, ShapeProperty, Bezier, ColorValue
from .color import Color
from .helpers import Transform


class BoundingBox:
    """!
    Shape bounding box
    """
    def __init__(self, x1=None, y1=None, x2=None, y2=None):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def include(self, x, y):
        """!
        Expands the box to include the point at x, y
        """
        if x is not None:
            if self.x1 is None or self.x1 > x:
                self.x1 = x
            if self.x2 is None or self.x2 < x:
                self.x2 = x
        if y is not None:
            if self.y1 is None or self.y1 > y:
                self.y1 = y
            if self.y2 is None or self.y2 < y:
                self.y2 = y

    def expand(self, other):
        """!
        Expands the bounding box to include another bounding box
        """
        self.include(other.x1, other.y1)
        self.include(other.x2, other.y2)

    def center(self):
        """!
        Center point of the bounding box
        """
        return NVector((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def isnull(self):
        """!
        Whether the box is default-initialized
        """
        return self.x1 is None or self.y2 is None

    def __repr__(self):
        return "<BoundingBox [%s, %s] - [%s, %s]>" % (self.x1, self.y1, self.x2, self.y2)

    @property
    def width(self):
        if self.isnull():
            return 0
        return self.x2 - self.x1

    @property
    def height(self):
        if self.isnull():
            return 0
        return self.y2 - self.y1

    def size(self):
        return NVector(self.width, self.height)


## @ingroup Lottie
class ShapeElement(LottieObject):
    """!
    Base class for all elements of ShapeLayer and Group
    """
    _props = [
        #LottieProp("match_name", "mn", str, False),
        LottieProp("hidden", "hd", bool, False),
        LottieProp("name", "nm", str, False),
        LottieProp("type", "ty", str, False),
        LottieProp("property_index", "cix", int, False),
        LottieProp("bm", "bm", int, False),
    ]
    ## %Shape type.
    type = None
    _shape_classses = None

    def __init__(self):
        # After Effect's Match Name. Used for expressions.
        #self.match_name = ""

        ## After Effect's Name. Used for expressions.
        self.name = None
        ## Property index
        self.property_index = None
        ## Hide element
        self.hidden = None
        ## @todo figure out?
        self.bm = None

    def bounding_box(self, time=0):
        """!
        Bounding box of the shape element at the given time
        """
        return BoundingBox()

    @classmethod
    def _load_get_class(cls, lottiedict):
        if not ShapeElement._shape_classses:
            ShapeElement._shape_classses = {}
            ShapeElement._load_sub(ShapeElement._shape_classses)
        return ShapeElement._shape_classses[lottiedict["ty"]]

    @classmethod
    def _load_sub(cls, dict):
        for sc in cls.__subclasses__():
            if sc.type:
                dict[sc.type] = sc
            sc._load_sub(dict)

    def __str__(self):
        return self.name or super().__str__()


## @ingroup Lottie
class Shape(ShapeElement):
    """!
    Drawable shape
    """
    _props = [
        LottieProp("direction", "d", float, False),
    ]

    def __init__(self):
        ShapeElement.__init__(self)
        ## After Effect's Direction. Direction how the shape is drawn. Used for trim path for example.
        self.direction = 1

    def to_bezier(self):
        """!
        Returns a Path corresponding to this Shape
        """
        raise NotImplementedError()


## @ingroup Lottie
class Rect(Shape):
    """!
    A simple rectangle shape
    """
    _props = [
        LottieProp("position", "p", MultiDimensional, False),
        LottieProp("size", "s", MultiDimensional, False),
        LottieProp("rounded", "r", Value, False),
    ]
    ## %Shape type.
    type = "rc"

    def __init__(self, pos=None, size=None, rounded=0):
        Shape.__init__(self)
        ## Rect's position
        self.position = MultiDimensional(pos or NVector(0, 0))
        ## Rect's size
        self.size = MultiDimensional(size or NVector(0, 0))
        ## Rect's rounded corners
        self.rounded = Value(rounded)

    def bounding_box(self, time=0):
        pos = self.position.get_value(time)
        sz = self.size.get_value(time)

        return BoundingBox(
            pos[0] - sz[0]/2,
            pos[1] - sz[1]/2,
            pos[0] + sz[0]/2,
            pos[1] + sz[1]/2,
        )

    def to_bezier(self):
        """!
        Returns a Shape corresponding to this rect
        """
        shape = Path()
        kft = set()
        if self.position.animated:
            kft |= set(kf.time for kf in self.position.keyframes)
        if self.size.animated:
            kft |= set(kf.time for kf in self.size.keyframes)
        if self.rounded.animated:
            kft |= set(kf.time for kf in self.rounded.keyframes)
        if not kft:
            shape.shape.value = self._bezier_t(0)
        else:
            for time in sorted(kft):
                shape.shape.add_keyframe(time, self._bezier_t(time))
        return shape

    def _bezier_t(self, time):
        bezier = Bezier()
        bb = self.bounding_box(time)
        rounded = self.rounded.get_value(time)
        tl = NVector(bb.x1, bb.y1)
        tr = NVector(bb.x2, bb.y1)
        br = NVector(bb.x2, bb.y2)
        bl = NVector(bb.x1, bb.y2)

        if not self.rounded.animated and rounded == 0:
            bezier.add_point(tl)
            bezier.add_point(tr)
            bezier.add_point(br)
            bezier.add_point(bl)
        else:
            hh = NVector(rounded/2, 0)
            vh = NVector(0, rounded/2)
            hd = NVector(rounded, 0)
            vd = NVector(0, rounded)
            bezier.add_point(tl+vd, outp=-vh)
            bezier.add_point(tl+hd, -hh)
            bezier.add_point(tr-hd, outp=hh)
            bezier.add_point(tr+vd, -vh)
            bezier.add_point(br-vd, outp=vh)
            bezier.add_point(br-hd, hh)
            bezier.add_point(bl+hd, outp=-hh)
            bezier.add_point(bl-vd, vh)

        bezier.close()
        return bezier


## @ingroup Lottie
class StarType(LottieEnum):
    Star = 1
    Polygon = 2


## @ingroup Lottie
class Star(Shape):
    """!
    Star shape
    """
    _props = [
        LottieProp("position", "p", MultiDimensional, False),
        LottieProp("inner_radius", "ir", Value, False),
        LottieProp("inner_roundness", "is", Value, False),
        LottieProp("outer_radius", "or", Value, False),
        LottieProp("outer_roundness", "os", Value, False),
        LottieProp("rotation", "r", Value, False),
        LottieProp("points", "pt", Value, False),
        LottieProp("star_type", "sy", StarType, False),
    ]
    ## %Shape type.
    type = "sr"

    def __init__(self):
        Shape.__init__(self)
        ## Star's position
        self.position = MultiDimensional(NVector(0, 0))
        ## Star's inner radius. (Star only)
        self.inner_radius = Value()
        ## Star's inner roundness. (Star only)
        self.inner_roundness = Value()
        ## Star's outer radius.
        self.outer_radius = Value()
        ## Star's outer roundness.
        self.outer_roundness = Value()
        ## Star's rotation.
        self.rotation = Value()
        ## Star's number of points.
        self.points = Value(5)
        ## Star's type. Polygon or Star.
        self.star_type = StarType.Star

    def bounding_box(self, time=0):
        pos = self.position.get_value(time)
        r = self.outer_radius.get_value(time)

        return BoundingBox(
            pos[0] - r,
            pos[1] - r,
            pos[0] + r,
            pos[1] + r,
        )

    def to_bezier(self):
        """!
        Returns a Shape corresponding to this star
        """
        shape = Path()
        kft = set()
        if self.position.animated:
            kft |= set(kf.time for kf in self.position.keyframes)
        if self.inner_radius.animated:
            kft |= set(kf.time for kf in self.inner_radius.keyframes)
        if self.inner_roundness.animated:
            kft |= set(kf.time for kf in self.inner_roundness.keyframes)
        if self.points.animated:
            kft |= set(kf.time for kf in self.points.keyframes)
        if self.rotation.animated:
            kft |= set(kf.time for kf in self.rotation.keyframes)
        # TODO inner_roundness / outer_roundness
        if not kft:
            shape.shape.value = self._bezier_t(0)
        else:
            for time in sorted(kft):
                shape.shape.add_keyframe(time, self._bezier_t(time))
        return shape

    def _bezier_t(self, time):
        bezier = Bezier()
        pos = self.position.get_value(time)
        r1 = self.inner_radius.get_value(time)
        r2 = self.outer_radius.get_value(time)
        rot = -(self.rotation.get_value(time)) * math.pi / 180 + math.pi
        p = self.points.get_value(time)
        halfd = -math.pi / p

        for i in range(int(p)):
            main_angle = rot + i * halfd * 2
            dx = r2 * math.sin(main_angle)
            dy = r2 * math.cos(main_angle)
            bezier.add_point(NVector(pos.x + dx, pos.y + dy))

            if self.star_type == StarType.Star:
                dx = r1 * math.sin(main_angle+halfd)
                dy = r1 * math.cos(main_angle+halfd)
                bezier.add_point(NVector(pos.x + dx, pos.y + dy))

        bezier.close()
        return bezier


## @ingroup Lottie
class Ellipse(Shape):
    """!
    Ellipse shape
    """
    _props = [
        LottieProp("position", "p", MultiDimensional, False),
        LottieProp("size", "s", MultiDimensional, False),
    ]
    ## %Shape type.
    type = "el"

    def __init__(self, position=None, size=None):
        Shape.__init__(self)
        ## Ellipse's position
        self.position = MultiDimensional(position or NVector(0, 0))
        ## Ellipse's size
        self.size = MultiDimensional(size or NVector(0, 0))

    def bounding_box(self, time=0):
        pos = self.position.get_value(time)
        sz = self.size.get_value(time)

        return BoundingBox(
            pos[0] - sz[0]/2,
            pos[1] - sz[1]/2,
            pos[0] + sz[0]/2,
            pos[1] + sz[1]/2,
        )

    def to_bezier(self):
        """!
        Returns a Shape corresponding to this ellipse
        """
        shape = Path()
        kft = set()
        if self.position.animated:
            kft |= set(kf.time for kf in self.position.keyframes)
        if self.size.animated:
            kft |= set(kf.time for kf in self.size.keyframes)
        if not kft:
            shape.shape.value = self._bezier_t(0)
        else:
            for time in sorted(kft):
                shape.shape.add_keyframe(time, self._bezier_t(time))
        return shape

    def _bezier_t(self, time):
        from ..utils.ellipse import Ellipse as EllipseConverter

        bezier = Bezier()
        position = self.position.get_value(time)
        radii = self.size.get_value(time) / 2

        el = EllipseConverter(position, radii, 0)
        points = el.to_bezier(0, math.pi*2)
        for point in points[1:]:
            bezier.add_point(point.vertex, point.in_tangent, point.out_tangent)

        bezier.close()
        return bezier


## @ingroup Lottie
class Path(Shape):
    """!
    Animatable Bezier curve
    """
    _props = [
        LottieProp("shape", "ks", ShapeProperty, False),
        LottieProp("index", "ind", int, False),
    ]
    ## %Shape type.
    type = "sh"

    def __init__(self, bezier=None):
        Shape.__init__(self)
        ## Shape's vertices
        self.shape = ShapeProperty(bezier or Bezier())
        ## @todo Index?
        self.index = None

    def bounding_box(self, time=0):
        pos = self.shape.get_value(time)

        bb = BoundingBox()
        for v in pos.vertices:
            bb.include(*v)

        return bb

    def to_bezier(self):
        return self.clone()


## @ingroup Lottie
class Group(ShapeElement):
    """!
    ShapeElement that can contain other shapes
    @note Shapes inside the same group will create "holes" in other shapes
    """
    _props = [
        LottieProp("number_of_properties", "np", float, False),
        LottieProp("shapes", "it", ShapeElement, True),
    ]
    ## %Shape type.
    type = "gr"

    def __init__(self):
        ShapeElement.__init__(self)
        ## Group number of properties. Used for expressions.
        self.number_of_properties = None
        ## Group list of items
        self.shapes = [TransformShape()]

    @property
    def transform(self):
        return self.shapes[-1]

    def bounding_box(self, time=0):
        bb = BoundingBox()
        for v in self.shapes:
            bb.expand(v.bounding_box(time))

        if not bb.isnull():
            mat = self.transform.to_matrix(time)
            points = [
                mat.apply(NVector(bb.x1, bb.y1)),
                mat.apply(NVector(bb.x1, bb.y2)),
                mat.apply(NVector(bb.x2, bb.y2)),
                mat.apply(NVector(bb.x2, bb.y1)),
            ]
            x1 = min(p.x for p in points)
            x2 = max(p.x for p in points)
            y1 = min(p.y for p in points)
            y2 = max(p.y for p in points)
            return BoundingBox(x1, y1, x2, y2)
        return bb

    def add_shape(self, shape):
        self.shapes.insert(-1, shape)
        return shape

    def insert_shape(self, index, shape):
        self.shapes.insert(index, shape)
        return shape

    @classmethod
    def load(cls, lottiedict):
        object = ShapeElement.load(lottiedict)

        shapes = []
        transform = None
        for obj in object.shapes:
            if isinstance(obj, TransformShape):
                if not transform:
                    transform = obj
            else:
                shapes.append(obj)

        object.shapes = shapes
        object.shapes.append(transform)
        return object


## @ingroup Lottie
class FillRule(LottieEnum):
    NonZero = 1
    EvenOdd = 2


## @ingroup Lottie
class Fill(ShapeElement):
    """!
    Solid fill color
    """
    _props = [
        LottieProp("opacity", "o", Value, False),
        LottieProp("color", "c", ColorValue, False),
        LottieProp("fill_rule", "r", FillRule, False),
    ]
    ## %Shape type.
    type = "fl"

    def __init__(self, color=None):
        ShapeElement.__init__(self)
        ## Fill Opacity
        self.opacity = Value(100)
        ## Fill Color
        self.color = ColorValue(color or Color(1, 1, 1))
        ## Fill rule
        self.fill_rule = None


## @ingroup Lottie
class GradientType(LottieEnum):
    Linear = 1
    Radial = 2


## @ingroup Lottie
class Gradient(LottieObject):
    _props = [
        LottieProp("start_point", "s", MultiDimensional, False),
        LottieProp("end_point", "e", MultiDimensional, False),
        LottieProp("gradient_type", "t", GradientType, False),
        LottieProp("highlight_length", "h", Value, False),
        LottieProp("highlight_angle", "a", Value, False),
        LottieProp("colors", "g", GradientColors, False),
    ]

    def __init__(self, colors=[]):
        ## Fill Opacity
        self.opacity = Value(100)
        ## Gradient Start Point
        self.start_point = MultiDimensional(NVector(0, 0))
        ## Gradient End Point
        self.end_point = MultiDimensional(NVector(0, 0))
        ## Gradient Type
        self.gradient_type = GradientType.Linear
        ## Gradient Highlight Length. Only if type is Radial
        self.highlight_length = Value()
        ## Highlight Angle. Only if type is Radial
        self.highlight_angle = Value()
        ## Gradient Colors
        self.colors = GradientColors(colors)


## @ingroup Lottie
class GradientFill(ShapeElement, Gradient):
    """!
    Gradient fill
    """
    _props = [
        LottieProp("opacity", "o", Value, False),
        LottieProp("fill_rule", "r", FillRule, False),
    ]
    ## %Shape type.
    type = "gf"

    def __init__(self, colors=[]):
        ShapeElement.__init__(self)
        Gradient.__init__(self, colors)
        ## Fill Opacity
        self.opacity = Value(100)
        ## Fill rule
        self.fill_rule = None


## @ingroup Lottie
class LineJoin(LottieEnum):
    Miter = 1
    Round = 2
    Bevel = 3


## @ingroup Lottie
class LineCap(LottieEnum):
    Butt = 1
    Round = 2
    Square = 3


## @ingroup Lottie
class StrokeDashType(LottieEnum):
    Dash = "d"
    Gap = "g"
    Offset = "o"


## @ingroup Lottie
class StrokeDash(LottieObject):
    _props = [
        LottieProp("name", "nm", str, False),
        LottieProp("type", "n", StrokeDashType, False),
        LottieProp("length", "v", Value, False),
    ]

    def __init__(self, length=0, type=StrokeDashType.Dash):
        self.name = type.name.lower()
        self.type = type
        self.length = Value(length)

    def __str__(self):
        return self.name or super().__str__()


## @ingroup Lottie
class BaseStroke(LottieObject):
    _props = [
        LottieProp("line_cap", "lc", LineCap, False),
        LottieProp("line_join", "lj", LineJoin, False),
        LottieProp("miter_limit", "ml", float, False),
        LottieProp("opacity", "o", Value, False),
        LottieProp("width", "w", Value, False),
        LottieProp("dashes", "d", StrokeDash, True),
    ]

    def __init__(self, width=1):
        ## Stroke Line Cap
        self.line_cap = LineCap.Round
        ## Stroke Line Join
        self.line_join = LineJoin.Round
        ## Stroke Miter Limit. Only if Line Join is set to Miter.
        self.miter_limit = 0
        ## Stroke Opacity
        self.opacity = Value(100)
        ## Stroke Width
        self.width = Value(width)
        ## Dashes
        self.dashes = None


## @ingroup Lottie
class Stroke(ShapeElement, BaseStroke):
    """!
    Solid stroke
    """
    _props = [
        LottieProp("color", "c", MultiDimensional, False),
    ]
    ## %Shape type.
    type = "st"

    def __init__(self, color=None, width=1):
        ShapeElement.__init__(self)
        BaseStroke.__init__(self, width)
        ## Stroke Color
        self.color = ColorValue(color or Color(0, 0, 0))


## @ingroup Lottie
class GradientStroke(ShapeElement, BaseStroke, Gradient):
    """!
    Gradient stroke
    """
    ## %Shape type.
    type = "gs"

    def __init__(self, stroke_width=1):
        ShapeElement.__init__(self)
        BaseStroke.__init__(self, stroke_width)
        Gradient.__init__(self)

    def bounding_box(self, time=0):
        return BoundingBox()


## @ingroup Lottie
class TransformShape(ShapeElement, Transform):
    """!
    Group transform
    """
    ## %Shape type.
    type = "tr"

    def __init__(self):
        ShapeElement.__init__(self)
        Transform.__init__(self)
        self.anchor_point = MultiDimensional(NVector(0, 0))


## @ingroup Lottie
class Composite(LottieEnum):
    Above = 1
    Below = 2


## @ingroup Lottie
class RepeaterTransform(Transform):
    _props = [
        LottieProp("start_opacity", "so", Value, False),
        LottieProp("end_opacity", "eo", Value, False),
    ]

    def __init__(self):
        Transform.__init__(self)
        self.start_opacity = Value(100)
        self.end_opacity = Value(100)


## @ingroup Lottie
class Modifier(ShapeElement):
    pass


## @ingroup Lottie
class TrimMultipleShapes(LottieEnum):
    Simultaneously = 1
    Individually = 2


## @ingroup Lottie
## @todo Implement SIF Export
class Trim(Modifier):
    """
    Trims shapes into a segment
    """
    _props = [
        LottieProp("start", "s", Value, False),
        LottieProp("end", "e", Value, False),
        LottieProp("offset", "o", Value, False),
        LottieProp("multiple", "m", TrimMultipleShapes, False),
    ]
    ## %Shape type.
    type = "tm"

    def __init__(self):
        ShapeElement.__init__(self)
        ## Start of the segment, as a percentage
        self.start = Value(0)
        ## End of the segment, as a percentage
        self.end = Value(100)
        ## start/end offset, as an angle (0, 360)
        self.offset = Value(0)
        ## @todo?
        self.multiple = None


## @ingroup Lottie
class Repeater(Modifier):
    """
    Duplicates previous shapes in a group
    """
    _props = [
        LottieProp("copies", "c", Value, False),
        LottieProp("offset", "o", Value, False),
        LottieProp("composite", "m", Composite, False),
        LottieProp("transform", "tr", RepeaterTransform, False),
    ]
    ## %Shape type.
    type = "rp"

    def __init__(self, copies=1):
        Modifier.__init__(self)
        ## Number of Copies
        self.copies = Value(copies)
        ## Offset of Copies
        self.offset = Value()
        ## Composite of copies
        self.composite = Composite.Above
        ## Transform values for each repeater copy
        self.transform = RepeaterTransform()


## @ingroup Lottie
## @todo Implement SIF Export
class RoundedCorners(Modifier):
    """
    Rounds corners of other shapes
    """
    _props = [
        LottieProp("radius", "r", Value, False),
    ]
    ## %Shape type.
    type = "rd"

    def __init__(self):
        Modifier.__init__(self)
        ## Rounded Corner Radius
        self.radius = Value()


## @ingroup Lottie
## @ingroup LottieCheck
## @note marked as unsupported by lottie
class Merge(ShapeElement):
    _props = [
        LottieProp("merge_mode", "mm", float, False),
    ]
    ## %Shape type.
    type = "mm"

    def __init__(self):
        ShapeElement.__init__(self)
        ## Merge Mode
        self.merge_mode = 1


## @ingroup Lottie
## @note marked as unsupported by lottie
class Twist(ShapeElement):
    _props = [
        LottieProp("angle", "a", Value, False),
        LottieProp("center", "c", MultiDimensional, False),
    ]
    ## %Shape type.
    type = "tw"

    def __init__(self):
        ShapeElement.__init__(self)
        self.angle = Value(0)
        self.center = MultiDimensional(NVector(0, 0))



class ZigZag(ShapeElement):
    """
    Zig Zag shape modifier
    """
    _props = [
        LottieProp("frequency", "r", Value, False),
        LottieProp("amplitude", "s", Value, False),
        LottieProp("point_type", "pt", Value, False),
    ]
    ## %Shape type.
    type = "zz"

    def __init__(self):
        ShapeElement.__init__(self)
        ## Number of ridges per segment
        self.frequency = Value(5)
        ## Distance between peaks and troughs
        self.amplitude = Value(10)
        ## Point type (1 = corner, 2 = smooth)
        self.point_type = Value(1)
