import sys
import os
import pkgutil
import argparse
import importlib


class Baseporter:
    def __init__(self, name, extensions, callback, extra_options=[], generic_options=set(), slug=None):
        self.name = name
        self.extensions = extensions
        self.callback = callback
        self.extra_options = extra_options
        self.generic_options = generic_options
        self.slug = slug if slug is not None else extensions[0]

    def process(self, *a, **kw):
        return self.callback(*a, **kw)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.slug)

    def argparse_options(self, ns):
        o_options = {}
        for opt in self.extra_options:
            o_options[opt.dest] = getattr(ns, opt.nsvar(self.slug))
        for opt in self.generic_options:
            o_options[opt] = getattr(ns, opt)
        return o_options


class ExtraOption:
    def __init__(self, name, **kwargs):
        self.name = name
        self.kwargs = kwargs
        if "action" not in self.kwargs:
            self.kwargs["metavar"] = self.name
        self.dest = kwargs.pop("dest", name)

    def add_argument(self, slug, parser):
        opt = "--%s-%s" % (slug, self.name.replace("_", "-"))
        parser.add_argument(opt, dest=self.nsvar(slug), **self.kwargs)

    def nsvar(self, slug):
        return "%s_%s" % (slug, self.dest)


def _add_options(parser, ie, object):
    if not object.extra_options:
        return

    suf = " %sing options" % ie
    group = parser.add_argument_group(object.name + suf)
    for op in object.extra_options:
        op.add_argument(object.slug, group)


class Loader:
    def __init__(self, module_path, module_name, ie):
        self._loaded = False
        self._registry = {}
        self._module_path = os.path.dirname(module_path)
        self._module_name = module_name.replace(".base", "")
        self._ie = ie
        self._failed = {}

    def load_modules(self):
        self._loaded = True

        for _, modname, _ in pkgutil.iter_modules([self._module_path]):
            if modname == "base":
                continue

            full_modname = "." + modname
            try:
                importlib.import_module(full_modname, self._module_name)
            except ImportError as e:
                self._failed[modname] = e.name

    @property
    def failed_modules(self):
        if not self._loaded:
            self.load_modules()

        return self._failed

    @property
    def items(self):
        if not self._loaded:
            self.load_modules()
        return self._registry

    def __iter__(self):
        return iter(self.items.values())

    def get(self, slug):
        return self.items.get(slug, None)

    def __getitem__(self, key):
        return self.get(key)

    def get_from_filename(self, filename):
        return self.get_from_extension(os.path.splitext(filename)[1][1:])

    def get_from_extension(self, ext):
        for p in self.items.values():
            if ext in p.extensions:
                return p
        return None

    def set_options(self, parser):
        for exporter in self.items.values():
            _add_options(parser, self._ie, exporter)

    def keys(self):
        return self.items.keys()

    def decorator(self, name, extensions, extra_options=[], generic_options=set(), slug=None):
        def decorator(callback):
            porter = Baseporter(name, extensions, callback, extra_options, generic_options, slug)
            self._registry[porter.slug] = porter
            return callback
        return decorator


class IoProgressReporter:
    def report_progress(self, title, value, total):
        sys.stderr.write("\r%s %s/%s" % (title, value, total))
        sys.stderr.flush()

    def report_message(self, message):
        sys.stderr.write("\r" + message + "\n")
        sys.stderr.flush()


IoProgressReporter.instance = IoProgressReporter()


def io_progress():
    return IoProgressReporter.instance
