import enum
import math
import colorsys
from ..nvector import NVector


def from_uint8(r, g, b, a=255):
    return Color(r, g, b, a) / 255


class ColorMode(enum.Enum):
    ## sRGB, Components in [0, 1]
    RGB = enum.auto()
    ## HSV, components in [0, 1]
    HSV = enum.auto()
    ## HSL, components in [0, 1]
    HSL = enum.auto()
    ## CIE XYZ with Illuminant D65. Components in [0, 1]
    XYZ = enum.auto()
    ## CIE L*u*v*
    LUV = enum.auto()
    ## CIE Lch(uv), polar version of LUV where C is the radius and H an angle in radians
    LCH_uv = enum.auto()
    ## CIE L*a*b*
    LAB = enum.auto()
    ## CIE LCh(ab), polar version of LAB where C is the radius and H an angle in radians
    #LCH_ab = enum.auto()


def _clamp(x):
    return max(0, min(1, x))


class Conversion:
    _conv_paths = {
        (ColorMode.RGB, ColorMode.RGB): [],
        (ColorMode.RGB, ColorMode.HSV): [],
        (ColorMode.RGB, ColorMode.HSL): [],
        (ColorMode.RGB, ColorMode.XYZ): [],
        (ColorMode.RGB, ColorMode.LUV): [ColorMode.XYZ],
        (ColorMode.RGB, ColorMode.LAB): [ColorMode.XYZ],
        (ColorMode.RGB, ColorMode.LCH_uv): [ColorMode.XYZ, ColorMode.LUV],
        #(ColorMode.RGB, ColorMode.LCH_ab): [ColorMode.XYZ, ColorMode.LAB],

        (ColorMode.HSV, ColorMode.RGB): [],
        (ColorMode.HSV, ColorMode.HSV): [],
        (ColorMode.HSV, ColorMode.HSL): [],
        (ColorMode.HSV, ColorMode.XYZ): [ColorMode.RGB],
        (ColorMode.HSV, ColorMode.LUV): [ColorMode.RGB, ColorMode.XYZ],
        (ColorMode.HSV, ColorMode.LAB): [ColorMode.RGB, ColorMode.XYZ],
        (ColorMode.HSV, ColorMode.LCH_uv): [ColorMode.RGB, ColorMode.XYZ, ColorMode.LUV],
        #(ColorMode.HSV, ColorMode.LCH_ab): [ColorMode.RGB, ColorMode.XYZ, ColorMode.LAB],

        (ColorMode.HSL, ColorMode.RGB): [],
        (ColorMode.HSL, ColorMode.HSV): [],
        (ColorMode.HSL, ColorMode.HSL): [],
        (ColorMode.HSL, ColorMode.XYZ): [ColorMode.RGB],
        (ColorMode.HSL, ColorMode.LUV): [ColorMode.RGB, ColorMode.XYZ],
        (ColorMode.HSL, ColorMode.LAB): [ColorMode.RGB, ColorMode.XYZ],
        (ColorMode.HSL, ColorMode.LCH_uv): [ColorMode.RGB, ColorMode.XYZ, ColorMode.LUV],
        #(ColorMode.HSL, ColorMode.LCH_ab): [ColorMode.RGB, ColorMode.XYZ, ColorMode.LAB],

        (ColorMode.XYZ, ColorMode.RGB): [],
        (ColorMode.XYZ, ColorMode.HSV): [ColorMode.RGB],
        (ColorMode.XYZ, ColorMode.HSL): [ColorMode.RGB],
        (ColorMode.XYZ, ColorMode.XYZ): [],
        (ColorMode.XYZ, ColorMode.LUV): [],
        (ColorMode.XYZ, ColorMode.LAB): [],
        (ColorMode.XYZ, ColorMode.LCH_uv): [ColorMode.LUV],
        #(ColorMode.XYZ, ColorMode.LCH_ab): [ColorMode.LAB],

        (ColorMode.LCH_uv, ColorMode.RGB): [ColorMode.LUV, ColorMode.XYZ],
        (ColorMode.LCH_uv, ColorMode.HSV): [ColorMode.LUV, ColorMode.XYZ, ColorMode.RGB],
        (ColorMode.LCH_uv, ColorMode.HSL): [ColorMode.LUV, ColorMode.XYZ, ColorMode.RGB],
        (ColorMode.LCH_uv, ColorMode.XYZ): [ColorMode.LUV],
        (ColorMode.LCH_uv, ColorMode.LUV): [],
        (ColorMode.LCH_uv, ColorMode.LAB): [ColorMode.LUV, ColorMode.XYZ],
        (ColorMode.LCH_uv, ColorMode.LCH_uv): [],
        #(ColorMode.LCH_uv, ColorMode.LCH_ab): [ColorMode.LUV, ColorMode.XYZ, ColorMode.LAB],

        (ColorMode.LUV, ColorMode.RGB): [ColorMode.XYZ],
        (ColorMode.LUV, ColorMode.HSV): [ColorMode.XYZ, ColorMode.RGB],
        (ColorMode.LUV, ColorMode.HSL): [ColorMode.XYZ, ColorMode.RGB],
        (ColorMode.LUV, ColorMode.XYZ): [],
        (ColorMode.LUV, ColorMode.LUV): [],
        (ColorMode.LUV, ColorMode.LAB): [ColorMode.XYZ],
        (ColorMode.LUV, ColorMode.LCH_uv): [],
        #(ColorMode.LUV, ColorMode.LCH_ab): [ColorMode.XYZ, ColorMode.LAB],

        (ColorMode.LAB, ColorMode.RGB): [ColorMode.XYZ],
        (ColorMode.LAB, ColorMode.HSV): [ColorMode.XYZ, ColorMode.RGB],
        (ColorMode.LAB, ColorMode.HSL): [ColorMode.XYZ, ColorMode.RGB],
        (ColorMode.LAB, ColorMode.XYZ): [],
        (ColorMode.LAB, ColorMode.LUV): [ColorMode.XYZ],
        (ColorMode.LAB, ColorMode.LAB): [],
        (ColorMode.LAB, ColorMode.LCH_uv): [ColorMode.XYZ, ColorMode.LUV],
        #(ColorMode.LAB, ColorMode.LCH_ab): [],

        #(ColorMode.LCH_ab, ColorMode.RGB): [ColorMode.LAB, ColorMode.XYZ],
        #(ColorMode.LCH_ab, ColorMode.HSV): [ColorMode.LAB, ColorMode.XYZ, ColorMode.RGB],
        #(ColorMode.LCH_ab, ColorMode.HSL): [ColorMode.LAB, ColorMode.XYZ, ColorMode.RGB],
        #(ColorMode.LCH_ab, ColorMode.XYZ): [ColorMode.LAB],
        #(ColorMode.LCH_ab, ColorMode.LUV): [ColorMode.LAB, ColorMode.XYZ],
        #(ColorMode.LCH_ab, ColorMode.LAB): [],
        #(ColorMode.LCH_ab, ColorMode.LCH_uv): [ColorMode.LAB, ColorMode.XYZ, ColorMode.LUV],
        #(ColorMode.LCH_ab, ColorMode.LCH_ab): [],
    }

    @staticmethod
    def rgb_to_hsv(r, g, b):
        return colorsys.rgb_to_hsv(r, g, b)

    @staticmethod
    def hsv_to_rgb(r, g, b):
        return colorsys.hsv_to_rgb(r, g, b)

    @staticmethod
    def hsl_to_hsv(h, s_hsl, l):
        v = l + s_hsl * min(l, 1 - l)
        s_hsv = 0 if v == 0 else 2 - 2 * l / v
        return (h, s_hsv, v)

    @staticmethod
    def hsv_to_hsl(h, s_hsv, v):
        l = v - v * s_hsv / 2
        s_hsl = 0 if l in (0, 1) else (v - l) / min(l, 1 - l)
        return (h, s_hsl, l)

    @staticmethod
    def rgb_to_hsl(r, g, b):
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return (h, s, l)

    @staticmethod
    def hsl_to_rgb(h, s, l):
        return colorsys.hls_to_rgb(h, l, s)

    # http://w3.uqo.ca/missaoui/Publications/TRColorSpace.zip
    #@staticmethod
    #def rgb_to_hcl(r, g, b, gamma=3, y0=100):
        #maxc = max(r, g, b)
        #minc = min(r, g, b)
        #if maxc > 0:
            #alpha = 1/y0 * minc / maxc
        #else:
            #alpha = 0
        #q = math.e ** (alpha * gamma)
        #h = math.atan2(g - b, r - g)
        #if h < 0:
            #h += 2*math.pi
        #h /= 2*math.pi
        #c = q / 3 * (abs(r-g) + abs(g-b) + abs(b-r))
        #l = (q * maxc + (q-1) * minc) / 2
        #return (h, c, l)

    #@staticmethod
    #def hcl_to_rgb(h, c, l, gamma=3, y0=100):
        #h *= 2*math.pi

        #q = math.e ** ((1 - 2*c / 4*l) * gamma / y0)
        #minc = (4*l - 3*c) / (4*q - 2)
        #maxc = minc + 3*c / 2*q

        #if h <= math.pi * 1 / 3:
            #tan = math.tan(3/2*h)
            #r = maxc
            #b = minc
            #g = (r * tan + b) / (1 + tan)
        #elif h <= math.pi * 2 / 3:
            #tan = math.tan(3/4*(h-math.pi))
            #g = maxc
            #b = minc
            #r = (g * (1+tan) - b) / tan
        #elif h <= math.pi * 3 / 3:
            #tan = math.tan(3/4*(h-math.pi))
            #g = maxc
            #r = minc
            #b = g * (1+tan) - r * tan
        #elif h <= math.pi * 4 / 3:
            #tan = math.tan(3/2*(h+math.pi))
            #b = maxc
            #r = minc
            #g = (r * tan + b) / (1 + tan)
        #elif h <= math.pi * 5 / 3:
            #tan = math.tan(3/4*h)
            #b = maxc
            #g = minc
            #r = (g * (1+tan) - b) / tan
        #else:
            #tan = math.tan(3/4*h)
            #r = maxc
            #g = minc
            #b = g * (1+tan) - r * tan

        #return _clamp(r), _clamp(g), _clamp(b)

    @staticmethod
    def rgb_to_xyz(r, g, b):
        def _gamma(v):
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        rgb = (_gamma(r), _gamma(g), _gamma(b))
        matrix = [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
        return tuple(
            sum(rgb[i] * c for i, c in enumerate(row))
            for row in matrix
        )

    @staticmethod
    def xyz_to_rgb(x, y, z):
        def _gamma1(v):
            return _clamp(v * 12.92 if v <= 0.0031308 else v ** (1/2.4) * 1.055 - 0.055)
        matrix = [
            [+3.2404542, -1.5371385, -0.4985314],
            [-0.9692660, +1.8760108, +0.0415560],
            [+0.0556434, -0.2040259, +1.0572252],
        ]
        xyz = (x, y, z)
        return tuple(map(_gamma1, (
            sum(xyz[i] * c for i, c in enumerate(row))
            for row in matrix
        )))

    @staticmethod
    def xyz_to_luv(x, y, z):
        u1r = 0.2009
        v1r = 0.4610
        yr = 100

        kap = (29/3)**3
        eps = (6/29)**3

        try:
            u1 = 4*x / (x + 15*y + 3*z)
            v1 = 9*y / (x + 15*y + 3*z)
        except ZeroDivisionError:
            return 0, 0, 0

        y_r = y/yr
        l = 166 * y_r ** (1/3) - 16 if y_r > eps else kap * y_r
        u = 13 * l * (u1 - u1r)
        v = 13 * l * (v1 - v1r)
        return l, u, v

    @staticmethod
    def luv_to_xyz(l, u, v):
        u1r = 0.2009
        v1r = 0.4610
        yr = 100

        kap = (29/3)**3

        if l == 0:
            u1 = u1r
            v1 = v1r
        else:
            u1 = u / (13 * l) + u1r
            v1 = v / (13 * l) + v1r

        y = yr * l / kap if l <= 8 else yr * ((l + 16) / 116) ** 3
        x = y * 9*u1 / (4*v1)
        z = y * (12 - 3*u1 - 20*v1) / (4*v1)
        return x, y, z

    @staticmethod
    def luv_to_lch_uv(l, u, v):
        c = math.hypot(u, v)
        h = math.atan2(v, u)
        if h < 0:
            h += math.tau
        return l, c, h

    @staticmethod
    def lch_uv_to_luv(l, c, h):
        u = math.cos(h) * c
        v = math.sin(h) * c
        return l, u, v

    @staticmethod
    def xyz_to_lab(x, y, z):
        # D65 Illuminant aka sRGB(1,1,1)
        xn = 0.950489
        yn = 1
        zn = 108.8840

        delta = 6 / 29

        def f(t):
            return t ** (1/3) if t > delta ** 3 else t / (3*delta**2) + 4/29

        fy = f(y/yn)
        l = 116 * fy - 16
        a = 500 * (f(x/xn) - fy)
        b = 200 * (fy - f(z/zn))

        return l, a, b

    @staticmethod
    def lab_to_xyz(l, a, b):
        # D65 Illuminant aka sRGB(1,1,1)
        xn = 0.950489
        yn = 1
        zn = 108.8840

        delta = 6 / 29

        def f1(t):
            return t**3 if t > delta else 3*delta**2*(t-4/29)

        l1 = (l+16) / 116
        x = xn * f1(l1+a/500)
        y = yn * f1(l1)
        z = zn * f1(l1-b/200)

        return x, y, z

    #@staticmethod
    #def lab_to_lch_ab(l, a, b):
        #c = math.hypot(a, b)
        #h = math.atan2(b, a)
        #if h < 0:
            #h += math.tau
        #return l, c, h

    #@staticmethod
    #def lch_ab_to_lab(l, c, h):
        #a = math.cos(h) * c
        #b = math.sin(h) * c
        #return l, a, b

    @staticmethod
    def conv_func(mode_from, mode_to):
        return getattr(Conversion, "%s_to_%s" % (mode_from.name.lower(), mode_to.name.lower()), None)

    @staticmethod
    def convert(tuple, mode_from, mode_to):
        if mode_from == mode_to:
            return tuple

        if len(tuple) == 4:
            alpha = tuple[3]
            tuple = tuple[:3]
        else:
            alpha = None

        func = Conversion.conv_func(mode_from, mode_to)
        if func:
            return func(*tuple)

        if (mode_from, mode_to) in Conversion._conv_paths:
            steps = Conversion._conv_paths[(mode_from, mode_to)] + [mode_to]
            for step in steps:
                func = Conversion.conv_func(mode_from, step)
                if not func:
                    raise ValueError("Missing definition for conversion from %s to %s" % (mode_from, step))
                tuple = func(*tuple)
                mode_from = step
            if alpha is not None:
                tuple += (alpha,)
            return tuple

        raise ValueError("No conversion path from %s to %s" % (mode_from, mode_to))


class Color(NVector):
    Mode = ColorMode

    def __init__(self, c1=0, c2=0, c3=0, a=1, *, mode=ColorMode.RGB):
        if isinstance(a, ColorMode):
            raise TypeError("Please update the Color constructor")
        super().__init__(c1, c2, c3, a)
        self._mode = mode

    @property
    def mode(self):
        return self._mode

    def convert(self, v):
        if v == self._mode:
            return self

        self.components = list(Conversion.convert(self.components, self._mode, v))

        self._mode = v
        return self

    def clone(self):
        return Color(*self.components, mode=self._mode)

    def converted(self, mode):
        return self.clone().convert(mode)

    def to_rgb(self):
        return self.converted(ColorMode.RGB)

    def __repr__(self):
        return "<%s %s [%.3f, %.3f, %.3f, %.3f]>" % (
            (self.__class__.__name__, self.mode.name) + tuple(self.components)
        )

    def component_names(self):
        comps = None

        if self._mode == ColorMode.RGB:
            comps = ({"r", "red"}, {"g", "green"}, {"b", "blue"})
        elif self._mode == ColorMode.HSV:
            comps = ({"h", "hue"}, {"s", "saturation"}, {"v", "value"})
        elif self._mode == ColorMode.HSL:
            comps = ({"h", "hue"}, {"s", "saturation"}, {"l", "lightness"})
        elif self._mode == ColorMode.LCH_uv:  # in (ColorMode.LCH_uv, ColorMode.LCH_ab):
            comps = ({"l", "luma", "luminance"}, {"c", "choma"}, {"h", "hue"})
        elif self._mode == ColorMode.XYZ:
            comps = "xyz"
        elif self._mode == ColorMode.LUV:
            comps = "luv"
        elif self._mode == ColorMode.LAB:
            comps = "lab"

        return comps

    def _attrindex(self, name):
        comps = self.component_names()

        if comps:
            for i, vals in enumerate(comps):
                if name in vals:
                    return i

        return None

    def __getattr__(self, name):
        if name not in vars(self) and name not in {"_mode", "components"}:
            i = self._attrindex(name)
            if i is not None:
                return self.components[i]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name not in vars(self) and name not in {"_mode", "components"}:
            i = self._attrindex(name)
            if i is not None:
                self.components[i] = value
                return
        return super().__setattr__(name, value)
