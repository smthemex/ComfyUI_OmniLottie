from PIL import Image
from .. import objects
from .. import NVector, Color
from ..utils import color


class Polygen:
    def __init__(self, x, y):
        self.vertices = [
            NVector(x, y),
            NVector(x+1, y),
            NVector(x+1, y+1),
            NVector(x, y+1),
        ]
        self._has_x = False
        self._has_y = False

    def add_pixel_x(self, x, y):
        i = self.vertices.index(NVector(x, y))
        if len(self.vertices) > i and self.vertices[i+1] == NVector(x, y+1):
            self._has_x = True
            self.vertices.insert(i+1, NVector(x+1, y))
            self.vertices.insert(i+2, NVector(x+1, y+1))
        else:
            raise ValueError()

    def add_pixel_x_neg(self, x, y):
        i = self.vertices.index(NVector(x+1, y))
        if i > 0 and self.vertices[i-1] == NVector(x+1, y+1):
            self._has_x = True
            self.vertices.insert(i, NVector(x, y))
            self.vertices.insert(i, NVector(x, y+1))
        else:
            raise ValueError()

    def add_pixel_y(self, x, y):
        i = self.vertices.index(NVector(x, y))
        if i > 0 and self.vertices[i-1] == NVector(x+1, y):
            self._has_y = True
            if i > 1 and self.vertices[i-2] == NVector(x+1, y+1):
                self.vertices[i-1] = NVector(x, y+1)
            else:
                self.vertices.insert(i, NVector(x, y+1))
                self.vertices.insert(i, NVector(x+1, y+1))
        else:
            raise ValueError()

    def _to_rect(self, id1, id2):
        p1 = self.vertices[id1]
        p2 = self.vertices[id2]
        return objects.Rect((p1+p2)/2, p2-p1)

    def to_shape(self):
        if not self._has_x or not self._has_y:
            return self._to_rect(0, int(len(self.vertices)/2))
        bez = objects.Bezier()
        bez.closed = True
        for point in self.vertices:
            if len(bez.vertices) > 1 and (
                bez.vertices[-1].x == bez.vertices[-2].x == point.x or
                bez.vertices[-1].y == bez.vertices[-2].y == point.y
            ):
                bez.vertices[-1] = point
            else:
                bez.add_point(point)

        if len(bez.vertices) > 2 and bez.vertices[0].x == bez.vertices[-1].x == bez.vertices[-2].x:
            bez.vertices.pop()
            bez.out_tangents.pop()
            bez.in_tangents.pop()
        return objects.Path(bez)


def pixel_add_layer_paths(animation, raster):
    layer = animation.add_layer(objects.ShapeLayer())
    groups = {}
    processed = set()
    xneg_candidates = set()

    def avail(x, y):
        rid = (x, y)
        return not (
            x < 0 or x >= raster.width or y >= raster.height or
            rid in processed or raster.getpixel(rid) != colort
        )

    def recurse(gen, x, y, xneg):
        processed.add((x, y))
        if avail(x+1, y):
            gen.add_pixel_x(x+1, y)
            recurse(gen, x+1, y, False)
        if avail(x, y+1):
            gen.add_pixel_y(x, y+1)
            recurse(gen, x, y+1, True)
        if xneg and avail(x-1, y):
            xneg_candidates.add((x-1, y))

    for y in range(raster.height):
        for x in range(raster.width):
            pid = (x, y)
            colort = raster.getpixel(pid)
            if colort[-1] == 0 or pid in processed:
                continue

            gen = Polygen(x, y)
            xneg_candidates = set()
            recurse(gen, x, y, False)
            xneg_candidates -= processed
            while xneg_candidates:
                p = next(iter(sorted(xneg_candidates, key=lambda t: (t[1], t[0]))))
                gen.add_pixel_x_neg(*p)
                recurse(gen, p[0], p[1], True)
                processed.add(p)
                xneg_candidates -= processed

            g = groups.setdefault(colort, set())
            g.add(gen.to_shape())

    for colort, rects in groups.items():
        g = layer.add_shape(objects.Group())
        g.shapes = list(rects) + g.shapes
        g.name = "".join("%02x" % c for c in colort)
        fill = g.add_shape(objects.Fill())
        fill.color.value = color.from_uint8(*colort[:3])
        fill.opacity.value = colort[-1] / 255 * 100
        stroke = g.add_shape(objects.Stroke(fill.color.value, 0.1))
        stroke.opacity.value = fill.opacity.value
    return layer


def pixel_add_layer_rects(animation, raster):
    layer = animation.add_layer(objects.ShapeLayer())
    last_rects = {}
    groups = {}

    def merge_up():
        if last_rect and last_rect._start in last_rects:
            yrect = last_rects[last_rect._start]
            if yrect.size.value.x == last_rect.size.value.x and yrect._color == last_rect._color:
                groups[last_rect._color].remove(last_rect)
                yrect.position.value.y += 0.5
                yrect.size.value.y += 1
                rects[last_rect._start] = yrect

    def group(colort):
        return groups.setdefault(colort, set())

    for y in range(raster.height):
        rects = {}
        last_color = None
        last_rect = None
        for x in range(raster.width):
            colort = raster.getpixel((x, y))
            if colort[-1] == 0:
                continue
            yrect = last_rects.get(x, None)
            if colort == last_color:
                last_rect.position.value.x += 0.5
                last_rect.size.value.x += 1
            elif yrect and colort == yrect._color and yrect.size.value.x == 1:
                yrect.position.value.y += 0.5
                yrect.size.value.y += 1
                rects[x] = yrect
                last_color = last_rect = colort = None
            else:
                merge_up()
                g = group(colort)
                last_rect = objects.Rect()
                g.add(last_rect)
                last_rect.size.value = NVector(1, 1)
                last_rect.position.value = NVector(x + 0.5, y + 0.5)
                rects[x] = last_rect
                last_rect._start = x
                last_rect._color = colort
            last_color = colort
        merge_up()
        last_rects = rects

    for colort, rects in groups.items():
        g = layer.add_shape(objects.Group())
        g.shapes = list(rects) + g.shapes
        g.name = "".join("%02x" % c for c in colort)
        fill = g.add_shape(objects.Fill())
        fill.color.value = color.from_uint8(*colort[:3])
        fill.opacity.value = colort[-1] / 255 * 100
        stroke = g.add_shape(objects.Stroke(fill.color.value, 0.1))
        stroke.opacity.value = fill.opacity.value
    return layer


def _vectorizing_func(filenames, frame_delay, framerate, callback):
    if not isinstance(filenames, list):
        filenames = [filenames]

    animation = objects.Animation(0, framerate)
    nframes = 0

    for filename in filenames:
        raster = Image.open(filename)
        if nframes == 0:
            animation.width = raster.width
            animation.height = raster.height
        if not hasattr(raster, "is_animated"):
            raster.n_frames = 1
            raster.seek = lambda x: None
        for frame in range(raster.n_frames):
            raster.seek(frame)
            new_im = Image.new("RGBA", raster.size)
            new_im.paste(raster)
            callback(animation, new_im, nframes + frame)
            new_im.close()
        nframes += raster.n_frames

    animation.out_point = frame_delay * nframes
    #animation._nframes = nframes

    return animation


def raster_to_embedded_assets(filenames, frame_delay=1, framerate=60, embed_format=None):
    """!
    @brief Loads external assets
    """
    def callback(animation, raster, frame):
        asset = objects.assets.Image.embedded(raster, embed_format)
        animation.assets.append(asset)
        layer = animation.add_layer(objects.ImageLayer(asset.id))
        layer.in_point = frame * frame_delay
        layer.out_point = layer.in_point + frame_delay

    return _vectorizing_func(filenames, frame_delay, framerate, callback)


def raster_to_linked_assets(filenames, frame_delay=1, framerate=60):
    """!
    @brief Loads external assets
    """
    animation = objects.Animation(frame_delay * len(filenames), framerate)

    for frame, filename in enumerate(filenames):
        asset = objects.assets.Image.linked(filename)
        animation.assets.append(asset)
        layer = animation.add_layer(objects.ImageLayer(asset.id))
        layer.in_point = frame * frame_delay
        layer.out_point = layer.in_point + frame_delay

    return animation


def pixel_to_animation(filenames, frame_delay=1, framerate=60):
    """!
    @brief Converts pixel art to vector
    """
    def callback(animation, raster, frame):
        layer = pixel_add_layer_rects(animation, raster.convert("RGBA"))
        layer.in_point = frame * frame_delay
        layer.out_point = layer.in_point + frame_delay

    return _vectorizing_func(filenames, frame_delay, framerate, callback)


def pixel_to_animation_paths(filenames, frame_delay=1, framerate=60):
    """!
    @brief Converts pixel art to vector paths

    Slower and yields larger files compared to pixel_to_animation,
    but it produces a single shape for each area with the same color.
    Mostly useful when you want to add your own animations to the loaded image
    """
    def callback(animation, raster, frame):
        layer = pixel_add_layer_paths(animation, raster.convert("RGBA"))
        layer.in_point = frame * frame_delay
        layer.out_point = layer.in_point + frame_delay

    return _vectorizing_func(filenames, frame_delay, framerate, callback)
