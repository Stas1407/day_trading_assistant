import pytz
from datetime import datetime
from utilities import print_banner
from multiprocessing import Queue
from Assistant import Assistant
from CentralLogger import CentralLogger
import json
import os

class StartupManager:
    def check_if_market_is_open(self):
        tz = pytz.timezone("America/New_York")
        time = datetime.now(tz)
        if (time.hour < 9) or (time.hour == 9 and time.minute < 30) or (time.hour >= 16):
            print("[*] Warning: For better performance run when the stock market is open.")

    def check_answer(self, answer):
        if answer.lower() == "yes" or answer.lower() == "y":
            return True
        else:
            return False

    def save_preferences(self, preferences):
        try:
            with open("data/preferences.json", "w") as f:
                json.dump(preferences, f)
        except FileNotFoundError:
            os.mkdir("data")

            with open("data/preferences.json", "w") as f:
                json.dump(preferences, f)

    def find_preferences(self):
        try:
            with open("data/preferences.json", "r") as f:
                preferences = json.load(f)
        except FileNotFoundError:
            preferences = {}

        return preferences

    def run(self):
        print_banner('Welcome to day trading assistant', 'green')

        self.check_if_market_is_open()

        preferences = self.find_preferences()

        if len(preferences) == 4 and self.check_answer(input("Do you want to use the same settings as last time? (y/n): ")):
            max_processes = preferences["max_processes"]
            run_surpriver = preferences["run_surpriver"]
            create_dictionary = preferences["create_dictionary"]
            create_stocks_list = preferences["create_stocks_list"]
            if run_surpriver:
                web_stocks_limit = max_processes-5
                max_surpriver_stocks_num = 5
            else:
                web_stocks_limit = max_processes
                max_surpriver_stocks_num = 0
            tickers = []
        else:
            tickers = input("Do you want to monitor any special tickers? (if not leave empty): ")
            tickers = tickers.replace(",", "").split(" ")

            max_processes = ""

            while not max_processes.isnumeric() or int(max_processes) >= 100:
                max_processes = input("How many processes can I run? (Recommended 30-40): ")

            max_processes = int(max_processes)

            run_surpriver = self.check_answer(input("Do you want me to run surpriver? (y/n): "))

            if run_surpriver:
                web_stocks_limit = max_processes-5
                max_surpriver_stocks_num = 5
                create_dictionary = self.check_answer(input("Do you want me to run surpriver with new data? (y/n): "))
                create_stocks_list = create_dictionary
            else:
                web_stocks_limit = max_processes
                max_surpriver_stocks_num = 0
                create_dictionary = False
                create_stocks_list = False

        show_prepost = True

        max_stocks_list_size = 1200
        dict_path = "surpriver/dictionaries/data"
        stocks_path = "best_stocks.txt"

        if stocks_path == "stocks.txt" and create_stocks_list:
            print("Cannot overwrite this file")
            return

        preferences = {
            "max_processes": max_processes,
            "run_surpriver": run_surpriver,
            "create_dictionary": create_dictionary,
            "create_stocks_list": create_stocks_list
        }

        self.save_preferences(preferences)

        q = Queue()
        logging_queue = Queue()
        additional_data_queue = Queue()

        logger = CentralLogger(logging_queue)
        logger.start()

        print_banner("Getting ready", "green")

        a = Assistant(q, logging_queue, additional_data_queue, max_processes, create_dictionary, create_stocks_list,
                      dict_path, stocks_path, web_stocks_limit, max_stocks_list_size, max_surpriver_stocks_num,
                      show_prepost, run_surpriver, tickers=tickers)
        a.run()
