import logging
from datetime import datetime
from typing import List

import pandas as pd
import pandas.io.sql as sqlio
from database_tools.lightning_uploader import LightningUploader

from src.api_adapters.yahoo import YahooData
from src.database import database

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
logging.getLogger('database_tools.lightning_uploader').setLevel(logging.WARNING)

SCHEMA = 'financial_data'
REQUIRED_COLUMNS_MAGIC = ['ticker', 'sector_key', 'enterprise_value', 'ebit', 'working_capital', 'net_tangible_assets']
REQUIRED_COLUMNS_GRAHAM = ['trailing_eps', 'book_value', 'current_price']
REQUIRED_COLUMNS_LYNCH = ['earnings_growth', 'trailing_eps', 'current_price']


class Tables:
    FINANCIALS = 'financials'
    BALANCE_SHEET = 'balance_sheet'
    CASH_FLOW = 'cash_flow'
    COMPANY_INFO = 'company_info'
    KEY_STATS = 'key_stats'
    INDICATORS = 'indicators'
    MAGIC_FORMULA = 'magic_formula'

    tables_list = [value for key, value in vars().items() if not key.startswith('__') and not callable(value)]


def fetch_data_from_db(statement_table, ticker, date=None) -> pd.DataFrame:
    if date:
        date_con = f"and date <= '{date}'"
    else:
        date_con = ''
    try:
        with database.connection_manager() as conn:
            sql = f"""
            select * from {SCHEMA}.{statement_table}
             where ticker in ('{ticker}') 
             {date_con}
             order by timestamp_generated desc
             limit 1
             """
            df = sqlio.read_sql(sql, conn)
            return df if not df.empty else None
    except Exception:
        return None


def fetch_and_save_tickers_data(tickers: List[str], last_day_only=True):
    timestamp = datetime.now()
    total_tickers = len(tickers)

    # Initialize lists to store data for bulk upload
    data_lists = {
        Tables.KEY_STATS: [],
        Tables.COMPANY_INFO: [],
        Tables.CASH_FLOW: [],
        Tables.FINANCIALS: [],
        Tables.BALANCE_SHEET: []
    }

    for counter, ticker in enumerate(tickers):
        try:
            ydata = YahooData(ticker)
            info, stats = ydata.fetch_info_table()
            bs = ydata.fetch_balance_sheet(last_date_only=last_day_only)

            if bs.empty:
                log_progress(counter, total_tickers, ticker, "Balance sheet is empty, skipping")
                continue

            last_date_api = bs['date'][0]
            bs_db = fetch_data_from_db('balance_sheet', ticker, last_date_api)

            if bs_db is not None and last_date_api <= bs_db['date'].max():
                fi_db = fetch_data_from_db('financials', ticker, last_date_api)
                cf_db = fetch_data_from_db('cash_flow', ticker, last_date_api)

                if fi_db is not None and last_date_api <= fi_db['date'].max() and \
                        cf_db is not None and last_date_api <= cf_db['date'].max():
                    append_to_lists(data_lists, stats)
                    log_progress(
                        counter + 1,
                        total_tickers,
                        ticker,
                        "Data financials already exists, saving only stats"
                    )
                    continue

            fi = ydata.fetch_financials(last_date_only=last_day_only)
            cf = ydata.fetch_cash_flow(last_date_only=last_day_only)

            info_db = fetch_data_from_db(Tables.COMPANY_INFO, ticker)
            if info_db is None:
                data_lists[Tables.COMPANY_INFO].append(info)

            append_to_lists(data_lists, stats, cf, fi, bs)
            log_progress(counter + 1, total_tickers, ticker, "Data processed successfully")
        except Exception as e:
            _logger.error(f"Error processing ticker {ticker}: {e}")
            log_progress(counter, total_tickers, ticker, "Skipping due to error")

    bulk_upload_data(data_lists, timestamp)
    refresh_views(data_lists.keys())


def append_to_lists(data_lists, stats, cf=None, fi=None, bs=None):
    data_lists[Tables.KEY_STATS].append(stats)
    if cf is not None:
        data_lists[Tables.CASH_FLOW].append(cf)
    if fi is not None:
        data_lists[Tables.FINANCIALS].append(fi)
    if bs is not None:
        data_lists[Tables.BALANCE_SHEET].append(bs)


def log_progress(counter, total_tickers, ticker, message):
    _logger.info(f"Ticker {ticker}: {message}. Progress: {counter}/{total_tickers}")


def bulk_upload_data(data_lists, timestamp):
    up = LightningUploader(schema=SCHEMA, table='', database=database)

    for table, data_list in data_lists.items():
        if data_list:
            # Filter out empty or all-NA DataFrames
            non_empty_data_list = [df for df in data_list if not df.empty]
            if non_empty_data_list:
                data_df = pd.concat(non_empty_data_list, ignore_index=True)
                data_df['timestamp_generated'] = timestamp
                up.table = table
                up.upload_data(data_df)
                _logger.info(f"Data for {table} uploaded successfully.")


def upload_table(table, df):
    up = LightningUploader(schema=SCHEMA, table=table, database=database)
    up.upload_data(df)


def refresh_views(tables_list):
    for table in tables_list:
        _logger.info(f"Refreshing mat. view {table}")
        sql_create = f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS {SCHEMA}.{table}_latest AS 
        SELECT DISTINCT ON (ticker) *
        FROM {SCHEMA}.{table}
        ORDER BY ticker, timestamp_generated DESC;
        """

        sql_refresh = f"""
        REFRESH MATERIALIZED VIEW {SCHEMA}.{table}_latest;
        """

        # Create the materialized view if it doesn't exist
        database.execute_sql(sql_create)

        # Refresh the materialized view
        database.execute_sql(sql_refresh)


def load_financial_data_for_indicators():
    sql_columns = list(set(REQUIRED_COLUMNS_MAGIC + REQUIRED_COLUMNS_GRAHAM + REQUIRED_COLUMNS_LYNCH))
    if 'ticker' in sql_columns:
        sql_columns.remove('ticker')
    sql_columns_string = ", ".join(sql_columns)

    with database.connection_manager() as conn:
        sql = f"""
        SELECT ci.ticker, {sql_columns_string}
        FROM financial_data.company_info_latest ci
        JOIN financial_data.balance_sheet_latest bs ON ci.ticker = bs.ticker
        JOIN financial_data.key_stats_latest ks ON ci.ticker = ks.ticker
        JOIN financial_data.financials_latest fi ON ci.ticker = fi.ticker
        JOIN financial_data.cash_flow_latest cf ON ci.ticker = cf.ticker;
        """

        df = sqlio.read_sql(sql, conn)

    return df


def calculate_and_save_indicators():
    _logger.info("Calculating indicators...")
    timestamp = datetime.now()
    latest_data = load_financial_data_for_indicators()

    # magic formula table
    calculate_and_save_magic_formula(latest_data)

    # other indicators
    latest_data = calculate_graham_number(latest_data)
    latest_data = calculate_peter_lynch_value(latest_data)
    latest_data = latest_data[['ticker',
                               'graham_number', 'current_price_graham_comparison',
                               'peter_lynch_value', 'current_price_lynch_comparison'
                               ]]
    latest_data['timestamp_generated'] = timestamp
    upload_table(Tables.INDICATORS, latest_data)
    refresh_views([Tables.INDICATORS])
    _logger.info("Indicators processed successfully")


def calculate_and_save_magic_formula(df):
    _logger.info("Calculating magic formula...")
    timestamp = datetime.now()
    df = df.dropna(subset=REQUIRED_COLUMNS_MAGIC).copy()

    # Calculate Earnings Yield and Return on Capital using net_tangible_assets
    df['earnings_yield'] = df['ebit'] / df['enterprise_value']
    df['return_on_capital'] = df['ebit'] / (df['working_capital'] + df['net_tangible_assets'])

    # Rank based on earnings yield and return on capital
    df['earnings_yield_rank'] = df['earnings_yield'].rank(ascending=False)
    df['return_on_capital_rank'] = df['return_on_capital'].rank(ascending=False)

    df[f'earnings_yield_rank_sector'] = df.groupby('sector_key')['return_on_capital'].rank(ascending=False)
    df[f'return_on_capital_rank_sector'] = df.groupby('sector_key')['return_on_capital'].rank(ascending=False)

    # Sum the ranks to get the total rank
    df['total_rank'] = df['earnings_yield_rank'] + df['return_on_capital_rank']
    df['total_sector_rank'] = df['earnings_yield_rank_sector'] + df['return_on_capital_rank_sector']

    df = df[['ticker', 'sector_key', 'earnings_yield', 'return_on_capital',
             'earnings_yield_rank', 'return_on_capital_rank',
             'total_rank', 'total_sector_rank']]

    df['timestamp_generated'] = timestamp

    upload_table(Tables.MAGIC_FORMULA, df)
    refresh_views([Tables.MAGIC_FORMULA])


def calculate_graham_number(df):
    _logger.info("Calculating Graham...")
    df = df.dropna(subset=REQUIRED_COLUMNS_GRAHAM).copy()
    df['graham_number'] = (22.5 * df['trailing_eps'] * df['book_value']) ** 0.5
    df['current_price_graham_comparison'] = df['current_price'] / df['graham_number']
    return df


def calculate_peter_lynch_value(df):
    _logger.info("Calculating Lynch...")
    df = df.dropna(subset=REQUIRED_COLUMNS_LYNCH).copy()
    df['growth_rate'] = df['earnings_growth'] if 'earnings_growth' in df.columns else 0
    df['peter_lynch_value'] = df['trailing_eps'] * (df['growth_rate'] + 1)
    df['current_price_lynch_comparison'] = df['current_price'] / df['peter_lynch_value']
    return df


if __name__ == '__main__':
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    fetch_and_save_tickers_data(tickers)
    calculate_and_save_indicators()
