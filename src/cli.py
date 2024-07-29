import logging

import click
from jnd_utils.log import init_logging

from config import FINANCIAL_DATA_SCREENER_FILTERS, FINANCIAL_DATA_SCREENER_ORDER
from src.financial_data.finviz_screener import fetch_view_data
from src.financial_data.yahoo_scraper import fetch_and_save_tickers_data, calculate_and_save_indicators
from src.rapid_api_processor.api_factory import ObjectProcessor

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)


@click.group(chain=True)
def cli():
    pass


@cli.command()
@click.option('-c', '--processor', type=str, default='mboum_screener')
@click.option('-c', '--collection', type=str, default='/co/collections/undervalued_growth_stocks')
def mboum_screener(processor, collection):
    downloader = ObjectProcessor()
    downloader.process(processor, collection)


@cli.command()
def financial_data():
    screener_df = fetch_view_data(
        view=111, filters=FINANCIAL_DATA_SCREENER_FILTERS, order=FINANCIAL_DATA_SCREENER_ORDER
    )
    tickers = [str.upper(s) for s in screener_df.index.to_list()]
    tickers = list(set(tickers))

    fetch_and_save_tickers_data(tickers)
    calculate_and_save_indicators()


if __name__ == '__main__':
    init_logging()
    cli()
