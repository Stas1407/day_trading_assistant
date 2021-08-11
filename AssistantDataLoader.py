import requests
from secrets import API_KEY
import json
from CreateSurpriverDict import CreateDict
from bs4 import BeautifulSoup
from surpriver.detection_engine import Surpriver

class AssistantDataLoader:
    def __init__(self, logger_queue, create_stocks_list, create_dictionary, dictionary_file_path, stocks_file_path, scraper_limit, max_stocks_list_size, max_surpriver_stocks_num):
        # Config
        self.create_stocks_list_bool = create_stocks_list
        self.create_dictionary_bool = create_dictionary
        self._scraper_limit = scraper_limit
        self._max_stocks_list_size = max_stocks_list_size
        self._max_surpriver_stocks_num = max_surpriver_stocks_num
        self._run_surpriver = True

        self._stocks_file_path = stocks_file_path
        self._dictionary_file_path = dictionary_file_path

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
        if not CreateDict(self._logger_queue, self._stocks_file_path, self._dictionary_file_path).run():
            # self._run_surpriver = False
            pass

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
            labels = row.find_all("td")
            if len(ticker.text) <= 4:
                volume = labels[1]
                tab.append([ticker.text, volume.text])

        l = len(tab)
        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Got {len(tab)} tickers from 1st source"])

        response2 = requests.get(self._unusual_volume_detector2)
        s2 = BeautifulSoup(response2.content, "html.parser")

        for row in s2.find_all('tr'):
            ticker = row.find('th').text.strip()
            volume = row.find_all('td')
            if len(ticker) <= 4:
                volume = volume[1].text.strip().replace(",", "")
                tab.append([ticker, volume])

        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Got {len(tab)-l} tickers from 2nd source"])

        tab = sorted(tab, key=lambda x: int(x[1]), reverse=True)
        tab = [i[0] for i in tab]

        return tab

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

            tickers.extend([i[0] for i in surpriver_tickers])
        else:
            surpriver_tickers = [[]]

        self._logger_queue.put(["INFO", " AssistantDataLoader: Running scraper"])
        scraper_tickers = self.scraper()
        limit_left = self._scraper_limit + self._max_surpriver_stocks_num - len(tickers)
        scraper_tickers = scraper_tickers[:limit_left]

        self._logger_queue.put(["DEBUG", f"AssistantDataLoader: Scraper returned: {scraper_tickers}"])
        self._logger_queue.put(["INFO", f"AssistantDataLoader: Scraper returned {len(scraper_tickers)} tickers"])

        tickers.extend(scraper_tickers)

        return tickers, surpriver_tickers
