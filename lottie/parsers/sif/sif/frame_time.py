import enum


class FrameTime:
    class Unit(enum.Enum):
        Frame = "f"
        Seconds = "s"

    def __init__(self, value, unit):
        self.value = value
        self.unit = unit

    def __eq__(self, other):
        return self.value == other.value and self.unit == other.unit

    def __ne__(self, other):
        return self.value == other.value and self.unit == other.unit

    def __str__(self):
        return "%s%s" % (self.value, self.unit.value)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self)

    @classmethod
    def frame(cls, amount):
        return cls(amount, cls.Unit.Frame)

    @classmethod
    def seconds(cls, amount):
        return cls(amount, cls.Unit.Seconds)

    @classmethod
    def parse_string(cls, value_str, canvas):
        if " " in value_str:
            value = 0
            unit = cls.Unit.Frame
            for sub in value_str.split():
                sv = float(sub[:-1])
                if sub[-1] == "s":
                    sv *= canvas.fps
                value += sv
        else:
            value = float(value_str[:-1])
            unit = cls.Unit(value_str[-1])
        return FrameTime(value, unit)
