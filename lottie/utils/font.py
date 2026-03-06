import os
import sys
import subprocess
import fontTools.pens.basePen
import fontTools.ttLib
import fontTools.t1Lib
from fontTools.pens.boundsPen import ControlBoundsPen
import enum
import math
from xml.etree import ElementTree
from ..nvector import NVector
from ..objects.bezier import Bezier, BezierPoint
from ..objects.shapes import Path, Group, Fill, Stroke
from ..objects.text import TextJustify
from ..objects.base import LottieProp, CustomObject
from ..objects.layers import ShapeLayer


class BezierPen(fontTools.pens.basePen.BasePen):
    def __init__(self, glyphSet, offset=NVector(0, 0)):
        super().__init__(glyphSet)
        self.beziers = []
        self.current = Bezier()
        self.offset = offset

    def _point(self, pt):
        return self.offset + NVector(pt[0], -pt[1])

    def _moveTo(self, pt):
        self._endPath()

    def _endPath(self):
        if len(self.current.points):
            self.beziers.append(self.current)
        self.current = Bezier()

    def _closePath(self):
        self.current.close()
        self._endPath()

    def _lineTo(self, pt):
        if len(self.current.points) == 0:
            self.current.points.append(self._point(self._getCurrentPoint()))

        self.current.points.append(self._point(pt))

    def _curveToOne(self, pt1, pt2, pt3):
        if len(self.current.points) == 0:
            cp = self._point(self._getCurrentPoint())
            self.current.points.append(
                BezierPoint(
                    cp,
                    None,
                    self._point(pt1) - cp
                )

            )
        else:
            self.current.points[-1].out_tangent = self._point(pt1) - self.current.points[-1].vertex

        dest = self._point(pt3)
        self.current.points.append(
            BezierPoint(
                dest,
                self._point(pt2) - dest,
                None,
            )
        )


class SystemFont:
    def __init__(self, family):
        self.family = family
        self.files = {}
        self.styles = set()
        self._renderers = {}

    def add_file(self, styles, file):
        self.styles |= set(styles)
        key = self._key(styles)
        self.files.setdefault(key, file)

    def filename(self, styles):
        return self.files[self._key(styles)]

    def _key(self, styles):
        if isinstance(styles, str):
            return (styles,)
        return tuple(sorted(styles))

    def __getitem__(self, styles):
        key = self._key(styles)
        if key in self._renderers:
            return self._renderers[key]
        fr = RawFontRenderer(self.files[key])
        self._renderers[key] = fr
        return fr

    def __repr__(self):
        return "<SystemFont %s>" % self.family


class FontQuery:
    """!
    @see https://www.freedesktop.org/software/fontconfig/fontconfig-user.html#AEN21
         https://manpages.ubuntu.com/manpages/cosmic/man1/fc-pattern.1.html
    """
    def __init__(self, str=""):
        self._query = {}
        if isinstance(str, FontQuery):
            self._query = str._query.copy()
        elif str:
            chunks = str.split(":")
            family = chunks.pop(0)
            self._query = dict(
                chunk.split("=")
                for chunk in chunks
                if chunk
            )
            self.family(family)

    def family(self, name):
        self._query["family"] = name
        return self

    def weight(self, weight):
        self._query["weight"] = weight
        return self

    def css_weight(self, weight):
        """!
            Weight from CSS weight value.

            Weight is different between CSS and fontconfig
            This creates some interpolations to ensure known values are translated properly
            @see https://www.freedesktop.org/software/fontconfig/fontconfig-user.html#AEN178
                 https://developer.mozilla.org/en-US/docs/Web/CSS/font-weight#Common_weight_name_mapping
        """
        if weight < 200:
            v = max(0, weight - 100) / 100 * 40
        elif weight < 500:
            v = -weight**3 / 200000 + weight**2 * 11/2000 - weight * 17/10 + 200
        elif weight < 700:
            v = -weight**2 * 3/1000 + weight * 41/10 - 1200
        else:
            v = (weight - 700) / 200 * 10 + 200
        return self.weight(int(round(v)))

    def style(self, *styles):
        self._query["style"] = " ".join(styles)
        return self

    def charset(self, *hex_ranges):
        self._query["charset"] = " ".join(hex_ranges)
        return self

    def char(self, char):
        return self.charset("%x" % ord(char))

    def custom(self, property, value):
        self._query[property] = value
        return self

    def clone(self):
        return FontQuery(self)

    def __getitem__(self, key):
        return self._query.get(key, "")

    def __contains__(self, item):
        return item in self._query

    def get(self, key, default=None):
        return self._query.get(key, default)

    def __str__(self):
        return self._query.get("family", "") + ":" + ":".join(
            "%s=%s" % (p, v)
            for p, v in self._query.items()
            if p != "family"
        )

    def __repr__(self):
        return "<FontQuery %r>" % str(self)

    def weight_to_css(self):
        x = int(self["weight"])
        if x < 40:
            v = x / 40 * 100 + 100
        elif x < 100:
            v = x**3/300 - x**2 * 11/15 + x*167/3 - 3200/3
        elif x < 200:
            v = (2050 - 10 * math.sqrt(5) * math.sqrt(1205 - 6 * x)) / 3
        else:
            v = (x - 200) * 200 / 10 + 700
        return int(round(v))


class _SystemFontList:
    def __init__(self):
        self.fonts = None

    def _lazy_load(self):
        if self.fonts is None:
            self.load()

    def load(self):
        self.fonts = {}
        self.load_fc_list()

    def cmd(self, *a):
        p = subprocess.Popen(a, stdout=subprocess.PIPE)
        out, err = p.communicate()
        out = out.decode("utf-8").strip()
        return out, p.returncode

    def load_fc_list(self):
        out, returncode = self.cmd("fc-list", r'--format=%{file}\t%{family[0]}\t%{style[0]}\n')
        if returncode == 0:
            for line in out.splitlines():
                file, family, styles = line.split("\t")
                self._get(family).add_file(styles.split(" "), file)

    def best(self, query):
        """!
        Returns the renderer best matching the name
        """
        out, returncode = self.cmd("fc-match", r"--format=%{family}\t%{style}", str(query))
        if returncode == 0:
            return self._font_from_match(out)

    def _font_from_match(self, out):
        fam, style = out.split("\t")
        fam = fam.split(",")[0]
        style = style.split(",")[0].split()
        return self[fam][style]

    def all(self, query):
        """!
        Yields all the renderers matching a query
        """
        out, returncode = self.cmd("fc-match", "-s", r"--format=%{family}\t%{style}\n", str(query))
        if returncode == 0:
            for line in out.splitlines():
                try:
                    yield self._font_from_match(line)
                except (fontTools.ttLib.TTLibError, fontTools.t1Lib.T1Error):
                    pass

    def default(self):
        """!
        Returns the default fornt renderer
        """
        return self.best()

    def _get(self, family):
        self._lazy_load()
        if family in self.fonts:
            return self.fonts[family]
        font = SystemFont(family)
        self.fonts[family] = font
        return font

    def __getitem__(self, key):
        self._lazy_load()
        return self.fonts[key]

    def __iter__(self):
        self._lazy_load()
        return iter(self.fonts.values())

    def keys(self):
        self._lazy_load()
        return self.fonts.keys()

    def __contains__(self, item):
        self._lazy_load()
        return item in self.fonts


## Dictionary of system fonts
fonts = _SystemFontList()


def collect_kerning_pairs(font):
    if "GPOS" not in font:
        return {}

    gpos_table = font["GPOS"].table

    unique_kern_lookups = set()
    for item in gpos_table.FeatureList.FeatureRecord:
        if item.FeatureTag == "kern":
            feature = item.Feature
            unique_kern_lookups |= set(feature.LookupListIndex)

    kerning_pairs = {}
    for kern_lookup_index in sorted(unique_kern_lookups):
        lookup = gpos_table.LookupList.Lookup[kern_lookup_index]
        if lookup.LookupType in {2, 9}:
            for pairPos in lookup.SubTable:
                if pairPos.LookupType == 9:  # extension table
                    if pairPos.ExtensionLookupType == 8:  # contextual
                        continue
                    elif pairPos.ExtensionLookupType == 2:
                        pairPos = pairPos.ExtSubTable

                if pairPos.Format != 1:
                    continue

                firstGlyphsList = pairPos.Coverage.glyphs
                for ps_index, _ in enumerate(pairPos.PairSet):
                    for pairValueRecordItem in pairPos.PairSet[ps_index].PairValueRecord:
                        secondGlyph = pairValueRecordItem.SecondGlyph
                        valueFormat = pairPos.ValueFormat1

                        if valueFormat == 5:  # RTL kerning
                            kernValue = "<%d 0 %d 0>" % (
                                pairValueRecordItem.Value1.XPlacement,
                                pairValueRecordItem.Value1.XAdvance)
                        elif valueFormat == 0:  # RTL pair with value <0 0 0 0>
                            kernValue = "<0 0 0 0>"
                        elif valueFormat == 4:  # LTR kerning
                            kernValue = pairValueRecordItem.Value1.XAdvance
                        else:
                            print(
                                "\tValueFormat1 = %d" % valueFormat,
                                file=sys.stdout)
                            continue  # skip the rest

                        kerning_pairs[(firstGlyphsList[ps_index], secondGlyph)] = kernValue
    return kerning_pairs


class GlyphMetrics:
    def __init__(self, glyph, lsb, aw, xmin, xmax):
        self.glyph = glyph
        self.lsb = lsb
        self.advance = aw
        self.xmin = xmin
        self.xmax = xmax
        self.width = xmax - xmin
        self.advance = xmax

    def draw(self, pen):
        return self.glyph.draw(pen)


class Font:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        if isinstance(self.wrapped, fontTools.ttLib.TTFont):
            self.cmap = self.wrapped.getBestCmap() or {}
        else:
            self.cmap = {}

        self.glyphset = self.wrapped.getGlyphSet()

    @classmethod
    def open(cls, filename):
        try:
            f = fontTools.ttLib.TTFont(filename)
        except fontTools.ttLib.TTLibError:
            f = fontTools.t1Lib.T1Font(filename)
            f.parse()

        return cls(f)

    def getGlyphSet(self):
        return self.wrapped.getGlyphSet()

    def getBestCmap(self):
        return {}

    def glyph_name(self, codepoint):
        if isinstance(codepoint, str):
            if len(codepoint) != 1:
                return ""
            codepoint = ord(codepoint)

        if codepoint in self.cmap:
            return self.cmap[codepoint]

        return self.calculated_glyph_name(codepoint)

    @staticmethod
    def calculated_glyph_name(codepoint):
        from fontTools import agl  # Adobe Glyph List
        if codepoint in agl.UV2AGL:
            return agl.UV2AGL[codepoint]
        elif codepoint <= 0xFFFF:
            return "uni%04X" % codepoint
        else:
            return "u%X" % codepoint

    def scale(self):
        if isinstance(self.wrapped, fontTools.ttLib.TTFont):
            return 1 / self.wrapped["head"].unitsPerEm
        elif isinstance(self.wrapped, fontTools.t1Lib.T1Font):
            return self.wrapped["FontMatrix"][0]

    def yMax(self):
        if isinstance(self.wrapped, fontTools.ttLib.TTFont):
            return self.wrapped["head"].yMax
        elif isinstance(self.wrapped, fontTools.t1Lib.T1Font):
            return self.wrapped["FontBBox"][3]

    def glyph(self, glyph_name):
        if isinstance(self.wrapped, fontTools.ttLib.TTFont):
            glyph = self.glyphset[glyph_name]

            xmin = getattr(glyph._glyph, "xMin", glyph.lsb)
            xmax = getattr(glyph._glyph, "xMax", glyph.width)
            return GlyphMetrics(glyph, glyph.lsb, glyph.width, xmin, xmax)
        elif isinstance(self.wrapped, fontTools.t1Lib.T1Font):
            glyph = self.glyphset[glyph_name]
            bounds_pen = ControlBoundsPen(self.glyphset)
            bounds = bounds_pen.bounds
            glyph.draw(bounds_pen)
            if not hasattr(glyph, "width"):
                advance = bounds[2]
            else:
                advance = glyph.width
            return GlyphMetrics(glyph, bounds[0], advance, bounds[0], bounds[2])

    def __contains__(self, key):
        if isinstance(self.wrapped, fontTools.t1Lib.T1Font):
            return key in self.wrapped.font
        return key in self.wrapped

    def __getitem__(self, key):
        return self.wrapped[key]


class FontRenderer:
    tab_width = 4

    @property
    def font(self):
        raise NotImplementedError

    def get_query(self):
        raise NotImplementedError

    def kerning(self, c1, c2):
        return 0

    def text_to_chars(self, text):
        return text

    def _on_missing(self, char, size, pos, group):
        """!
        - Character as string
        - Font size
        - [in, out] Character position
        - Group shape
        """

    def glyph_name(self, ch):
        return self.font.glyph_name(ch)

    def scale(self, size):
        return size * self.font.scale()

    def line_height(self, size):
        return self.font.yMax() * self.scale(size)

    def ex(self, size):
        return self.font.glyph("x").advance * self.scale(size)

    def glyph_beziers(self, glyph, offset=NVector(0, 0)):
        pen = BezierPen(self.font.glyphset, offset)
        glyph.draw(pen)
        return pen.beziers

    def glyph_shapes(self, glyph, offset=NVector(0, 0)):
        beziers = self.glyph_beziers(glyph, offset)
        return [
            Path(bez)
            for bez in beziers
        ]

    def _on_character(self, ch, size, pos, scale, line, use_kerning, chars, i):
        chname = self.glyph_name(ch)

        if chname in self.font.glyphset:
            glyphdata = self.font.glyph(chname)
            #pos.x += glyphdata.lsb * scale
            glyph_shapes = self.glyph_shapes(glyphdata, pos / scale)

            if glyph_shapes:
                if len(glyph_shapes) > 1:
                    glyph_shape_group = line.add_shape(Group())
                    glyph_shape = glyph_shape_group
                else:
                    glyph_shape_group = line
                    glyph_shape = glyph_shapes[0]

                for sh in glyph_shapes:
                    sh.shape.value.scale(scale)
                    glyph_shape_group.add_shape(sh)

                glyph_shape.name = ch

            kerning = 0
            if use_kerning and i < len(chars) - 1:
                nextcname = chars[i+1]
                kerning = self.kerning(chname, nextcname)

            pos.x += (glyphdata.advance + kerning) * scale
            return True
        return False

    def render(self, text, size, pos=None, use_kerning=True):
        """!
        Renders some text

        @param text         String to render
        @param size         Font size (in pizels)
        @param[in,out] pos  Text position
        @param use_kerning  Whether to honour kerning info from the font file

        @returns a Group shape, augmented with some extra attributes:
        - line_height   Line height
        - next_x        X position of the next character
        """
        scale = self.scale(size)
        line_height = self.line_height(size)
        group = Group()
        group.name = text
        if pos is None:
            pos = NVector(0, 0)
        start_x = pos.x
        line = Group()
        group.add_shape(line)
        #group.transform.scale.value = NVector(100, 100) * scale

        chars = self.text_to_chars(text)
        for i, ch in enumerate(chars):
            if ch == "\n":
                line.next_x = pos.x
                pos.x = start_x
                pos.y += line_height
                line = Group()
                group.add_shape(line)
                continue
            elif ch == "\t":
                chname = self.glyph_name(ch)
                if chname in self.font.glyphset:
                    width = self.font.glyph(chname).advance
                else:
                    width = self.ex(size)
                pos.x += width * scale * self.tab_width
                continue

            self._on_character(ch, size, pos, scale, line, use_kerning, chars, i)

        group.line_height = line_height
        group.next_x = line.next_x = pos.x
        return group


class RawFontRenderer(FontRenderer):
    def __init__(self, filename):
        self.filename = filename
        self._font = Font.open(filename)
        self._kerning = None

    @property
    def font(self):
        return self._font

    def kerning(self, c1, c2):
        if self._kerning is None:
            self._kerning = collect_kerning_pairs(self.font)
        return self._kerning.get((c1, c2), 0)

    def __repr__(self):
        return "<FontRenderer %r>" % self.filename

    def get_query(self):
        return self.filename


class FallbackFontRenderer(FontRenderer):
    def __init__(self, query, max_attempts=10):
        self.query = FontQuery(query)
        self._best = None
        self._bq = None
        self._fallback = {}
        self.max_attempts = max_attempts

    @property
    def font(self):
        return self.best.font

    def get_query(self):
        return self.query

    def ex(self, size):
        best = self.best
        if "x" not in self.font.glyphset:
            best = fonts.best(self.query.clone().char("x"))
        return best.ex(size)

    @property
    def best(self):
        cq = str(self.query)
        if self._best is None or self._bq != cq:
            self._best = fonts.best(self.query)
            self._bq = cq
        return self._best

    def fallback_renderer(self, char):
        if char in self._fallback:
            return self._fallback[char]

        if len(char) != 1:
            return None

        codepoint = ord(char)
        name = Font.calculated_glyph_name(codepoint)
        for i, font in enumerate(fonts.all(self.query.clone().char(char))):
            # For some reason fontconfig sometimes returns a font that doesn't
            # actually contain the glyph
            if name in font.font.glyphset or codepoint in font.cmap:
                self._fallback[char] = font
                return font

            if i > self.max_attempts:
                self._fallback[char] = None
                return None

    def _on_character(self, char, size, pos, scale, group, use_kerning, chars, i):
        if self.best._on_character(char, size, pos, scale, group, use_kerning, chars, i):
            return True

        font = self.fallback_renderer(char)
        if not font:
            return False

        child = font.render(char, size, pos)
        if len(child.shapes) == 2:
            group.add_shape(child.shapes[0])
        else:
            group.add_shape(child)

    def __repr__(self):
        return "<FallbackFontRenderer %s>" % self.query


class EmojiRenderer(FontRenderer):
    _split = None

    def __init__(self, wrapped, emoji_dir):
        if not os.path.isdir(emoji_dir):
            raise Exception("Not a valid directory: %s" % emoji_dir)
        self.wrapped = wrapped
        self.emoji_dir = emoji_dir
        self._svgs = {}

    @property
    def font(self):
        return self.wrapped.font

    def _get_svg(self, char):
        from ..parsers.svg import parse_svg_file

        if char in self._svgs:
            return self._svgs[char]

        basename = "-".join("%x" % ord(cp) for cp in char) + ".svg"
        filename = os.path.join(self.emoji_dir, basename)
        if not os.path.isfile(filename):
            self._svgs[char] = None
            return None

        svga = parse_svg_file(filename)
        svgshape = Group()
        svgshape.name = basename
        for layer in svga.layers:
            if isinstance(layer, ShapeLayer):
                for shape in layer.shapes:
                    svgshape.add_shape(shape)

        self._svgs[char] = svgshape
        svgshape._bbox = svgshape.bounding_box()
        return svgshape

    def _on_character(self, char, size, pos, scale, group, use_kerning, chars, i):
        svgshape = self._get_svg(char)
        if svgshape:
            target_height = self.line_height(size)
            scale = target_height / svgshape._bbox.height
            shape_group = Group()
            shape_group = svgshape.clone()
            shape_group.transform.scale.value *= scale
            offset = NVector(
                -svgshape._bbox.x1 + svgshape._bbox.width * 0.075,
                -svgshape._bbox.y2 + svgshape._bbox.height * 0.1
            )
            shape_group.transform.position.value = pos + offset * scale
            group.add_shape(shape_group)
            pos.x += svgshape._bbox.width * scale
            return True
        return self.wrapped._on_character(char, size, pos, scale, group, use_kerning, chars, i)

    def get_query(self):
        return self.wrapped.get_query()

    @staticmethod
    def _get_splitter():
        if EmojiRenderer._split is None:
            try:
                import grapheme
                EmojiRenderer._split = grapheme.graphemes
            except ImportError:
                sys.stderr.write("Install `grapheme` for better Emoji support\n")
                EmojiRenderer._split = lambda x: x
        return EmojiRenderer._split

    @staticmethod
    def emoji_split(string):
        return EmojiRenderer._get_splitter()(string)

    def text_to_chars(self, string):
        return list(self.emoji_split(string))


class FontStyle:
    def __init__(self, query, size, justify=TextJustify.Left, position=None, use_kerning=True, emoji_svg=None):
        self.emoji_svg = emoji_svg
        self._set_query(query)
        self.size = size
        self.justify = justify
        self.position = position.clone() if position else NVector(0, 0)
        self.use_kerning = use_kerning

    def _set_query(self, query):
        if isinstance(query, str) and os.path.isfile(query):
            self._renderer = RawFontRenderer(query)
        else:
            self._renderer = FallbackFontRenderer(query)

        if self.emoji_svg:
            self._renderer = EmojiRenderer(self._renderer, self.emoji_svg)

    @property
    def query(self):
        return self._renderer.get_query()

    @query.setter
    def query(self, value):
        if str(value) != str(self.query):
            self._set_query(value)

    @property
    def renderer(self):
        return self._renderer

    def render(self, text, pos=NVector(0, 0)):
        group = self._renderer.render(text, self.size, self.position+pos, self.use_kerning)
        for subg in group.shapes[:-1]:
            width = subg.next_x - self.position.x - pos.x
            if self.justify == TextJustify.Center:
                subg.transform.position.value.x -= width / 2
            elif self.justify == TextJustify.Right:
                subg.transform.position.value.x -= width
        return group

    def clone(self):
        return FontStyle(str(self._renderer.query), self.size, self.justify, NVector(*self.position), self.use_kerning)

    @property
    def ex(self):
        return self._renderer.ex(self.size)

    @property
    def line_height(self):
        return self._renderer.line_height(self.size)


def _propfac(a):
    return property(lambda s: s._get(a), lambda s, v: s._set(a, v))


class FontShape(CustomObject):
    _props = [
        LottieProp("query_string", "_query", str),
        LottieProp("size", "_size", float),
        LottieProp("justify", "_justify", TextJustify),
        LottieProp("text", "_text", str),
        LottieProp("position", "_position", NVector),
    ]
    wrapped_lottie = Group

    def __init__(self, text="", query="", size=64, justify=TextJustify.Left):
        CustomObject.__init__(self)
        if isinstance(query, FontStyle):
            self.style = query
        else:
            self.style = FontStyle(query, size, justify)
        self.text = text
        self.hidden = None

    def _get(self, a):
        return getattr(self.style, a)

    def _set(self, a, v):
        return setattr(self.style, a, v)

    query = _propfac("query")
    size = _propfac("size")
    justify = _propfac("justify")
    position = _propfac("position")

    @property
    def query_string(self):
        return str(self.query)

    @query_string.setter
    def query_string(self, v):
        self.query = v

    def _build_wrapped(self):
        g = self.style.render(self.text)
        self.line_height = g.line_height
        return g

    def bounding_box(self, time=0):
        return self.wrapped.bounding_box(time)
