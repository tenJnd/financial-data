from datetime import datetime, timedelta

import pandas as pd
import requests

from src.config import FRED_API_KEY, FRED_MACRO_DATA  # Adjust imports as needed


class FredData:
    def __init__(self, series_ids=None):
        # Use provided series IDs or default to FRED_MACRO_DATA
        self.series_ids = series_ids or FRED_MACRO_DATA
        self.base_url = 'https://api.stlouisfed.org/fred/series/observations'
        self.api_key = FRED_API_KEY

    def get_data(self, look_back=2, return_full_data=True):
        start_date = self.calculate_start_date(look_back)
        fred_data = {}
        for name, series_id in self.series_ids.items():
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'observation_start': start_date,
                'observation_end': datetime.today().strftime('%Y-%m-%d')
            }
            response = requests.get(self.base_url, params=params)
            observations = response.json()['observations']

            # Convert observations to a pandas Series
            dates = [obs['date'] for obs in observations]
            values = [float(obs['value']) for obs in observations]

            fred_data[name] = pd.Series(data=values, index=pd.to_datetime(dates))

        # Convert the dictionary to a DataFrame
        fred_df = pd.DataFrame(fred_data)

        # Return full DataFrame or just the series data based on the parameter
        return fred_df if return_full_data else fred_df.tail(1)

    def calculate_start_date(self, look_back):
        # Calculate the start date based on the look_back period (in years)
        return (datetime.today() - timedelta(days=look_back * 365)).strftime('%Y-%m-%d')
