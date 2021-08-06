from Stock import Stock
from multiprocessing import Process
import time
from utilities import handle_console_interface, print_banner
from tqdm import tqdm
from AssistantDataLoader import AssistantDataLoader
import yfinance as yf
from terminaltables import AsciiTable
import warnings

class Assistant:
    def __init__(self, q, logger_queue, additional_data_queue, max_processes, create_dictionary, create_stocks_list,
                 dictionary_file_path, stocks_file_path, tickers=None):
        self._q = q
        self._additional_queue = additional_data_queue

        data_loader = AssistantDataLoader(logger_queue=logger_queue,
                                          create_dictionary=create_dictionary,
                                          create_stocks_list=create_stocks_list,
                                          dictionary_file_path=dictionary_file_path,
                                          stocks_file_path=stocks_file_path)

        self._tickers, self._surpriver_tickers = data_loader.get_tickers(tickers)

        self._logger_queue = logger_queue

        self._max_processes = min([max_processes, len(self._tickers)])
        self._processes = {}

        self._interface = Process()

    def start_monitoring(self, tickers, show_progress=True):
        warnings.filterwarnings("ignore")
        self._logger_queue.put(["INFO", "  Assistant: Starting monitoring given tickers"])
        processes = {}
        tickers = tickers[:self._max_processes]

        if show_progress:
            print("[+] Downloading data for day trading assistant from yahoo finance (up to 3 minutes)...")

        data = yf.download(
            tickers=" ".join(tickers),
            period="1y",
            interval="1d",
            group_by='ticker')

        data_for_chart = yf.download(
            tickers=" ".join(tickers),
            period="1d",
            interval="5m",
            group_by='ticker',
            prepost=True)

        if show_progress:
            print_banner('Preparing Trades', 'blue')

        if show_progress:
            for ticker in tqdm(tickers):
                self._logger_queue.put(["DEBUG", f"  Assistant: Starting {ticker}"])
                s = Stock(ticker, data=data[ticker], data_for_chart=data_for_chart[ticker], queue=self._q,
                          logger_queue=self._logger_queue, additional_queue=self._additional_queue)
                s.name = ticker
                s.start()
                processes[ticker] = s
                self._logger_queue.put(["DEBUG", f"  Assistant: {ticker} started"])
        else:
            for ticker in tickers:
                self._logger_queue.put(["DEBUG", f"  Assistant: Starting {ticker}"])
                s = Stock(ticker, data=data[ticker], data_for_chart=data_for_chart[ticker], queue=self._q,
                          logger_queue=self._logger_queue, additional_queue=self._additional_queue)
                s.name = ticker
                s.start()
                processes[ticker] = s
                self._logger_queue.put(["DEBUG", f"  Assistant: {ticker} started"])

        return processes

    def start_console_interface(self):
        self._logger_queue.put(["INFO", "  Assistant: Starting console interface"])
        interface = Process(target=handle_console_interface, args=(self._logger_queue, self._q, self._max_processes, self._surpriver_tickers))
        interface.name = "console_interface"
        interface.start()

        return interface

    def handle_input(self):
        self._logger_queue.put(["INFO", "  Assistant: Handling input started"])

        try:
            while True:
                inp = input()

                if inp.isnumeric():
                    self._processes[self._tickers[int(inp)]].show_chart()
                elif inp in self._processes.keys():
                    self._processes[inp].show_chart()
                elif inp.lower() == "exit":
                    break
                elif inp[0] == '+' and not inp.isnumeric():
                    self._processes.update(self.start_monitoring([inp[1:]], show_progress=False))
                    self._tickers.append(inp[1:])
                    self._q.put({"max_processes": "+1"})
                elif inp == "surpriver":
                    table_data = []
                    for ticker, prediction in self._surpriver_tickers:
                        if self._processes[ticker].is_alive():
                            self._processes[ticker].get_data()

                            data = self._additional_queue.get()

                            table_data.append([ticker]+data+[round(prediction, 2)])

                    sorted(table_data, key=lambda x: x[4])
                    table_data = [["Ticker", "Price", "Support", "Resistance", "Estimated profit", "Volatility", "Prediction"]] + table_data
                    table = AsciiTable(table_data)
                    print(table.table)
                elif inp == "help" or inp == "?":
                    print("Commands:")
                    print("\t <TICKER>    = Shows chart of given ticker")
                    print("\t +<TICKER>   = Adds ticker for analysis")
                    print("\t surpriver   = Shows stocks picked by surpriver")
                    print("\t exit        = Close day trading assistant")
                else:
                    print("[-] Wrong ticker")

                print("Ticker (help for help menu): ", end='')
        except KeyboardInterrupt:
            print("[+] Exiting")

        self.stop()

    def run(self):
        self._processes = self.start_monitoring(self._tickers)
        self._interface = self.start_console_interface()
        self.handle_input()

    def stop(self):
        self._logger_queue.put(["INFO", "  Assistant: Exiting"])
        for ticker, proc in self._processes.items():
            self._logger_queue.put(["DEBUG", f"[*] Assistant: {ticker} requesting to stop"])
            proc.stop()

        self._logger_queue.put(["DEBUG", "  Assistant: Requesting console interface to stop"])

        self._q.put({'ticker': "exit"})

        time.sleep(3)

        for ticker, proc in self._processes.items():
            if proc.is_alive():
                self._logger_queue.put(["WARNING", f"  Assistant: {ticker} did not exit, terminating..."])
                proc.terminate()

        if self._interface.is_alive():
            self._logger_queue.put(["WARNING", "  Assistant: console interface did not exit, terminating..."])
            self._interface.terminate()

        while not self._q.empty():
            item = self._q.get()
            self._logger_queue.put(["WARNING", f"  Assistant: Cleaning queue {item}"])

        self._logger_queue.put(["INFO", "  Assistant: Exited"])

        self._logger_queue.put(["DEBUG", "  Requesting logger to stop"])
        self._logger_queue.put(["stop", ""])

        self._q.close()
        self._logger_queue.close()

        self._q.join_thread()
        self._logger_queue.join_thread()

