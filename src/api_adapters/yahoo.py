import re

import pandas as pd
import yfinance as yf
from pyrate_limiter import Duration, RequestRate, Limiter
from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket

from src.config import MACRO_YDATA_TICKERS


class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    pass


def to_snake_case(s):
    # Replace spaces with underscores only if followed by an uppercase letter and a lowercase letter
    s = re.sub(r'(?<=\w) (?=[A-Z][a-z])', '_', s)
    # Replace sequences of uppercase letters followed by lowercase letters correctly
    s = re.sub(r'(?<!^)(?<!_)(?=[A-Z][a-z])', '_', s)
    s = re.sub(r'[^a-zA-Z0-9]', '_', s)
    return s.lower()


def normalize_column_names(df):
    normalized_columns = [to_snake_case(col) for col in df.columns]
    df.columns = normalized_columns
    return df


class YahooData:
    def __init__(self, ticker=None):
        self.ticker = ticker
        self.session = CachedLimiterSession(
            limiter=Limiter(RequestRate(2, Duration.SECOND * 5)),  # max 2 requests per 5 seconds
            bucket_class=MemoryQueueBucket,
            backend=SQLiteCache("yfinance.cache"),
        )
        self.ticker_data = yf.Ticker(ticker, session=self.session) if ticker else None

    def adjust_api_result(self, api_result, last_date_only):
        result = api_result.copy()
        if last_date_only:
            result = result.iloc[:1]

        result['ticker'] = self.ticker
        result.reset_index(inplace=True)
        result.rename(columns={'index': 'date'}, inplace=True)
        return normalize_column_names(result)

    def fetch_balance_sheet(self, last_date_only=False):
        balance_sheet = self.ticker_data.balance_sheet.transpose()
        return self.adjust_api_result(balance_sheet, last_date_only)

    def fetch_financials(self, last_date_only=False):
        financials = self.ticker_data.financials.transpose()
        return self.adjust_api_result(financials, last_date_only)

    def fetch_cash_flow(self, last_date_only=False):
        cash_flow = self.ticker_data.cashflow.transpose()
        return self.adjust_api_result(cash_flow, last_date_only)

    def fetch_info_table(self):
        info = self.ticker_data.info

        # Normalize column names
        info = {to_snake_case(k): v for k, v in info.items()}

        # Define keys for splitting
        info_keys = {'symbol', 'short_name', 'long_name', 'uuid', 'address1', 'address2', 'fax',
                     'city', 'state', 'zip', 'country', 'phone', 'website',
                     'industry', 'industry_key', 'industry_disp', 'sector', 'sector_key',
                     'sector_disp', 'long_business_summary', 'full_time_employees', 'ir_website',
                     'company_officers'}

        # Split the info based on keys
        non_changeable_info = {k: v for k, v in info.items() if k in info_keys}
        changeable_info = {k: v for k, v in info.items() if k not in info_keys}

        # Create DataFrames
        info_df = pd.DataFrame([non_changeable_info])
        stats_df = pd.DataFrame([changeable_info])

        # Add ticker column
        info_df['ticker'] = self.ticker
        stats_df['ticker'] = self.ticker

        return info_df, stats_df

    def bulk_download_h_prices(self, tickers=None, period="2y", interval='1wk', return_ohlc4=True):
        # Use provided tickers or default to MACRO_YDATA_TICKERS
        tickers = tickers or MACRO_YDATA_TICKERS

        # Download data using the initialized session
        data = yf.download(' '.join(tickers.values()), period=period, interval=interval, group_by='ticker',
                           threads=True, session=self.session)

        # If return_ohlc4 is True, calculate OHLC4 for each ticker and return that
        if return_ohlc4:
            def calculate_ohlc4(df):
                return (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

            # Process each ticker's data and store in a dictionary with appropriate keys
            ohlc4_data = {}
            for name, ticker in tickers.items():
                ohlc4_data[name] = calculate_ohlc4(data[ticker])

            return pd.DataFrame(ohlc4_data)

        # Otherwise, return the full DataFrame
        return data
