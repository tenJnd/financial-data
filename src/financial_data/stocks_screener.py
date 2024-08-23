from io import StringIO
import numpy as np
import pandas as pd
import requests as re
from bs4 import BeautifulSoup

URL_BASE_FINVIZ = 'https://finviz.com/screener.ashx?v={view}&f={filters}&r={page}&o={order}'
HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Constants for the filters
VIEWS = [111, 121, 161, 131]
FILTERS = 'cap_mega,fa_debteq_u0.7,fa_eps5years_pos,fa_roa_pos,geo_usa'
ORDER = '-roa'  # Ensure consistent ordering by ROA

RANKED_COLS = {
    'roa': False,
    'p/fcf': True,
    # 'roe': False,
    # 'debt/eq': True
}


def adjust_columns(df):
    df.columns = df.columns.str.lower()
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = [x.replace(" ", "_") for x in df.columns]
    df.set_index('ticker', inplace=True)
    df.index = df.index.str.lower()
    return df


def get_last_page(soup):
    pages = soup.find_all('a', class_="screener-pages")
    if pages and len(pages) > 1:
        last_page_text = pages[-2].text.strip()
        if last_page_text.isdigit():
            return int(last_page_text)
        else:
            print(f"Unexpected page text: '{last_page_text}'")
            return 1
    return 1


def fetch_page_data(view, filters, page, order):
    url = URL_BASE_FINVIZ.format(view=view, filters=filters, page=page, order=order)
    web_screen = re.get(url, headers=HEADERS).text
    soup_screen = BeautifulSoup(web_screen, 'html.parser')
    return soup_screen


def extract_table(soup_screen):
    table = soup_screen.find(id='screener-table')
    if table:
        tables = pd.read_html(StringIO(str(table)))
        for df in tables:
            if df.shape[0] > 1:  # Check if the table has more than one row
                return df
    return pd.DataFrame()


def fetch_view_data(view, filters, order):
    web = re.get(URL_BASE_FINVIZ.format(view=view, filters=filters, page=0, order=order), headers=HEADERS).text
    soup = BeautifulSoup(web, 'html.parser')

    last_page = get_last_page(soup)
    df_result = pd.DataFrame()
    page = 1

    while page <= last_page * 20:
        soup_screen = fetch_page_data(view, filters, page, order)
        df = extract_table(soup_screen)
        if not df.empty:
            df_result = pd.concat([df_result, df], ignore_index=True)

        page += 20
        progress = int((page / (last_page * 20)) * 100)
        if progress % 20 == 0:
            print(f"{progress} %")

    df_result = adjust_columns(df_result)
    return df_result


def merge_dataframes(dfs):
    result_df = dfs[0]
    for df in dfs[1:]:
        result_df = result_df.join(df, how='outer', lsuffix='', rsuffix='_dup')
        duplicate_cols = [col for col in result_df.columns if col.endswith('_dup')]
        result_df.drop(columns=duplicate_cols, inplace=True)
    return result_df


def preprocess_dataframe(df):
    # filter sectors
    df = df[~df['sector'].isin(['Financial', 'Utilities'])]

    # Remove percentage signs and convert to numeric values
    percentage_columns = [col for col in df.columns if df[col].dtype == 'object' and df[col].str.endswith('%').any()]
    # Replace '-' with NaN
    df[percentage_columns] = df[percentage_columns].replace('-', np.nan)
    for col in percentage_columns:
        df[col] = df[col].str.replace('%', '').astype(float)

    # Convert other columns to numeric values if possible
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='ignore')

    # Add ranking columns
    for col, order in RANKED_COLS.items():
        if col not in df.columns:
            continue
        df[f'rank_{col}'] = df[col].rank(ascending=order)

    # Group by industry and rank within each industry
    for col, order in RANKED_COLS.items():
        if col not in df.columns:
            continue
        df[f'industry_rank_{col}'] = df.groupby('industry')[col].rank(ascending=order)

    # Sum the ranks
    rank_columns = [f'rank_{col}' for col in RANKED_COLS if f'rank_{col}' in df.columns]
    df['score'] = df[rank_columns].sum(axis=1)

    industry_rank_columns = [f'industry_rank_{col}' for col in RANKED_COLS if f'industry_rank_{col}' in df.columns]
    df['industry_score'] = df[industry_rank_columns].sum(axis=1)

    # Sort the dataframe by score in ascending order
    df = df.sort_values(by=['industry_score', 'score'], ascending=True)

    return df


if __name__ == '__main__':
    dfs = [fetch_view_data(view, FILTERS, ORDER) for view in VIEWS]
    final_df = merge_dataframes(dfs)
    final_df = preprocess_dataframe(final_df)
    print(final_df)
