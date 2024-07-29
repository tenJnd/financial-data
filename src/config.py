import os

RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')
BOUM_FINANCE_HOST = os.environ.get('BOUM_FINANCE_HOST', 'mboum-finance.p.rapidapi.com')

FEAR_AND_GREED_HOST = os.environ.get('FEAR_AND_GREED_URL', 'fear-and-greed-index.p.rapidapi.com')
DB_SCHEMA = os.environ.get('DB_SCHEMA', 'data_monkee')

SERVICES = {
    'mboum_screener': {
        'host': BOUM_FINANCE_HOST,
        'endpoints': {
            '/co/collections/undervalued_large_caps': {'params': {}, 'table': 'undervalued_large_caps'},
            '/co/collections/undervalued_growth_stocks': {'params': {}, 'table': 'undervalued_growth_stocks'}
        }
    },
    'fgi': {
        'host': FEAR_AND_GREED_HOST,
        'endpoints': {
            '/v1/fgi': {'params': {}, 'table': 'fgi'}
        }
    }
}

FINANCIAL_DATA_SCREENER_FILTERS = 'cap_microover,fa_debteq_u1,fa_roa_pos,geo_usa'
FINANCIAL_DATA_SCREENER_ORDER = '-roa'
