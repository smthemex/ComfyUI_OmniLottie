from ..parsers.baseporter import Baseporter, Loader


class ImporterLoader(Loader):
    def __init__(self):
        super().__init__(__file__, __name__, "import")

    @property
    def importers(self):
        return self.items

    def set_options(self, parser):
        group = parser.add_argument_group("Generic input options")

        super().set_options(parser)

        return group


importers = ImporterLoader()
importer = importers.decorator
