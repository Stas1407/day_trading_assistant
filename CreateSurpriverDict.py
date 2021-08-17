from surpriver.feature_generator import TAEngine
import numpy as np
import yfinance as yf
import pandas as pd
import time
from progress.bar import Bar
import warnings
from utilities import print_banner
import os
import gc
import datetime

class CreateDict:
    def __init__(self, logger_queue, stocks_file_path, dict_path):
        warnings.filterwarnings("ignore")

        # Queue for communication with logger process
        self._logger_queue = logger_queue

        # Config
        self.taEngine = TAEngine(history_to_use=60)     # 60 bars * 15 minutes (DATA_GRANULARITY_MINUTES)
        self.DATA_GRANULARITY_MINUTES = 15
        self.directory_path = str(os.path.dirname(os.path.abspath(__file__)))
        self.STOCKS_FILE_PATH = self.directory_path + f"/surpriver/stocks/{stocks_file_path}"
        self.DICT_PATH = dict_path

        self._logger_queue.put(["INFO", " CreateSurpriverDict: Loading stocks from file..."])

        # Load stocks list
        self.stocks_list = open(self.STOCKS_FILE_PATH, "r").readlines()
        self.stocks_list = [str(item).strip("\n") for item in self.stocks_list]
        self.stocks_list = list(sorted(set(self.stocks_list)))

        # Main dict
        self.features_dictionary_for_all_symbols = {}


    def calculate_volatility(self, stock_price_data):
        CLOSE_PRICE_INDEX = 4
        stock_price_data_list = stock_price_data.values.tolist()
        close_prices = [float(item[CLOSE_PRICE_INDEX]) for item in stock_price_data_list]
        close_prices = [item for item in close_prices if item != 0]
        volatility = np.std(close_prices)
        return volatility

    def get_data(self):
        self._logger_queue.put(["INFO", " CreateSurpriverDict: Getting data from yahoo..."])
        period = "30d"
        start = time.time()

        print("[+] Downloading data for surpriver from yahoo finance...")

        data = yf.download(
                        tickers=" ".join(self.stocks_list),
                        period=period,
                        interval=str(self.DATA_GRANULARITY_MINUTES) + "m",
                        group_by='ticker',
                        auto_adjust=False,
                        progress=True)

        print("[+] Processing...")

        self._logger_queue.put(["DEBUG", f" CreateSurpriverDict: Got data after {time.time()-start}s"])
        return data

    def process_data(self, stock_prices):
        try:
            # stock_prices = stock_prices.reset_index()
            # stock_prices = stock_prices[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']]

            stock_prices_list = stock_prices.values.tolist()
            stock_prices_list = stock_prices_list[1:]
            historical_prices = pd.DataFrame(stock_prices_list)
            historical_prices.columns = ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']

            return historical_prices
        except KeyError as e:
            self._logger_queue.put(["ERROR", e])
            self._logger_queue.put(["ERROR", stock_prices])
            print("[-] Failed to create dict for surpriver = Not executing surpriver.")
            return []

    def run(self):
        data = self.get_data()
        failed = []
        print_banner("Preparing data for surpriver", "red")
        bar = Bar("", max=len(self.stocks_list))

        self._logger_queue.put(["INFO", " CreateSurpriverDict: Started creating dict"])
        for symbol in self.stocks_list:
            try:
                stock_price_data = data[symbol]
            except KeyError as e:
                failed.append(symbol)
                continue

            bar.next()

            stock_price_data = self.process_data(stock_price_data)

            if stock_price_data.empty:
                return False

            if str(stock_price_data) == "":
                continue

            volatility = self.calculate_volatility(stock_price_data)

            # Filter low volatility stocks
            if volatility < 0.05:
                self._logger_queue.put(["DEBUG", f" CreateSurpriverDict: Too low volatility - {symbol}"])
                continue

            features_dictionary = self.taEngine.get_technical_indicators(stock_price_data)

            # Add to dictionary
            self.features_dictionary_for_all_symbols[symbol] = {"features": features_dictionary,
                                                                "current_prices": stock_price_data,
                                                                "future_prices": []}

            # Save dictionary after every 100 symbols
            if len(self.features_dictionary_for_all_symbols) % 100 == 0:
                np.save(self.DICT_PATH, self.features_dictionary_for_all_symbols)

        bar.finish()
        print(f"[*] Successfully got data for {len(self.stocks_list) - len(failed)} out of {len(self.stocks_list)} tickers.")
        self._logger_queue.put(["INFO", f" CreateSurpriverDict: Dict created length - {len(self.features_dictionary_for_all_symbols)}"])
        self._logger_queue.put(["DEBUG", f" CreateSurpriverDict: Failed - {failed}"])
        self._logger_queue.put(["DEBUG", f" CreateSurpriverDict: Failed count - {len(failed)}"])

        np.save(self.DICT_PATH, self.features_dictionary_for_all_symbols)

        del self.features_dictionary_for_all_symbols
        del data
        gc.collect()

        return True
