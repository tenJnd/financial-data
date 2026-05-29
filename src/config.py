import os

FRED_API_KEY = os.environ.get('FRED_API_KEY')

FINANCIAL_DATA_SCREENER_FILTERS = 'cap_microover,fa_debteq_u1,fa_roa_pos'
FINANCIAL_DATA_SCREENER_ORDER = '-roa'

MACRO_YDATA_TICKERS = {
    'S&P 500': '^GSPC',
    'VIX': '^VIX',
    '10Y Treasury Yield': '^TNX',
    'Gold': 'GC=F',
    'Oil (WTI Crude)': 'CL=F',
    'U.S. Dollar Index': 'DX-Y.NYB'
}

FRED_MACRO_DATA = {
    'M2 Money Supply': 'M2SL',
    'Consumer Sentiment Index': 'UMCSENT',
    'Industrial Production Index': 'INDPRO'
}
