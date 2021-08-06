import requests
from secrets import API_KEY
import json
from CreateSurpriverDict import CreateDict
from bs4 import BeautifulSoup
from surpriver.detection_engine import Surpriver

class AssistantDataLoader:
    def __init__(self, logger_queue):
        self.create_dictionary = False
        self._logger_queue = logger_queue

    def create_surpriver_dictionary(self):
        CreateDict(self._logger_queue).run()

    def create_stocks_list(self):
        response = requests.get("https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=500000000&\
                                marketCapLowerThan=5000000000&volumeMoreThan=1000000&isActivelyTrading=true&priceLowerThan=50&\
                                country=US&exchange=nasdaq&apikey={0}".format(API_KEY))

        data = json.loads(response.content)
        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Received {len(data)} stocks"])

        if len(data) < 500:
            self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Getting more stocks"])
            response = requests.get("https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=500000000&\
                                    marketCapLowerThan=7000000000&volumeMoreThan=100000&isActivelyTrading=true&priceLowerThan=50&\
                                    country=US&exchange=nasdaq&apikey={0}".format(API_KEY))
            data = json.loads(response.content)
            self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Now received {len(data)} stocks"])

        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Shortening data to 1200 stocks"])
        data = data[:1200]

        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Writing to file"])
        with open("surpriver/stocks/best_stocks.txt", "w") as f:
            for o in data:
                f.write(f"{o['symbol']}\n")
            f.close()

    def scraper(self):
        response = requests.get("https://sampom100.github.io/UnusualVolumeDetector_Dynamic/")
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

        response2 = requests.get("https://unusualvolume.info/")
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
        tab = tab[:25]

        return tab

    def get_tickers(self, tickers):
        if tickers is None:
            tickers = []

        if self.create_dictionary:
            self._logger_queue.put(["INFO", " AssistantDataLoader: Creating stocks list..."])
            self.create_stocks_list()

            self._logger_queue.put(["INFO", " AssistantDataLoader: Creating dictionary for surpriver..."])
            self.create_surpriver_dictionary()

        self._logger_queue.put(["INFO", " AssistantDataLoader: Initializing surpriver"])
        surpriver = Surpriver(top_n=25,
                              history_to_use=60,
                              min_volume=5000,
                              data_dictionary_path="surpriver/dictionaries/data.npy",
                              data_granularity_minutes=15,
                              output_format="None",
                              volatility_filter=0.05,
                              stock_list="best_stocks.txt",
                              data_source="yahoo_finance",
                              logger_queue=self._logger_queue)

        self._logger_queue.put(["INFO", " AssistantDataLoader: Running surpriver"])
        surpriver_tickers = surpriver.find_anomalies()

        self._logger_queue.put(["DEBUG", f" AssistantDataLoader: Surpriver returned: {surpriver_tickers}"])
        self._logger_queue.put(["INFO", f"AssistantDataLoader: Surpriver returned {len(surpriver_tickers)} tickers"])

        tickers.extend([i[0] for i in surpriver_tickers])

        self._logger_queue.put(["INFO", " AssistantDataLoader: Running scraper"])
        scraper_tickers = self.scraper()

        self._logger_queue.put(["DEBUG", f"AssistantDataLoader: Scraper returned: {scraper_tickers}"])
        self._logger_queue.put(["INFO", f"AssistantDataLoader: Scraper returned {len(scraper_tickers)} tickers"])

        tickers.extend(scraper_tickers)

        return tickers, surpriver_tickers
