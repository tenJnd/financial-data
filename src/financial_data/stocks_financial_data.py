"""Pure-calculation valuation helpers.

Kept as a fallback should the gurufocus tool stop returning the
Price-to-GF-Value / Price-to-Graham-Number / Price-to-Peter-Lynch-Fair-Value
ratios. Inputs are plain pandas DataFrames; no database, no IO.
"""
import logging

import pandas as pd

_logger = logging.getLogger(__name__)

REQUIRED_COLUMNS_MAGIC = ['ticker', 'sector_key', 'enterprise_value', 'ebit',
                          'working_capital', 'net_tangible_assets']
REQUIRED_COLUMNS_GRAHAM = ['trailing_eps', 'book_value', 'current_price']
REQUIRED_COLUMNS_LYNCH = ['earnings_growth', 'trailing_eps', 'current_price']


def calculate_magic_formula(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=REQUIRED_COLUMNS_MAGIC).copy()

    df['earnings_yield'] = df['ebit'] / df['enterprise_value']
    df['return_on_capital'] = df['ebit'] / (df['working_capital'] + df['net_tangible_assets'])

    df['earnings_yield_rank'] = df['earnings_yield'].rank(ascending=False)
    df['return_on_capital_rank'] = df['return_on_capital'].rank(ascending=False)

    df['earnings_yield_rank_sector'] = df.groupby('sector_key')['earnings_yield'].rank(ascending=False)
    df['return_on_capital_rank_sector'] = df.groupby('sector_key')['return_on_capital'].rank(ascending=False)

    df['total_rank'] = df['earnings_yield_rank'] + df['return_on_capital_rank']
    df['total_sector_rank'] = df['earnings_yield_rank_sector'] + df['return_on_capital_rank_sector']

    return df[['ticker', 'sector_key', 'earnings_yield', 'return_on_capital',
               'earnings_yield_rank', 'return_on_capital_rank',
               'total_rank', 'total_sector_rank']]


def calculate_graham_number(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=REQUIRED_COLUMNS_GRAHAM).copy()
    df['graham_number'] = (22.5 * df['trailing_eps'] * df['book_value']) ** 0.5
    df['current_price_graham_comparison'] = df['current_price'] / df['graham_number']
    return df


def calculate_peter_lynch_value(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=REQUIRED_COLUMNS_LYNCH).copy()
    df['growth_rate'] = df['earnings_growth'] if 'earnings_growth' in df.columns else 0
    df['peter_lynch_value'] = df['trailing_eps'] * (df['growth_rate'] + 1)
    df['current_price_lynch_comparison'] = df['current_price'] / df['peter_lynch_value']
    return df
