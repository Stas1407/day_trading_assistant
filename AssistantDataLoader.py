import requests
from secrets import API_KEY
import json
from CreateSurpriverDict import CreateSurpriverDict
from bs4 import BeautifulSoup
from surpriver.detection_engine import Surpriver
import gc
from yahoo_fin import stock_info
from pandas_datareader import data as pandas_data
import pandas as pd
import yfinance as yf
import numpy as np
import os
from utilities import print_banner
from tqdm import tqdm


class AssistantDataLoader:
    def __init__(self, logger_queue, create_stocks_list, create_dictionary, dictionary_file_path, stocks_file_path,
                 web_stocks_limit, max_stocks_list_size, max_surpriver_stocks_num, run_surpriver):
        # Config
        self.create_stocks_list_bool = create_stocks_list
        self.create_dictionary_bool = create_dictionary
        self._web_stocks_limit = web_stocks_limit
        self._max_stocks_list_size = max_stocks_list_size
        self._max_surpriver_stocks_num = max_surpriver_stocks_num
        self._run_surpriver = run_surpriver

        self._stocks_file_path = stocks_file_path
        self._dictionary_file_path = dictionary_file_path

        self.directory_path = str(os.path.dirname(os.path.abspath(__file__)))
        self._stocks_file_path = self.directory_path + f"/surpriver/stocks/{stocks_file_path}"

        # Urls
        self._stock_screener_url = "https://financialmodelingprep.com/api/v3/stock-screener?" \
                                   "marketCapLowerThan=700000000&" \
                                   "volumeMoreThan=100000&" \
                                   "isActivelyTrading=true&" \
                                   "priceLowerThan=30&" \
                                   "country=US&" \
                                   "exchange=nasdaq&" \
                                   "apikey={0}".format(API_KEY)
        self._stock_screener_for_surpriver = "https://financialmodelingprep.com/api/v3/stock-screener?" \
                                             "marketCapLowerThan=10000000000&" \
                                             "volumeMoreThan=300000&" \
                                             "isActivelyTrading=true&" \
                                             "priceLowerThan=50&" \
                                             "country=US&" \
                                             "exchange=nasdaq&" \
                                             "apikey={0}".format(API_KEY)
        self._unusual_volume_detector = "https://unusualvolume.info/"

        # Queues
        self._logger_queue = logger_queue

    def create_surpriver_dictionary(self):
        if not CreateSurpriverDict(self._logger_queue, self._stocks_file_path, self._dictionary_file_path).run():
            self._run_surpriver = False

    def create_stocks_list(self):
        response = requests.get(self._stock_screener_for_surpriver)

        data = json.loads(response.content)
        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Received {len(data)} stocks for surpriver"])

        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Shortening data to {self._max_stocks_list_size} stocks"])
        data = data[:self._max_stocks_list_size]

        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Writing to file"])

        with open(self._stocks_file_path, "w") as f:
            for o in data:
                f.write(f"{o['symbol']}\n")
            f.close()

    def scraper(self):
        response = requests.get(self._unusual_volume_detector)
        s = BeautifulSoup(response.content, "html.parser")

        tab = []

        for row in s.find_all('tr'):
            ticker = row.find("th").text.strip()
            if len(ticker) <= 4:
                tab.append(ticker)

        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Got {len(tab)} tickers from unusual volume detector"])

        response = requests.get(self._stock_screener_url)
        response_content = json.loads(response.content)
        tab.extend([i["symbol"] for i in response_content])

        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Got {len(response_content)} tickers from stock screener"])

        tab = list(set(tab))

        return tab

    def get_current_price(self, ticker):
        ticker = yf.Ticker(ticker)
        data = ticker.history(period='1d')

        try:
            return data['Close'][0]
        except IndexError:
            return -1

    def get_data(self, tickers):
        print_banner("Downloading data", "green")

        data = yf.download(
            tickers=" ".join(tickers),
            period="5d",
            interval="1d",
            group_by='ticker',
            progress=True,
            threads=True)

        return data

    def filter_tickers(self, tickers, mode):
        result = []
        data = self.get_data(tickers)

        if mode == "Full":
            print_banner("Filtering additional tickers", "red")
        else:
            print_banner("Filtering tickers", "cyan")

        for ticker in tqdm(tickers):
            try:
                ticker_data = data[ticker]
            except KeyError:
                self._logger_queue.put(["ERROR", f" AssistantDataLoader: Ticker - {ticker} not found"])
                continue

            current_price = ticker_data["Close"][-1]

            if np.isnan(current_price):
                current_price = self.get_current_price(ticker)

            if current_price > 30 and mode == "Full":
                continue

            if mode == "Full":
                try:
                    market_cap = int(pandas_data.get_quote_yahoo(ticker)["marketCap"])
                except (KeyError, IndexError):
                    self._logger_queue.put(["WARNING", f" AssistantDataLoader: {ticker} Market Cap not found"])
                    continue

                if market_cap > 500000000:
                    continue

            gap = abs(ticker_data["Open"][-1] - ticker_data["Close"][-2]) / ticker_data["Open"][-1]

            if gap < 0.05:
                continue

            if mode == "Full":
                try:
                    volume = yf.Ticker(ticker).info["averageVolume"]
                except KeyError:
                    self._logger_queue.put(["INFO", f" AssistantDataLoader: {ticker} could not find volume"])
                    volume = None

                if volume is None or volume < 200000:
                    continue

            returns = np.log(ticker_data["Close"]/ticker_data["Close"].shift(-1))
            volatility = (np.std(returns)*5**0.5)/current_price

            if volatility < 0.05 or np.isnan(volatility):
                self._logger_queue.put(["INFO", f" AssistantDataLoader: {ticker} - too low volatility"])
                continue

            result.append(ticker)

        return result

    def get_more_tickers(self):
        most_active = stock_info.get_day_most_active()["Symbol"].values.tolist()
        gainers = stock_info.get_day_gainers()["Symbol"].values.tolist()

        return list(set(most_active+gainers))

    def get_best_stocks(self):
        self._logger_queue.put(["INFO", " AssistantDataLoader: Running scraper"])
        tickers = self.scraper()
        self._logger_queue.put(["INFO", f" AssistantDataLoader: Got {len(tickers)} tickers from scraper"])

        best_stocks = self.filter_tickers(tickers, mode="Partial")

        self._logger_queue.put(["INFO", f" AssistantDataLoader: After filtering {len(best_stocks)} tickers are left"])

        if len(best_stocks) < self._web_stocks_limit:
            self._logger_queue.put(["INFO", f" AssistantDataLoader: Getting more stocks"])

            additional_tickers = self.get_more_tickers()
            filtered_tickers = self.filter_tickers(additional_tickers, mode="Full")

            self._logger_queue.put(["INFO", f" AssistantDataLoader: After filtering "
                                            f"additional stocks {len(filtered_tickers)} tickers are left"])

            best_stocks += filtered_tickers

        return best_stocks[:self._web_stocks_limit]

    def get_tickers(self, tickers):
        if tickers is None:
            tickers = []

        if self.create_stocks_list_bool:
            self._logger_queue.put(["INFO", " AssistantDataLoader: Creating stocks list..."])
            self.create_stocks_list()

        if self.create_dictionary_bool:
            self._logger_queue.put(["INFO", " AssistantDataLoader: Creating dictionary for surpriver..."])
            self.create_surpriver_dictionary()

        if self._run_surpriver:
            self._logger_queue.put(["INFO", " AssistantDataLoader: Initializing surpriver"])
            surpriver = Surpriver(top_n=self._max_surpriver_stocks_num,
                                  history_to_use=60,
                                  min_volume=5000,
                                  data_dictionary_path="surpriver/dictionaries/data.npy",
                                  data_granularity_minutes=15,
                                  output_format="None",
                                  volatility_filter=0.05,
                                  stock_list=self._stocks_file_path,
                                  data_source="yahoo_finance",
                                  logger_queue=self._logger_queue)

            self._logger_queue.put(["INFO", " AssistantDataLoader: Running surpriver"])
            surpriver_tickers = surpriver.find_anomalies()

            self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Surpriver returned: {surpriver_tickers}"])
            self._logger_queue.put(
                ["INFO", f"AssistantDataLoader: Surpriver returned {len(surpriver_tickers)} tickers"])

            surpriver_tickers = list(filter(lambda i: i[1] < 0, surpriver_tickers))

            self._logger_queue.put(
                ["DEBUG", f" AssistantDataLoader: After filtering surpriver tickers: {surpriver_tickers}"])
            self._logger_queue.put(
                ["INFO", f"AssistantDataLoader: After filtering surpriver: {len(surpriver_tickers)} tickers"])

            tickers.extend([i[0] for i in surpriver_tickers])
            del surpriver
        else:
            surpriver_tickers = []

        self._logger_queue.put(["INFO", " AssistantDataLoader: Getting most volatile stocks"])
        best_stocks = self.get_best_stocks()

        self._logger_queue.put(["DEBUG", f"AssistantDataLoader: Best stocks are - {best_stocks}"])
        self._logger_queue.put(["INFO", f"AssistantDataLoader: Best stocks length - {len(best_stocks)} tickers"])

        tickers.extend(best_stocks)

        tickers = list(set(tickers))

        gc.collect()

        return tickers, surpriver_tickers
