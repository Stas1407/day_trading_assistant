import requests
from secrets import API_KEY
import json
from DataDownloader import DataDownloader
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
    def __init__(self, logger_queue, create_stocks_list, create_dictionary, dictionary_file_path, stocks_file_path, scraper_limit, max_stocks_list_size, max_surpriver_stocks_num, run_surpriver):
        # Config
        self.create_stocks_list_bool = create_stocks_list
        self.create_dictionary_bool = create_dictionary
        self._scraper_limit = scraper_limit
        self._max_stocks_list_size = max_stocks_list_size
        self._max_surpriver_stocks_num = max_surpriver_stocks_num
        self._run_surpriver = run_surpriver

        self._stocks_file_path = stocks_file_path
        self._dictionary_file_path = dictionary_file_path

        #self._fast = False if self._stocks_file_path == "stocks.txt" else True
        self._fast = False

        self.directory_path = str(os.path.dirname(os.path.abspath(__file__)))
        self._stocks_file_path = self.directory_path + f"/surpriver/stocks/{stocks_file_path}"

        # Urls
        self._stock_screener_url = "https://financialmodelingprep.com/api/v3/stock-screener?" + \
                                   "marketCapMoreThan=500000000&" + \
                                   "marketCapLowerThan=5000000000&" + \
                                   "volumeMoreThan=1000000&" + \
                                   "isActivelyTrading=true&" + \
                                   "priceLowerThan=50&" + \
                                   "country=US&" + \
                                   "exchange=nasdaq&" + \
                                   "apikey={0}".format(API_KEY)
        self._stock_screener_url2 = "https://financialmodelingprep.com/api/v3/stock-screener?" \
                                    "marketCapMoreThan=500000000&" \
                                    "marketCapLowerThan=7000000000&" \
                                    "volumeMoreThan=500000&" \
                                    "isActivelyTrading=true&" \
                                    "priceLowerThan=50&" \
                                    "country=US&" \
                                    "exchange=nasdaq&" \
                                    "apikey={0}".format(API_KEY)
        self._unusual_volume_detector = "https://sampom100.github.io/UnusualVolumeDetector_Dynamic/"
        self._unusual_volume_detector2 = "https://unusualvolume.info/"

        # Queues
        self._logger_queue = logger_queue

    def create_surpriver_dictionary(self):
        if not DataDownloader(self._logger_queue, self._stocks_file_path, self._dictionary_file_path).run():
            self._run_surpriver = False

    def create_stocks_list(self):
        response = requests.get(self._stock_screener_url)

        data = json.loads(response.content)
        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Received {len(data)} stocks"])

        if len(data) < 500:
            self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Getting more stocks"])
            response = requests.get(self._stock_screener_url2)
            data = json.loads(response.content)
            self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Now received {len(data)} stocks"])

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
            ticker = row.find("th")
            if len(ticker.text) <= 4:
                tab.append(ticker.text)

        l = len(tab)
        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Got {len(tab)} tickers from 1st source"])

        response2 = requests.get(self._unusual_volume_detector2)
        s2 = BeautifulSoup(response2.content, "html.parser")

        for row in s2.find_all('tr'):
            ticker = row.find('th').text.strip()
            if len(ticker) <= 4:
                tab.append(ticker)

        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Got {len(tab)-l} tickers from 2nd source"])

        return tab

    def get_current_price(self, ticker):
        ticker = yf.Ticker(ticker)
        data = ticker.history(period='1d')

        try:
            return data['Close'][0]
        except IndexError:
            return -1

    def get_most_volatile_stocks(self):

        result = []

        if self._fast:
            self._logger_queue.put(["INFO", " AssistantDataLoader: Running scraper"])
            tickers = self.scraper()

            self._logger_queue.put(["INFO", f" AssistantDataLoader: Got {len(tickers)} tickers from scraper"])

            most_active = stock_info.get_day_most_active()["Symbol"].values.tolist()
            gainers = stock_info.get_day_gainers()["Symbol"].values.tolist()

            self._logger_queue.put(["INFO", f" AssistantDataLoader: Got {len(most_active)} tickers from most active"])
            self._logger_queue.put(["INFO", f" AssistantDataLoader: Got {len(gainers)} tickers from biggest gainers"])

            tickers.extend(most_active)
            tickers.extend(gainers)
        else:
            tickers = open(self._stocks_file_path, "r").readlines()
            tickers = [str(item).strip("\n") for item in tickers]
            tickers = list(sorted(set(tickers)))

        data = pd.read_pickle("data/all_stocks_data.pkl")

        print_banner("Finding the best stocks", "green")

        for ticker in tqdm(tickers):
            try:
                ticker_data = data[ticker]
            except KeyError:
                self._logger_queue.put(["ERROR", f" AssistantDataLoader: Ticker - {ticker} not found"])
                continue

            current_price = ticker_data["Close"][-1]

            if np.isnan(current_price):
                current_price = self.get_current_price(ticker)

            if current_price > 25:
                continue

            try:
                market_cap = int(pandas_data.get_quote_yahoo(ticker)["marketCap"])
            except (KeyError, IndexError):
                market_cap = 0
                self._logger_queue.put(["WARNING", f" AssistantDataLoader: {ticker} Market Cap not found"])

            if market_cap > 5000000000:
                continue

            open_close_prices = [(i[1]["Open"][0], i[1]["Close"][-1]) for i in ticker_data.groupby(ticker_data.index.day)]
            gap = abs(open_close_prices[-1][0] - open_close_prices[-2][1])/current_price

            self._logger_queue.put(["INFO", f" AssistantDataLoader: {ticker} - gap = {gap}"])

            if gap < 0.03:
                continue

            try:
                volume = yf.Ticker(ticker).info["averageVolume"]
            except KeyError:
                # TODO
                self._logger_queue.put(["INFO", f" AssistantDataLoader: {ticker} could not find volume"])
                volume = 20000

            self._logger_queue.put(["INFO", f" AssistantDataLoader: {ticker} - volume = {volume}"])

            if volume is None:
                volume = 20000

            if volume < 20000:
                continue

            high = np.max(ticker_data["High"].last("2d"))
            low = np.min(ticker_data["Low"].last("2d"))
            volatility = (high - low) / low

            self._logger_queue.put(["INFO", f" AssistantDataLoader: {ticker} - volatility = {volatility}"])

            if volatility < 0.1:
                self._logger_queue.put(["INFO", f" AssistantDataLoader: {ticker} - too low volatility"])
                continue

            result.append(ticker)
        
        return result

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
            self._logger_queue.put(["INFO", f"AssistantDataLoader: Surpriver returned {len(surpriver_tickers)} tickers"])

            surpriver_tickers = list(filter(lambda i: i[1] < 0, surpriver_tickers))

            self._logger_queue.put(["DEBUG", f" AssistantDataLoader: After filtering surpriver tickers: {surpriver_tickers}"])
            self._logger_queue.put(["INFO", f"AssistantDataLoader: After filtering surpriver: {len(surpriver_tickers)} tickers"])

            tickers.extend([i[0] for i in surpriver_tickers])
            del surpriver
        else:
            surpriver_tickers = []

        self._logger_queue.put(["INFO", " AssistantDataLoader: Getting most volatile stocks"])
        scraper_tickers = self.get_most_volatile_stocks()
        limit_left = self._scraper_limit + self._max_surpriver_stocks_num - len(tickers)
        scraper_tickers = scraper_tickers[:limit_left]

        self._logger_queue.put(["DEBUG", f"AssistantDataLoader: Scraper returned: {scraper_tickers}"])
        self._logger_queue.put(["INFO", f"AssistantDataLoader: Scraper returned {len(scraper_tickers)} tickers"])

        tickers.extend(scraper_tickers)

        gc.collect()

        return tickers, surpriver_tickers
