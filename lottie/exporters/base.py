from ..parsers.baseporter import Baseporter, Loader, ExtraOption, io_progress


class ExporterLoader(Loader):
    def __init__(self):
        super().__init__(__file__, __name__, "export")

    @property
    def exporters(self):
        return self.items

    def set_options(self, parser):
        group = parser.add_argument_group("Generic output options")
        group.add_argument(
            "--pretty", "-p",
            action="store_true",
            help="Pretty print (for formats that support it)",
        )
        group.add_argument(
            "--frame",
            type=int,
            default=0,
            help="Frame to extract (for single-image formats)",
        )

        super().set_options(parser)

        return group


exporters = ExporterLoader()
exporter = exporters.decorator
