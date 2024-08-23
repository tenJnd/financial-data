import llm_adapters.model_config as model_config
import pandas as pd
from llm_adapters.llm_adapter import LLMClientFactory

from prompts import load_macro_agent_prompt
from src.api_adapters.fred import FredData
from src.api_adapters.yahoo import YahooData
from src.config import MACRO_YDATA_TICKERS, FRED_MACRO_DATA


def download_macro_data():
    # Get the Yahoo data
    yahoo_appi = YahooData()
    ydata_df = yahoo_appi.bulk_download_h_prices(MACRO_YDATA_TICKERS)

    # Get the FRED data and convert to DataFrame
    fred_api = FredData(FRED_MACRO_DATA)
    fred_df = pd.DataFrame(fred_api.get_data())

    # Combine both DataFrames, aligning on the date index
    combined_df = pd.concat([ydata_df, fred_df], axis=1)

    # Reset the index to ensure the date becomes a column
    combined_df.reset_index(inplace=True)

    # Rename the index column to 'date'
    combined_df.rename(columns={'index': 'date'}, inplace=True)

    return combined_df


if __name__ == '__main__':
    combined_df = download_macro_data()
    print(combined_df.head())

    # Convert DataFrame to CSV string with the date as a column
    df_csv = combined_df.to_csv(index=False)  # Do not include the index in the CSV string since it's now a column
    print(df_csv)

    system_prompt = load_macro_agent_prompt()
    human_prompt = f"""
    Below is the CSV data containing historical values for key macroeconomic indicators over the past two years:

    {df_csv}
    """

    class Gpt4Config(model_config.Gpt4Config):
        CONTEXT_WINDOW = 8000

    model = LLMClientFactory().create_llm_client(Gpt4Config)
    resp = model.call_agent(system_prompt=system_prompt, user_prompt=human_prompt)

    print(resp)
