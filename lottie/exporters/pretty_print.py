import sys

from ..objects.base import LottieObject, LottieBase
from ..objects.properties import MultiDimensional, Value, ShapeProperty
from ..objects.layers import Layer


def _prettyprint_scalar(lottie_object, out=sys.stdout):
    if isinstance(lottie_object, float) and lottie_object == round(lottie_object):
        lottie_object = int(lottie_object)
    return str(lottie_object)


def prettyprint(lottie_object, out=sys.stdout, indent="   ", _i=""):
    if isinstance(lottie_object, LottieObject):
        out.write(lottie_object.__class__.__name__)
        out.write('\n')
        _i += indent
        maxk = max(map(lambda x: len(x.name), lottie_object._props))
        for k in lottie_object._props:
            out.write(_i)
            out.write(k.name.ljust(maxk))
            out.write(' : ')
            prettyprint(k.get(lottie_object), out, indent, _i)
    elif isinstance(lottie_object, (list, tuple)):
        if not lottie_object or (not isinstance(lottie_object[0], LottieBase) and len(lottie_object) < 16):
            out.write("[")
            out.write(", ".join(map(_prettyprint_scalar, lottie_object)))
            out.write("]\n")
        else:
            out.write("[\n")
            for k in lottie_object:
                out.write(_i + indent)
                prettyprint(k, out, indent, _i + indent)
            out.write(_i)
            out.write(']\n')
    else:
        out.write(_prettyprint_scalar(lottie_object, out))
        out.write('\n')


def _prettyprint_summary_printable(obj):
    if isinstance(obj, LottieObject):
        return not isinstance(obj, (MultiDimensional, Value, ShapeProperty))
    return obj and isinstance(obj, (list, tuple)) and isinstance(obj[0], LottieObject)


def prettyprint_summary(lottie_object, out=sys.stdout, indent="   ", _i=""):
    if isinstance(lottie_object, LottieObject):
        out.write(lottie_object.__class__.__name__)
        name = getattr(lottie_object, "name", None)
        if name:
            out.write(" %r" % name)
        if isinstance(lottie_object, Layer):
            out.write(" %s -> %s" % (lottie_object.index, lottie_object.parent_index))
        out.write('\n')
        _i += indent
        for k in lottie_object._props:
            val = k.get(lottie_object)
            if _prettyprint_summary_printable(val):
                out.write(_i)
                out.write(k.name)
                out.write(' : ')
                prettyprint_summary(val, out, indent, _i)
    elif _prettyprint_summary_printable(lottie_object):
            out.write("[\n")
            for k in lottie_object:
                out.write(_i + indent)
                prettyprint_summary(k, out, indent, _i + indent)
            out.write(_i)
            out.write(']\n')
