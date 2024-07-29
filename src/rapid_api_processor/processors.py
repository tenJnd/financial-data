import pandas as pd
import requests

from src.rapid_api_processor.processor_base import BaseProcessor


class MboumScreener(BaseProcessor):

    def __init__(self):
        super().__init__()

    def download_badge(self, start=0):
        # TODO params
        response = requests.request("GET", self._url,
                                    headers=self._headers,
                                    params={'start': start})
        return response.json()

    def download(self):

        result_data = pd.DataFrame()
        start = 0
        count = 1

        while count > 0:
            data_badge = self.download_badge(start)
            df = pd.DataFrame(data_badge['body'])
            if result_data.empty:
                result_data = df
            else:
                result_data = pd.concat([result_data, df], ignore_index=True)

            count = data_badge['meta']['count']
            start += count

        self.data = result_data

    def process(self):
        pass

    def download_and_save(self):
        self.download()
        self.process()
        BaseProcessor.save_base(self)


class FearGreedIndex(BaseProcessor):

    def __init__(self):
        super().__init__()

    def process(self):
        now = self.response_json['fgi']['now']

        self.data = pd.DataFrame(now, index=[0])

    def download_and_save(self):
        BaseProcessor.download_base(self)
        self.process()
        BaseProcessor.save_base(self)
