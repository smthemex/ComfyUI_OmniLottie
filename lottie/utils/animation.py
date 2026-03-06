import random
import math
from ..nvector import NVector
from ..objects.shapes import Path
from .. import objects
from ..objects import easing
from ..objects import properties


def shake(position_prop, x_radius, y_radius, start_time, end_time, n_frames, interp=easing.Linear()):
    if not isinstance(position_prop, list):
        position_prop = [position_prop]

    n_frames = int(round(n_frames))
    frame_time = (end_time - start_time) / n_frames
    startpoints = list(map(
        lambda pp: pp.get_value(start_time),
        position_prop
    ))

    for i in range(n_frames):
        x = (random.random() * 2 - 1) * x_radius
        y = (random.random() * 2 - 1) * y_radius
        for pp, start in zip(position_prop, startpoints):
            px = start[0] + x
            py = start[1] + y
            pp.add_keyframe(start_time + i * frame_time, NVector(px, py), interp)

    for pp, start in zip(position_prop, startpoints):
        pp.add_keyframe(end_time, start, interp)


def rot_shake(rotation_prop, angles, start_time, end_time, n_frames):
    frame_time = (end_time - start_time) / n_frames
    start = rotation_prop.get_value(start_time)

    for i in range(0, n_frames):
        a = angles[i % len(angles)] * math.sin(i/n_frames * math.pi)
        rotation_prop.add_keyframe(start_time + i * frame_time, start + a)
    rotation_prop.add_keyframe(end_time, start)


def spring_pull(position_prop, point, start_time, end_time, falloff=15, oscillations=7):
    start = position_prop.get_value(start_time)
    d = start-point

    delta = (end_time - start_time) / oscillations

    for i in range(oscillations):
        time_x = i / oscillations
        factor = math.cos(time_x * math.pi * oscillations) * (1-time_x**(1/falloff))
        p = point + d * factor
        position_prop.add_keyframe(start_time + delta * i, p)

    position_prop.add_keyframe(end_time, point)


def follow_path(position_prop, bezier, start_time, end_time, n_keyframes,
                reverse=False, offset=NVector(0, 0), start_t=0, rotation_prop=None, rotation_offset=0):
    delta = (end_time - start_time) / (n_keyframes-1)
    fact = start_t
    factd = 1 / (n_keyframes-1)

    if rotation_prop:
        start_rot = rotation_prop.get_value(start_time) if rotation_offset is None else rotation_offset

    for i in range(n_keyframes):
        time = start_time + i * delta

        if fact > 1 + factd/2:
            fact -= 1
            if time != start_time:
                easing.Jump()(position_prop.keyframes[-1])
                if rotation_prop:
                    easing.Jump()(rotation_prop.keyframes[-1])

        f = 1 - fact if reverse else fact
        position_prop.add_keyframe(time, bezier.point_at(f)+offset)

        if rotation_prop:
            rotation_prop.add_keyframe(time, bezier.tangent_angle_at(f) / math.pi * 180 + start_rot)

        fact += factd


def generate_path_appear(bezier, appear_start, appear_end, n_keyframes, reverse=False):
    obj = Path()
    beziers = []
    maxp = 0

    time_delta = (appear_end - appear_start) / n_keyframes
    for i in range(n_keyframes+1):
        time = appear_start + i * time_delta
        t2 = (time - appear_start) / (appear_end - appear_start)

        if reverse:
            t2 = 1 - t2
            segment = bezier.segment(t2, 1)
            segment.reverse()
        else:
            segment = bezier.segment(0, t2)

        beziers.append(segment)
        if len(segment.vertices) > maxp:
            maxp = len(segment.vertices)

        obj.shape.add_keyframe(time, segment)

    for segment in beziers:
        deltap = maxp - len(segment.vertices)
        if deltap > 0:
            segment.vertices += [segment.vertices[-1]] * deltap
            segment.in_tangents += [NVector(0, 0)] * deltap
            segment.out_tangents += [NVector(0, 0)] * deltap

    return obj


def generate_path_disappear(bezier, disappear_start, disappear_end, n_keyframes, reverse=False):
    obj = Path()
    beziers = []
    maxp = 0

    time_delta = (disappear_end - disappear_start) / n_keyframes
    for i in range(n_keyframes+1):
        time = disappear_start + i * time_delta
        t1 = (time - disappear_start) / (disappear_end - disappear_start)
        if reverse:
            t1 = 1 - t1
            segment = bezier.segment(0, t1)
        else:
            segment = bezier.segment(1, t1)
            segment.reverse()

        beziers.append(segment)
        if len(segment.vertices) > maxp:
            maxp = len(segment.vertices)

        obj.shape.add_keyframe(time, segment)

    for segment in beziers:
        deltap = maxp - len(segment.vertices)
        if deltap > 0:
            segment.vertices += [segment.vertices[-1]] * deltap
            segment.in_tangents += [NVector(0, 0)] * deltap
            segment.out_tangents += [NVector(0, 0)] * deltap

    return obj


def generate_path_segment(bezier, appear_start, appear_end, disappear_start, disappear_end, n_keyframes, reverse=False):
    obj = Path()
    beziers = []
    maxp = 0

    # HACK: For some reson reversed works better
    if not reverse:
        bezier.reverse()

    time_delta = (appear_end - appear_start) / n_keyframes
    for i in range(n_keyframes+1):
        time = appear_start + i * time_delta
        t1 = (time - disappear_start) / (disappear_end - disappear_start)
        t2 = (time - appear_start) / (appear_end - appear_start)

        t1 = max(0, min(1, t1))
        t2 = max(0, min(1, t2))

        #if reverse:
        if True:
            t1 = 1 - t1
            t2 = 1 - t2
            segment = bezier.segment(t2, t1)
            segment.reverse()
        #else:
            #segment = bezier.segment(t1, t2)
            #segment.reverse()

        beziers.append(segment)
        if len(segment.vertices) > maxp:
            maxp = len(segment.vertices)

        obj.shape.add_keyframe(time, segment)

    for segment in beziers:
        deltap = maxp - len(segment.vertices)
        if deltap > 0:
            segment.split_self_chunks(deltap+1)

    # HACK: Restore
    if not reverse:
        bezier.reverse()
    return obj


class PointDisplacer:
    def __init__(self, time_start, time_end, n_frames):
        """!
        @param time_start   When the animation shall start
        @param time_end     When the animation shall end
        @param n_frames     Number of frames in the animation
        """
        ## When the animation shall start
        self.time_start = time_start
        ## When the animation shall end
        self.time_end = time_end
        ## Number of frames in the animation
        self.n_frames = n_frames
        ## Length of a frame
        self.time_delta = (time_end - time_start) / n_frames

    def animate_point(self, prop):
        startpos = prop.get_value(self.time_start)
        for f in range(self.n_frames+1):
            p = self._on_displace(startpos, f)
            prop.add_keyframe(self.frame_time(f), startpos+p)

    def _on_displace(self, startpos, f):
        raise NotImplementedError()

    def animate_bezier(self, prop):
        initial = prop.get_value(self.time_start)

        for f in range(self.n_frames+1):
            bezier = objects.Bezier()
            bezier.closed = initial.closed

            for pi in range(len(initial.vertices)):
                startpos = initial.vertices[pi]
                dp = self._on_displace(startpos, f)
                t1sp = initial.in_tangents[pi] + startpos
                t1fin = initial.in_tangents[pi] + self._on_displace(t1sp, f) - dp
                t2sp = initial.out_tangents[pi] + startpos
                t2fin = initial.out_tangents[pi] + self._on_displace(t2sp, f) - dp

                bezier.add_point(dp + startpos, t1fin, t2fin)

            prop.add_keyframe(self.frame_time(f), bezier)

    def frame_time(self, f):
        return f * self.time_delta + self.time_start

    def _init_lerp(self, val_from, val_to, easing):
        self._kf = properties.OffsetKeyframe(0, NVector(val_from), NVector(val_to), easing)

    def _lerp_get(self, offset):
        return self._kf.interpolated_value(offset / self.n_frames)[0]


class SineDisplacer(PointDisplacer):
    def __init__(
        self,
        wavelength,
        amplitude,
        time_start,
        time_end,
        n_frames,
        speed=1,
        axis=90,
    ):
        """!
        Displaces points as if they were following a sine wave

        @param wavelength  Distance between consecutive peaks
        @param amplitude   Distance from a peak to the original position
        @param time_start  When the animation shall start
        @param time_end    When the animation shall end
        @param n_frames    Number of keyframes to add
        @param speed       Number of peaks a point will go through in the given time
                           If negative, it will go the other way
        @param axis        Wave peak direction
        """
        super().__init__(time_start, time_end, n_frames)

        self.wavelength = wavelength
        self.amplitude = amplitude
        self.speed_f = math.pi * 2 * speed
        self.axis = axis / 180 * math.pi

    def _on_displace(self, startpos, f):
        off = -math.sin(startpos[0]/self.wavelength*math.pi*2-f*self.speed_f/self.n_frames) * self.amplitude
        return NVector(off * math.cos(self.axis), off * math.sin(self.axis))


class MultiSineDisplacer(PointDisplacer):
    def __init__(
        self,
        waves,
        time_start,
        time_end,
        n_frames,
        speed=1,
        axis=90,
        amplitude_scale=1,
    ):
        """!
        Displaces points as if they were following a sine wave

        @param waves       List of tuples (wavelength, amplitude)
        @param time_start  When the animation shall start
        @param time_end    When the animation shall end
        @param n_frames    Number of keyframes to add
        @param speed       Number of peaks a point will go through in the given time
                           If negative, it will go the other way
        @param axis        Wave peak direction
        @param amplitude_scale  Multiplies the resulting amplitude by this factor
        """
        super().__init__(time_start, time_end, n_frames)

        self.waves = waves
        self.speed_f = math.pi * 2 * speed
        self.axis = axis / 180 * math.pi
        self.amplitude_scale = amplitude_scale

    def _on_displace(self, startpos, f):
        off = 0
        for wavelength, amplitude in self.waves:
            off -= math.sin(startpos[0]/wavelength*math.pi*2-f*self.speed_f/self.n_frames) * amplitude

        off *= self.amplitude_scale
        return NVector(off * math.cos(self.axis), off * math.sin(self.axis))


class DepthRotationAxis:
    def __init__(self, x, y, keep):
        self.x = x / x.length
        self.y = y / y.length
        self.keep = keep / keep.length # should be the cross product

    def rot_center(self, center, point):
        return (
            self.x * self.x.dot(center) +
            self.y * self.y.dot(center) +
            self.keep * self.keep.dot(point)
        )

    def extract_component(self, vector, axis):
        return sum(vector.element_scaled(axis).components)

    @classmethod
    def from_points(cls, keep_point, center=NVector(0, 0, 0)):
        keep = keep_point - center
        keep /= keep.length
        # Hughes-Moller to find x and y
        if abs(keep.x) > abs(keep.z):
            y = NVector(-keep.y, keep.x, 0)
        else:
            y = NVector(0, -keep.z, keep.y)
        y /= y.length
        x = y.cross(keep)
        return cls(x, y, keep)


class DepthRotation:
    axis_x = DepthRotationAxis(NVector(0, 0, 1), NVector(0, 1, 0), NVector(1, 0, 0))
    axis_y = DepthRotationAxis(NVector(1, 0, 0), NVector(0, 0, 1), NVector(0, 1, 0))
    axis_z = DepthRotationAxis(NVector(1, 0, 0), NVector(0, 1, 0), NVector(0, 0, 1))

    def __init__(self, center):
        self.center = center

    def rotate3d_y(self, point, angle):
        return self.rotate3d(point, angle, self.axis_y)
        # Hard-coded version:
        #c = NVector(self.center.x, point.y, self.center.z)
        #rad = angle * math.pi / 180
        #delta = point - c
        #pol_l = delta.length
        #pol_a = math.atan2(delta.z, delta.x)
        #dest_a = pol_a + rad
        #return NVector(
        #    c.x + pol_l * math.cos(dest_a),
        #    point.y,
        #    c.z + pol_l * math.sin(dest_a)
        #)

    def rotate3d_x(self, point, angle):
        return self.rotate3d(point, angle, self.axis_x)
        # Hard-coded version:
        #c = NVector(point.x, self.center.y, self.center.z)
        #rad = angle * math.pi / 180
        #delta = point - c
        #pol_l = delta.length
        #pol_a = math.atan2(delta.y, delta.z)
        #dest_a = pol_a + rad
        #return NVector(
        #    point.x,
        #    c.y + pol_l * math.sin(dest_a),
        #    c.z + pol_l * math.cos(dest_a),
        #)

    def rotate3d_z(self, point, angle):
        return self.rotate3d(point, angle, self.axis_z)

    def rotate3d(self, point, angle, axis):
        c = axis.rot_center(self.center, point)
        rad = angle * math.pi / 180
        delta = point - c
        pol_l = delta.length
        pol_a = math.atan2(
            axis.extract_component(delta, axis.y),
            axis.extract_component(delta, axis.x)
        )
        dest_a = pol_a + rad
        return c + axis.x * pol_l * math.cos(dest_a) + axis.y * pol_l * math.sin(dest_a)


class DepthRotationDisplacer(PointDisplacer):
    axis_x = DepthRotation.axis_x
    axis_y = DepthRotation.axis_y
    axis_z = DepthRotation.axis_z

    def __init__(self, center, time_start, time_end, n_frames, axis,
                 depth=0, angle=360, anglestart=0, ease=easing.Linear()):
        super().__init__(time_start, time_end, n_frames)
        self.rotation = DepthRotation(center)
        if isinstance(axis, NVector):
            axis = DepthRotationAxis.from_points(axis)
        self.axis = axis
        self.depth = depth
        self._angle = angle
        self.anglestart = anglestart
        self.ease = ease
        self._init_lerp(0, angle, ease)

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        self._angle = value
        self._init_lerp(0, value, self.ease)

    def _on_displace(self, startpos, f):
        angle = self.anglestart + self._lerp_get(f)
        if len(startpos) < 3:
            startpos = NVector(*(startpos.components + [self.depth]))
        return self.rotation.rotate3d(startpos, angle, self.axis) - startpos


class EnvelopeDeformation(PointDisplacer):
    def __init__(self, topleft, bottomright):
        self.topleft = topleft
        self.size = bottomright - topleft
        self.keyframes = []

    @property
    def time_start(self):
        return self.keyframes[0][0]

    def add_reset_keyframe(self, time):
        self.add_keyframe(
            time,
            self.topleft.clone(),
            NVector(self.topleft.x + self.size.x, self.topleft.y),
            NVector(self.topleft.x + self.size.x, self.topleft.y + self.size.y),
            NVector(self.topleft.x, self.topleft.y + self.size.y),
        )

    def add_keyframe(self, time, tl, tr, br, bl):
        self.keyframes.append([
            time,
            tl.clone(),
            tr.clone(),
            br.clone(),
            bl.clone()
        ])

    def _on_displace(self, startpos, f):
        _, tl, tr, br, bl = self.keyframes[f]
        relp = startpos - self.topleft
        relp.x /= self.size.x
        relp.y /= self.size.y

        x1 = tl.lerp(tr, relp.x)
        x2 = bl.lerp(br, relp.x)

        #return x1.lerp(x2, relp.y)
        return x1.lerp(x2, relp.y) - startpos

    @property
    def n_frames(self):
        return len(self.keyframes)-1

    def frame_time(self, f):
        return self.keyframes[f][0]


class DisplacerDampener(PointDisplacer):
    """!
    Given a displacer and a function that returns a factor for a point,
    multiplies the effect of the displacer by the factor
    """
    def __init__(self, displacer, dampener):
        self.displacer = displacer
        self.dampener = dampener

    @property
    def time_start(self):
        return self.displacer.time_start

    def _on_displace(self, startpos, f):
        disp = self.displacer._on_displace(startpos, f)
        damp = self.dampener(startpos)
        return disp * damp

    @property
    def n_frames(self):
        return self.displacer.n_frames

    def frame_time(self, f):
        return self.displacer.frame_time(f)


class FollowDisplacer(PointDisplacer):
    def __init__(
        self,
        origin,
        range,
        offset_func,
        time_start, time_end, n_frames,
        falloff_exp=1,
    ):
        """!
        @brief Uses a custom offset function, and applies a falloff to the displacement

        @param origin       Origin point for the falloff
        @param range        Radius after which the points will not move
        @param offset_func  Function returning an offset given a ratio of the time
        @param time_start   When the animation shall start
        @param time_end     When the animation shall end
        @param n_frames     Number of frames in the animation
        @param falloff_exp  Exponent for the falloff
        """
        super().__init__(time_start, time_end, n_frames)
        self.origin = origin
        self.range = range
        self.offset_func = offset_func
        self.falloff_exp = falloff_exp

    def _on_displace(self, startpos, f):
        influence = 1 - min(1, (startpos - self.origin).length / self.range) ** self.falloff_exp
        return self.offset_func(f / self.n_frames) * influence
