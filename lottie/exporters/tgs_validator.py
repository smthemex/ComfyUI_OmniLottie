import os
import enum
import json
import inspect

from ..parsers.tgs import parse_tgs
from ..objects.base import ObjectVisitor
from ..objects.animation import Animation
from ..objects import layers
from ..objects import shapes
from ..objects import helpers


class Severity(enum.Enum):
    Note = enum.auto()
    Warning = enum.auto()
    Error = enum.auto()


class TgsError:
    def __init__(self, message, target, severity=Severity.Warning):
        self.message = message
        self.target = target
        self.severity = severity

    def target_id(self):
        if isinstance(self.target, str):
            return self.target
        if getattr(self.target, "name", ""):
            return self.target.name
        return self.target.__class__.__name__

    def __str__(self):
        return "%s: on %s: %s" % (
            self.severity.name,
            self.target_id(),
            self.message
        )


class TgsValidator(ObjectVisitor):
    def __init__(self, severity=Severity.Note):
        self.errors = []
        self.severity = severity

    def _check(self, expr, message, target, severity=Severity.Warning):
        if severity.value >= self.severity.value and not expr:
            self.errors.append(TgsError(message, target, severity))

    def check_file_size(self, filename):
        return self.check_size(os.path.getsize(filename))

    def check_size(self, bytes, filename="file"):
        size_k = bytes / 1024
        self._check(
            size_k <= 64,
            "Invalid size (%.1fk), should be less than 64k" % size_k,
            filename,
            Severity.Error
        )

    def check_file(self, filename):
        self.check_file_size(filename)
        try:
            self(parse_tgs(filename))
        except json.decoder.JSONDecodeError as e:
            self._check(
                False,
                "Invalid JSON: %s" % e,
                filename,
                Severity.Error
            )

    def visit(self, object):
        for cls in inspect.getmro(object.__class__):
            callback = "_visit_%s" % cls.__name__.lower()
            if hasattr(self, callback):
                getattr(self, callback)(object)

    def _visit_animation(self, o: Animation):
        self._check(
            o.frame_rate in {30, 60},
            "Invalid framerate %s, should be 30 or 60" % o.frame_rate,
            o,
            Severity.Error
        )
        self._check(
            o.width == 512,
            "Invalid width %s, should be 512" % o.width,
            o,
            Severity.Error
        )
        self._check(
            o.height == 512,
            "Invalid height %s, should be 512" % o.height,
            o,
            Severity.Error
        )
        self._check(
            (o.out_point-o.in_point) <= 180,
            "Too many frames (%s), should be less than 180" % (o.out_point-o.in_point),
            o,
            Severity.Error
        )

    def _visit_layer(self, o: layers.Layer):
        self._check(
            not o.has_masks and not o.masks,
            "Masks are not officially supported",
            o,
            Severity.Note
        )
        self._check(
            not o.effects,
            "Effects are not supported",
            o,
            Severity.Warning
        )
        self._check(
            not o.threedimensional,
            "3D layers are not supported",
            o,
            Severity.Warning
        )
        self._check(
            not isinstance(o, layers.TextLayer),
            "Text layers are not supported",
            o,
            Severity.Warning
        )
        self._check(
            not isinstance(o, layers.ImageLayer),
            "Image layers are not supported",
            o,
            Severity.Warning
        )
        self._check(
            not o.auto_orient,
            "Auto-orient layers are not supported",
            o,
            Severity.Warning
        )
        self._check(
            o.matte_mode in {None, layers.MatteMode.Normal},
            "Mattes are not supported",
            o,
            Severity.Warning
        )

    def _visit_precomplayer(self, o: layers.PreCompLayer):
        self._check(
            o.time_remapping is None,
            "Time remapping is not supported",
            o,
            Severity.Warning
        )

    def _visit_merge(self, o: shapes.Merge):
        self._check(
            False,
            "Merge paths are not supported",
            o,
            Severity.Warning
        )

    def _visit_transform(self, o: helpers.Transform):
        self._check(
            o.skew is None or (
                not o.skew.animated and o.skew.value == 0
            ),
            "Skew transforms are not supported",
            o,
            Severity.Warning
        )

    def _visit_gradientstroke(self, o: shapes.GradientStroke):
        self._check(
            False,
            "Gradient strokes are not officially supported",
            o,
            Severity.Note
        )

    def _visit_star(self, o: shapes.Star):
        self._check(
            False,
            "Star Shapes are not officially supported",
            o,
            Severity.Note
        )

    def _visit_repeater(self, o: shapes.Repeater):
        self._check(
            False,
            "Repeaters are not officially supported",
            o,
            Severity.Note
        )
