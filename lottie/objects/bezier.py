import math
from .base import LottieObject, LottieProp
from .nvector import NVector


class BezierPoint:
    def __init__(self, vertex, in_tangent=None, out_tangent=None):
        self.vertex = vertex
        self.in_tangent = in_tangent or NVector(0, 0)
        self.out_tangent = out_tangent or NVector(0, 0)

    def relative(self):
        return self

    @classmethod
    def smooth(cls, point, in_tangent):
        return cls(point, in_tangent, -in_tangent)

    @classmethod
    def from_absolute(cls, point, in_tangent=None, out_tangent=None):
        if not in_tangent:
            in_tangent = point.clone()
        if not out_tangent:
            out_tangent = point.clone()
        return BezierPoint(point, in_tangent, out_tangent)


class BezierPointView:
    """
    View for bezier point
    """
    def __init__(self, bezier, index):
        self.bezier = bezier
        self.index = index

    @property
    def vertex(self):
        return self.bezier.vertices[self.index]

    @vertex.setter
    def vertex(self, point):
        self.bezier.vertices[self.index] = point

    @property
    def in_tangent(self):
        return self.bezier.in_tangents[self.index]

    @in_tangent.setter
    def in_tangent(self, point):
        self.bezier.in_tangents[self.index] = point

    @property
    def out_tangent(self):
        return self.bezier.out_tangents[self.index]

    @out_tangent.setter
    def out_tangent(self, point):
        self.bezier.out_tangents[self.index] = point

    def relative(self):
        return self


class AbsoluteBezierPointView(BezierPointView):
    @property
    def in_tangent(self):
        return self.bezier.in_tangents[self.index] + self.vertex

    @in_tangent.setter
    def in_tangent(self, point):
        self.bezier.in_tangents[self.index] = point - self.vertex

    @property
    def out_tangent(self):
        return self.bezier.out_tangents[self.index] + self.vertex

    @out_tangent.setter
    def out_tangent(self, point):
        self.bezier.out_tangents[self.index] = point - self.vertex

    def relative(self):
        return BezierPointView(self.bezier, self.index)


class BezierView:
    def __init__(self, bezier, absolute=False):
        self.bezier = bezier
        self.is_absolute = absolute

    def point(self, index):
        if self.is_absolute:
            return AbsoluteBezierPointView(self.bezier, index)
        return BezierPointView(self.bezier, index)

    def __len__(self):
        return len(self.bezier.vertices)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return [
                self.point(i)
                for i in key
            ]
        return self.point(key)

    def __iter__(self):
        for i in range(len(self)):
            yield self.point(i)

    def append(self, point):
        if isinstance(point, NVector):
            self.bezier.add_point(point.clone())
        else:
            bpt = point.relative()
            self.bezier.add_point(bpt.vertex.clone(), bpt.in_tangent.clone(), bpt.out_tangent.clone())

    @property
    def absolute(self):
        return BezierView(self.bezier, True)


## @ingroup Lottie
class Bezier(LottieObject):
    """!
    Single bezier curve
    """
    _props = [
        LottieProp("closed", "c", bool, False),
        LottieProp("in_tangents", "i", NVector, True),
        LottieProp("out_tangents", "o", NVector, True),
        LottieProp("vertices", "v", NVector, True),
    ]

    def __init__(self):
        ## Closed property of shape
        self.closed = False
        ## Cubic bezier handles for the segments before each vertex
        self.in_tangents = []
        ## Cubic bezier handles for the segments after each vertex
        self.out_tangents = []
        ## Bezier curve vertices.
        self.vertices = []
        #self.rel_tangents = rel_tangents
        ## More convent way to  access points
        self.points = BezierView(self)

    def clone(self):
        clone = Bezier()
        clone.closed = self.closed
        clone.in_tangents = [p.clone() for p in self.in_tangents]
        clone.out_tangents = [p.clone() for p in self.out_tangents]
        clone.vertices = [p.clone() for p in self.vertices]
        #clone.rel_tangents = self.rel_tangents
        return clone

    def insert_point(self, index, pos, inp=NVector(0, 0), outp=NVector(0, 0)):
        """!
        Inserts a point at the given index
        @param index    Index to insert the point at
        @param pos      Point to add
        @param inp      Tangent entering the point, as a vector relative to @p pos
        @param outp     Tangent exiting the point, as a vector relative to @p pos
        @returns @c self, for easy chaining
        """
        self.vertices.insert(index, pos)
        self.in_tangents.insert(index, inp.clone())
        self.out_tangents.insert(index, outp.clone())
        #if not self.rel_tangents:
            #self.in_tangents[-1] += pos
            #self.out_tangents[-1] += pos
        return self

    def add_point(self, pos, inp=NVector(0, 0), outp=NVector(0, 0)):
        """!
        Appends a point to the curve
        @see insert_point
        """
        self.insert_point(len(self.vertices), pos, inp, outp)
        return self

    def add_smooth_point(self, pos, inp):
        """!
        Appends a point with symmetrical tangents
        @see insert_point
        """
        self.add_point(pos, inp, -inp)
        return self

    def close(self, closed=True):
        """!
        Updates self.closed
        @returns @c self, for easy chaining
        """
        self.closed = closed
        return self

    def point_at(self, t):
        """!
        @param t    A value between 0 and 1, percentage along the length of the curve
        @returns    The point at @p t in the curve
        """
        i, t = self._index_t(t)
        points = self._bezier_points(i, True)
        return self._solve_bezier(t, points)

    def tangent_angle_at(self, t):
        i, t = self._index_t(t)
        points = self._bezier_points(i, True)

        n = len(points) - 1
        if n > 0:
            delta = sum((
                (points[i+1] - points[i]) * n * self._solve_bezier_coeff(i, n - 1, t)
                for i in range(n)
            ), NVector(0, 0))
            return math.atan2(delta.y, delta.x)

        return 0

    def _split(self, t):
        i, t = self._index_t(t)
        cub = self._bezier_points(i, True)
        split1, split2 = self._split_segment(t, cub)
        return i, split1, split2

    def _split_segment(self, t, cub):
        if len(cub) == 2:
            k = self._solve_bezier_step(t, cub)[0]
            split1 = [cub[0], NVector(0, 0), NVector(0, 0), k]
            split2 = [k, NVector(0, 0), NVector(0, 0), cub[-1]]
            return split1, split2

        if len(cub) == 3:
            quad = cub
        else:
            quad = self._solve_bezier_step(t, cub)
        lin = self._solve_bezier_step(t, quad)
        k = self._solve_bezier_step(t, lin)[0]
        split1 = [cub[0], quad[0]-cub[0], lin[0]-k, k]
        split2 = [k, lin[-1]-k, quad[-1]-cub[-1], cub[-1]]
        return split1, split2

    def split_at(self, t):
        """!
        Get two pieces out of a Bezier curve
        @param t    A value between 0 and 1, percentage along the length of the curve
        @returns Two Bezier objects that correspond to self, but split at @p t
        """
        i, split1, split2 = self._split(t)

        seg1 = Bezier()
        seg2 = Bezier()
        for j in range(i):
            seg1.add_point(self.vertices[j].clone(), self.in_tangents[j].clone(), self.out_tangents[j].clone())
        for j in range(i+2, len(self.vertices)):
            seg2.add_point(self.vertices[j].clone(), self.in_tangents[j].clone(), self.out_tangents[j].clone())

        seg1.add_point(split1[0], self.in_tangents[i].clone(), split1[1])
        seg1.add_point(split1[3], split1[2], split2[1])

        seg2.insert_point(0, split2[0], split1[2], split2[1])
        seg2.insert_point(1, split2[3], split2[2], self.out_tangents[i+1].clone())

        return seg1, seg2

    def segment(self, t1, t2):
        """!
        Splits a Bezier in two points and returns the segment between the
        @param t1   A value between 0 and 1, percentage along the length of the curve
        @param t2   A value between 0 and 1, percentage along the length of the curve
        @returns Bezier object that correspond to the segment between @p t1 and @p t2
        """
        if self.closed and self.vertices and self.vertices[-1] != self.vertices[0]:
            copy = self.clone()
            copy.add_point(self.vertices[0])
            copy.closed = False
            return copy.segment(t1, t2)

        if t1 > 1:
            t1 = 1
        if t2 > 1:
            t2 = 1

        if t1 > t2:
            t1, t2 = t2, t1
        elif t1 == t2:
            seg = Bezier()
            p = self.point_at(t1)
            seg.add_point(p)
            seg.add_point(p)
            return seg

        seg1, seg2 = self.split_at(t1)
        t2p = (t2-t1) / (1-t1)
        seg3, seg4 = seg2.split_at(t2p)
        return seg3

    def split_self_multi(self, positions):
        """!
        Adds more points to the Bezier
        @param positions    list of percentages along the curve
        """
        if not len(positions):
            return
        t1 = positions[0]
        seg1, seg2 = self.split_at(t1)
        self.vertices = []
        self.in_tangents = []
        self.out_tangents = []

        self.vertices = seg1.vertices[:-1]
        self.in_tangents = seg1.in_tangents[:-1]
        self.out_tangents = seg1.out_tangents[:-1]

        for t2 in positions[1:]:
            t = (t2-t1) / (1-t1)
            seg1, seg2 = seg2.split_at(t)
            t1 = t
            self.vertices += seg1.vertices[:-1]
            self.in_tangents += seg1.in_tangents[:-1]
            self.out_tangents += seg1.out_tangents[:-1]

        self.vertices += seg2.vertices
        self.in_tangents += seg2.in_tangents
        self.out_tangents += seg2.out_tangents

    def split_each_segment(self):
        """!
        Adds a point in the middle of the segment between every pair of points in the Bezier
        """
        vertices = self.vertices
        in_tangents = self.in_tangents
        out_tangents = self.out_tangents

        self.vertices = []
        self.in_tangents = []
        self.out_tangents = []

        for i in range(len(vertices)-1):
            tocut = [vertices[i], out_tangents[i]+vertices[i], in_tangents[i+1]+vertices[i+1], vertices[i+1]]
            split1, split2 = self._split_segment(0.5, tocut)
            if i:
                self.out_tangents[-1] = split1[1]
            else:
                self.add_point(vertices[0], in_tangents[0], split1[1])
            self.add_point(split1[3], split1[2], split2[1])
            self.add_point(vertices[i+1], split2[2], NVector(0, 0))

    def split_self_chunks(self, n_chunks):
        """!
        Adds points the Bezier, splitting it into @p n_chunks additional chunks.
        """
        splits = [i/n_chunks for i in range(1, n_chunks)]
        return self.split_self_multi(splits)

    def _bezier_points(self, i, optimize):
        v1 = self.vertices[i].clone()
        v2 = self.vertices[i+1].clone()
        points = [v1]
        t1 = self.out_tangents[i].clone()
        if not optimize or t1.length != 0:
            points.append(t1+v1)
        t2 = self.in_tangents[i+1].clone()
        if not optimize or t1.length != 0:
            points.append(t2+v2)
        points.append(v2)
        return points

    def _solve_bezier_step(self, t, points):
        next = []
        p1 = points[0]
        for p2 in points[1:]:
            next.append(p1 * (1-t) + p2 * t)
            p1 = p2
        return next

    def _solve_bezier_coeff(self, i, n, t):
        return (
            math.factorial(n) / (math.factorial(i) * math.factorial(n - i)) # (n choose i)
            * (t ** i) * ((1 - t) ** (n-i))
        )

    def _solve_bezier(self, t, points):
        n = len(points) - 1
        if n > 0:
            return sum((
                points[i] * self._solve_bezier_coeff(i, n, t)
                for i in range(n+1)
            ), NVector(0, 0))

        #while len(points) > 1:
            #points = self._solve_bezier_step(t, points)
        return points[0]

    def _index_t(self, t):
        if t <= 0:
            return 0, 0

        if t >= 1:
            return len(self.vertices)-2, 1

        n = len(self.vertices)-1
        for i in range(n):
            if (i+1) / n > t:
                break

        return i, (t - (i/n)) * n

    def reverse(self):
        """!
        Reverses the Bezier curve
        """
        self.vertices = list(reversed(self.vertices))
        out_tangents = list(reversed(self.in_tangents))
        in_tangents = list(reversed(self.out_tangents))
        self.in_tangents = in_tangents
        self.out_tangents = out_tangents

    """def to_absolute(self):
        if self.rel_tangents:
            self.rel_tangents = False
            for i in range(len(self.vertices)):
                p = self.vertices[i]
                self.in_tangents[i] += p
                self.out_tangents[i] += p
        return self"""

    def rounded(self, round_distance):
        cloned = Bezier()
        cloned.closed = self.closed
        round_corner = 0.5519

        def _get_vt(closest_index):
            closer_v = self.vertices[closest_index]
            distance = (current - closer_v).length
            new_pos_perc = min(distance/2, round_distance) / distance if distance else 0
            vert = current + (closer_v - current) * new_pos_perc
            tan = - (vert - current) * round_corner
            return vert, tan

        for i, current in enumerate(self.vertices):
            if not self.closed and (i == 0 or i == len(self.points) - 1):
                cloned.points.append(self.points[i])
            else:
                vert1, out_t = _get_vt(i - 1)
                cloned.add_point(vert1, NVector(0, 0), out_t)
                vert2, in_t = _get_vt((i+1) % len(self.points))
                cloned.add_point(vert2, in_t, NVector(0, 0))

        return cloned

    def scale(self, amount):
        for vl in (self.vertices, self.in_tangents, self.out_tangents):
            for v in vl:
                v *= amount

    def lerp(self, other, t):
        if len(other.vertices) != len(self.vertices):
            if t < 1:
                return self.clone()
            return other.clone()

        bez = Bezier()
        bez.closed = self.closed

        for vlist_name in ["vertices", "in_tangents", "out_tangents"]:
            vlist = getattr(self, vlist_name)
            olist = getattr(other, vlist_name)
            out = getattr(bez, vlist_name)
            for v, o in zip(vlist, olist):
                out.append(v.lerp(o, t))

        return bez

    def rough_length(self):
        if len(self.vertices) < 2:
            return 0
        last = self.vertices[0]
        length = 0
        for v in self.vertices[1:]:
            length += (v-last).length
            last = v
        if self.closed:
            length += (last-self.vertices[0]).length
        return length
