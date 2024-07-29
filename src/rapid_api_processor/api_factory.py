from processors import MboumScreener, FearGreedIndex


class ApiFactory:

    def __init__(self):
        self._creators = {}

    def register_format(self, name, creator):
        self._creators[name] = creator

    def get_processor(self, name):
        creator = self._creators.get(name)
        if not creator:
            raise ValueError(name)
        return creator()


class ObjectProcessor:

    @staticmethod
    def process(service, endpoint):
        processor = factory.get_processor(service)
        processor.create(service, endpoint)
        processor.download_and_save()


factory = ApiFactory()
factory.register_format('mboum_screener', MboumScreener)
factory.register_format('fgi', FearGreedIndex)
