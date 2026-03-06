import enum
import inspect
import importlib
from .nvector import NVector
from .color import Color


class LottieBase:
    """!
    Base class for Lottie JSON objects bindings
    """
    def to_dict(self):
        """!
        Serializes into a JSON object fit for the Lottie format
        """
        raise NotImplementedError

    @classmethod
    def load(cls, lottiedict):
        """!
        Loads from a JSON object
        @returns An instance of the class
        """
        raise NotImplementedError

    def clone(self):
        """!
        Returns a copy of the object
        """
        raise NotImplementedError


class EnumMeta(enum.EnumMeta):
    """!
    Hack to counter-hack the hack in enum meta
    """
    def __new__(cls, name, bases, classdict):
        classdict["__reduce_ex__"] = lambda *a, **kw: None  # pragma: no cover
        return super().__new__(cls, name, bases, classdict)


class LottieEnum(LottieBase, enum.Enum, metaclass=EnumMeta):
    """!
    Base class for enum-like types in the Lottie JSON structure
    """
    def to_dict(self):
        return self.value

    @classmethod
    def load(cls, lottieint):
        return cls(lottieint)

    def clone(self):
        return self


class PseudoList:
    """!
    List tag for some weird values in the Lottie JSON
    """
    pass


class LottieValueConverter:
    """!
    Factory for property types that require special conversions
    """
    def __init__(self, py, lottie, name=None):
        self.py = py
        self.lottie = lottie
        self.name = name or "%s but displayed as %s" % (self.py.__name__, self.lottie.__name__)

    def py_to_lottie(self, val):
        return self.lottie(val)

    def lottie_to_py(self, val):
        return self.py(val)

    @property
    def __name__(self):
        return self.name


## For values in Lottie that are bools but ints in the JSON
PseudoBool = LottieValueConverter(bool, int, "0-1 int")


class LottieProp:
    """!
    Lottie <-> Python property mapper
    """
    def __init__(self, name, lottie, type=float, list=False, cond=None):
        ## Name of the Python property
        self.name = name
        ## Name of the Lottie JSON property
        self.lottie = lottie
        ## Type of the property
        ## @see LottieValueConverter, PseudoBool
        self.type = type
        ## Whether the property is a list of self.type
        ## @see PseudoList
        self.list = list
        ## Condition on when the property is loaded from the Lottie JSON
        self.cond = cond

    def get(self, obj):
        """!
        Returns the value of the property from a Python object
        """
        return getattr(obj, self.name)

    def set(self, obj, value):
        """!
        Sets the value of the property from a Python object
        """
        if isinstance(getattr(obj.__class__, self.name, None), property):
            return
        return setattr(obj, self.name, value)

    def load_from_parent(self, lottiedict):
        """!
        Returns the value for this property from a JSON dict representing the parent object
        @returns The loaded value or @c None if the property is not in @p lottiedict
        """
        if self.lottie in lottiedict:
            return self.load(lottiedict[self.lottie])
        return None

    def load_into(self, lottiedict, obj):
        """!
        Loads from a Lottie dict into an object
        """
        if self.cond and not self.cond(lottiedict):
            return
        self.set(obj, self.load_from_parent(lottiedict))

    def load(self, lottieval):
        """!
        Loads the property from a JSON value
        @returns the Python equivalent of the JSON value
        """
        if self.list is PseudoList and isinstance(lottieval, list):
            return self._load_scalar(lottieval[0])
            #return [
                #self._load_scalar(it)
                #for it in lottieval
            #]
        elif self.list is True:
            return list(filter(lambda x: x is not None, (
                self._load_scalar(it)
                for it in lottieval
            )))
        return self._load_scalar(lottieval)

    def _load_scalar(self, lottieval):
        if lottieval is None:
            return None
        if inspect.isclass(self.type) and issubclass(self.type, LottieBase):
            return self.type.load(lottieval)
        elif isinstance(self.type, type) and isinstance(lottieval, self.type):
            return lottieval
        elif isinstance(self.type, LottieValueConverter):
            return self.type.lottie_to_py(lottieval)
        elif self.type is NVector:
            return NVector(*lottieval)
        elif self.type is Color:
            return Color(*lottieval)
        if isinstance(lottieval, list) and lottieval:
            lottieval = lottieval[0]
        return self.type(lottieval)

    def to_dict(self, obj):
        """!
        Converts the value of the property as from @p obj into a JSON value
        @param obj LottieObject with this property
        """
        val = self._basic_to_dict(self.get(obj))
        if self.list is PseudoList:
            if not isinstance(obj, list):
                return [val]
        elif isinstance(self.type, LottieValueConverter):
            val = self._basic_to_dict(self.type.py_to_lottie(val))
        return val

    def _basic_to_dict(self, v):
        if isinstance(v, LottieBase):
            return v.to_dict()
        elif isinstance(v, NVector):
            return list(map(self._basic_to_dict, v.components))
        elif isinstance(v, list):
            return list(map(self._basic_to_dict, v))
        elif isinstance(v, (int, str, bool)):
            return v
        elif isinstance(v, float):
            if v % 1 == 0:
                return int(v)
            return v #round(v, 3)
        else:
            raise Exception("Unknown value %r" % v)

    def __repr__(self):
        return "<LottieProp %s:%s>" % (self.name, self.lottie)

    def clone_value(self, value):
        if isinstance(value, list):
            return [self.clone_value(v) for v in value]
        if isinstance(value, (LottieBase, NVector)):
            return value.clone()
        if isinstance(value, (int, float, bool, str)) or value is None:
            return value
        raise Exception("Could not convert %r" % value)


class LottieObjectMeta(type):
    def __new__(cls, name, bases, attr):
        props = []
        for base in bases:
            if type(base) == cls:
                props += base._props
        attr["_props"] = props + attr.get("_props", [])
        return super().__new__(cls, name, bases, attr)


class LottieObject(LottieBase, metaclass=LottieObjectMeta):
    """!
    @brief Base class for mapping Python classes into Lottie JSON objects
    """
    def to_dict(self):
        return {
            prop.lottie: prop.to_dict(self)
            for prop in self._props
            if prop.get(self) is not None
        }

    @classmethod
    def load(cls, lottiedict):
        if "__pyclass" in lottiedict:
            return CustomObject.load(lottiedict)
        if not lottiedict:
            return None
        cls = cls._load_get_class(lottiedict)
        obj = cls()
        for prop in cls._props:
            prop.load_into(lottiedict, obj)
        return obj

    @classmethod
    def _load_get_class(cls, lottiedict):
        return cls

    def find(self, search, propname="name"):
        """!
        @param search   The value of the property to search
        @param propname The name of the property used to search
        @brief Recursively searches for child objects with a matching property
        """
        if getattr(self, propname, None) == search:
            return self
        for prop in self._props:
            v = prop.get(self)
            if isinstance(v, LottieObject):
                found = v.find(search, propname)
                if found:
                    return found
            elif isinstance(v, list) and v and isinstance(v[0], LottieObject):
                for obj in v:
                    found = obj.find(search, propname)
                    if found:
                        return found
        return None

    def find_all(self, type, predicate=None, include_self=True):
        """!
        Find all child objects that match a predicate
        @param type         Type (or tuple of types) of the objects to match
        @param predicate    Function that returns true on the objects to find
        @param include_self Whether should counsider `self` for a potential match
        """

        if isinstance(self, type) and include_self:
            if not predicate or predicate(self):
                yield self

        for prop in self._props:
            v = prop.get(self)

            if isinstance(v, LottieObject):
                for found in v.find_all(type, predicate, True):
                    yield found
            elif isinstance(v, list) and v and isinstance(v[0], LottieObject):
                for child in v:
                    for found in child.find_all(type, predicate, True):
                        yield found

    def clone(self):
        obj = self.__class__()
        for prop in self._props:
            v = prop.get(self)
            prop.set(obj, prop.clone_value(v))
        return obj

    def __str__(self):
        return type(self).__name__


class Index:
    """!
    @brief Simple iterator to generate increasing integers
    """
    def __init__(self):
        self._i = -1

    def __next__(self):
        self._i += 1
        return self._i


class CustomObject(LottieObject):
    """!
    Allows extending the Lottie shapes with custom Python classes
    """
    wrapped_lottie = LottieObject

    def __init__(self):
        self.wrapped = self.wrapped_lottie()

    @classmethod
    def load(cls, lottiedict):
        ld = lottiedict.copy()
        classname = ld.pop("__pyclass")
        modn, clsn = classname.rsplit(".", 1)
        subcls = getattr(importlib.import_module(modn), clsn)
        obj = subcls()
        for prop in subcls._props:
            prop.load_into(lottiedict, obj)
        obj.wrapped = subcls.wrapped_lottie.load(ld)
        return obj

    def clone(self):
        obj = self.__class__(**self.to_pyctor())
        obj.wrapped = self.wrapped.clone()
        return obj

    def to_dict(self):
        dict = self.wrapped.to_dict()
        dict["__pyclass"] = "{0.__module__}.{0.__name__}".format(self.__class__)
        dict.update(LottieObject.to_dict(self))
        return dict

    def _build_wrapped(self):
        return self.wrapped_lottie()

    def refresh(self):
        self.wrapped = self._build_wrapped()


class ObjectVisitor:
    DONT_RECURSE = object()

    def __call__(self, lottie_object):
        self._process(lottie_object)

    def _process(self, lottie_object):
        self.visit(lottie_object)
        for p in lottie_object._props:
            pval = p.get(lottie_object)
            if self.visit_property(lottie_object, p, pval) is not self.DONT_RECURSE:
                if isinstance(pval, LottieObject):
                    self._process(pval)
                elif isinstance(pval, list) and pval and isinstance(pval[0], LottieObject):
                    for c in pval:
                        self._process(c)

    def visit(self, object):
        pass

    def visit_property(self, object, property, value):
        pass
