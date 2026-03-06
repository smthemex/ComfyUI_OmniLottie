import math

from ..nvector import NVector
from ..objects.bezier import BezierPoint


## @todo Just output a Bezier object
class Ellipse:
    def __init__(self, center, radii, xrot):
        """
        @param center      2D vector, center of the ellipse
        @param radii       2D vector, x/y radius of the ellipse
        @param xrot        Angle between the main axis of the ellipse and the x axis (in radians)
        """
        self.center = center
        self.radii = radii
        self.xrot = xrot

    def point(self, t):
        return NVector(
            self.center[0]
            + self.radii[0] * math.cos(self.xrot) * math.cos(t)
            - self.radii[1] * math.sin(self.xrot) * math.sin(t),

            self.center[1]
            + self.radii[0] * math.sin(self.xrot) * math.cos(t)
            + self.radii[1] * math.cos(self.xrot) * math.sin(t)
        )

    def derivative(self, t):
        return NVector(
            - self.radii[0] * math.cos(self.xrot) * math.sin(t)
            - self.radii[1] * math.sin(self.xrot) * math.cos(t),

            - self.radii[0] * math.sin(self.xrot) * math.sin(t)
            + self.radii[1] * math.cos(self.xrot) * math.cos(t)
        )

    def to_bezier(self, anglestart, angle_delta):
        points = []
        angle1 = anglestart
        angle_left = abs(angle_delta)
        step = math.pi / 2
        sign = -1 if anglestart+angle_delta < angle1 else 1

        # We need to fix the first handle
        firststep = min(angle_left, step) * sign
        alpha = self._alpha(firststep)
        q1 = self.derivative(angle1) * alpha
        points.append(BezierPoint(self.point(angle1), NVector(0, 0), q1))

        # Then we iterate until the angle has been completed
        tolerance = step / 2
        while angle_left > tolerance:
            lstep = min(angle_left, step)
            step_sign = lstep * sign
            angle2 = angle1 + step_sign
            angle_left -= abs(lstep)

            alpha = self._alpha(step_sign)
            p2 = self.point(angle2)
            q2 = self.derivative(angle2) * alpha

            points.append(BezierPoint(p2, -q2, q2))
            angle1 = angle2
        return points

    def _alpha(self, step):
        return math.sin(step) * (math.sqrt(4+3*math.tan(step/2)**2) - 1) / 3

    @classmethod
    def from_svg_arc(cls, start, rx, ry, xrot, large, sweep, dest):
        rx = abs(rx)
        ry = abs(ry)

        x1 = start[0]
        y1 = start[1]
        x2 = dest[0]
        y2 = dest[1]
        phi = math.pi * xrot / 180

        x1p, y1p = _matrix_mul(phi, (start-dest)/2, -1)

        cr = x1p ** 2 / rx**2 + y1p**2 / ry**2
        if cr > 1:
            s = math.sqrt(cr)
            rx *= s
            ry *= s

        dq = rx**2 * y1p**2 + ry**2 * x1p**2
        pq = (rx**2 * ry**2 - dq) / dq
        cpm = math.sqrt(max(0, pq))
        if large == sweep:
            cpm = -cpm
        cp = NVector(cpm * rx * y1p / ry, -cpm * ry * x1p / rx)
        c = _matrix_mul(phi, cp) + NVector((x1+x2)/2, (y1+y2)/2)
        theta1 = _angle(NVector(1, 0), NVector((x1p - cp[0]) / rx, (y1p - cp[1]) / ry))
        deltatheta = _angle(
            NVector((x1p - cp[0]) / rx, (y1p - cp[1]) / ry),
            NVector((-x1p - cp[0]) / rx, (-y1p - cp[1]) / ry)
        ) % (2*math.pi)

        if not sweep and deltatheta > 0:
            deltatheta -= 2*math.pi
        elif sweep and deltatheta < 0:
            deltatheta += 2*math.pi

        return cls(c, NVector(rx, ry), phi), theta1, deltatheta


def _matrix_mul(phi, p, sin_mul=1):
    c = math.cos(phi)
    s = math.sin(phi) * sin_mul

    xr = c * p.x - s * p.y
    yr = s * p.x + c * p.y
    return NVector(xr, yr)


def _angle(u, v):
    arg = math.acos(max(-1, min(1, u.dot(v) / (u.length * v.length))))
    if u[0] * v[1] - u[1] * v[0] < 0:
        return -arg
    return arg
