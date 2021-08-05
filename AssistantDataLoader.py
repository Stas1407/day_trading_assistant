import requests
from secrets import API_KEY
import json
from CreateSurpriverDict import CreateDict
from bs4 import BeautifulSoup
from surpriver.detection_engine import Surpriver

class AssistantDataLoader:
    def __init__(self):
        self.create_dictionary = False

    def create_surpriver_dictionary(self):
        CreateDict().run()

    def create_stocks_list(self):
        print("[+] Start")
        response = requests.get("https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=500000000&\
                                marketCapLowerThan=5000000000&volumeMoreThan=1000000&isActivelyTrading=true&priceLowerThan=50&\
                                country=US&exchange=nasdaq&apikey={0}".format(API_KEY))

        data = json.loads(response.content)
        print("Received ", len(data), " stocks")

        if len(data) < 500:
            print("[+] Getting more stocks")
            response = requests.get("https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=500000000&\
                                    marketCapLowerThan=7000000000&volumeMoreThan=100000&isActivelyTrading=true&priceLowerThan=50&\
                                    country=US&exchange=nasdaq&apikey={0}".format(API_KEY))
            data = json.loads(response.content)
            print("[+] Now received ", len(data), " stocks")

        print("[+] Writing to a file")
        with open("surpriver/stocks/best_stocks.txt", "w") as f:
            for o in data:
                f.write(f"{o['symbol']}\n")
            f.close()

        print("[+] End. Exiting")

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

        tab = sorted(tab, key=lambda x: x[1], reverse=True)
        tab = [i[0] for i in tab]
        tab = tab[:25]

        response2 = requests.get("https://unusualvolume.info/")
        s2 = BeautifulSoup(response2.content, "html.parser")

        for row in s2.find_all('tr'):
            ticker = row.find('th').text
            if len(ticker) <= 4:
                tab.append(ticker)

        print(tab)

        return tab

    def get_tickers(self, tickers):
        if self.create_dictionary:
            print("Creating stocks list...")
            self.create_stocks_list()
            print("Creating dictionary...")
            self.create_surpriver_dictionary()

        surpriver = Surpriver(top_n=25,
                              history_to_use=60,
                              min_volume=5000,
                              data_dictionary_path="surpriver/dictionaries/data.npy",
                              data_granularity_minutes=15,
                              volatility_filter=0.05,
                              stock_list="best_stocks.txt",
                              data_source="yahoo_finance")
        print("Running surpriver...")
        surpriver_tickers = surpriver.find_anomalies()
        print(surpriver_tickers)
        tickers.extend(surpriver_tickers)
        print("Running scraper...")
        tickers.extend(self.scraper())
        print("Scraper done")

        return tickers