from .base import LottieEnum


## @ingroup Lottie
class TestBased(LottieEnum):
    Characters = 1
    CharacterExcludingSpaces = 2
    Words = 3
    Lines = 4

    @classmethod
    def default(cls):
        return cls.Characters


## @ingroup Lottie
class TextShape(LottieEnum):
    Square = 1
    RampUp = 2
    RampDown = 3
    Triangle = 4
    Round = 5
    Smooth = 6

    @classmethod
    def default(cls):
        return cls.Square


## @ingroup Lottie
class TextGrouping(LottieEnum):
    Characters = 1
    Word = 2
    Line = 3
    All = 4

    @classmethod
    def default(cls):
        return cls.Characters
