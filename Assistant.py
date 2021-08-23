from Stock import Stock
from multiprocessing import Process, Queue
import time
from utilities import handle_console_interface, print_banner
from tqdm import tqdm
from AssistantDataLoader import AssistantDataLoader
import yfinance as yf
from terminaltables import AsciiTable
import warnings
import gc

class Assistant:
    def __init__(self, q, logger_queue, additional_data_queue, max_processes, create_dictionary, create_stocks_list,
                 dictionary_file_path, stocks_file_path, web_stocks_limit, max_stocks_list_size, max_surpriver_stocks_num,
                 prepost, run_surpriver, tickers=None):
        # Queues
        self._q = q
        self._additional_queue = additional_data_queue
        self._console_interface_queue = Queue()
        self._logger_queue = logger_queue

        # Config
        data_loader = AssistantDataLoader(logger_queue=logger_queue,
                                          create_dictionary=create_dictionary,
                                          create_stocks_list=create_stocks_list,
                                          dictionary_file_path=dictionary_file_path,
                                          stocks_file_path=stocks_file_path,
                                          web_stocks_limit=web_stocks_limit,
                                          max_stocks_list_size=max_stocks_list_size,
                                          max_surpriver_stocks_num=max_surpriver_stocks_num,
                                          run_surpriver=run_surpriver)
        self._tickers, self._surpriver_tickers = data_loader.get_tickers(tickers)
        self._max_processes = min([max_processes, len(self._tickers)])
        self._processes = {}
        self._interface = Process()
        self._show_prepost = prepost
        self._run_surpriver = run_surpriver

        del data_loader
        gc.collect()

    def start_monitoring(self, tickers, show_progress=True):
        warnings.filterwarnings("ignore")
        self._logger_queue.put(["INFO", "  Assistant: Starting monitoring given tickers"])
        processes = {}
        tickers = tickers[:self._max_processes]

        if show_progress:
            print_banner("Downloading final data", "cyan")
            print("[+] Downloading data for day trading assistant from yahoo finance (up to 3 minutes)...")

        data = yf.download(
            tickers=" ".join(tickers),
            period="1y",
            interval="1d",
            group_by='ticker')

        data_for_chart = yf.download(
            tickers=" ".join(tickers),
            period="30d",
            interval="5m",
            group_by='ticker',
            prepost=self._show_prepost)

        data.to_pickle("data/data.pkl")
        data_for_chart.to_pickle("data/data_for_chart.pkl")

        del data
        del data_for_chart


        gc.collect()

        if show_progress:
            print_banner('Preparing Trades', 'magenta')

        if show_progress:
            for ticker in tqdm(tickers):
                self._logger_queue.put(["DEBUG", f"  Assistant: Starting {ticker}"])
                s = Stock(ticker, queue=self._q, logger_queue=self._logger_queue, additional_queue=self._additional_queue)
                s.name = ticker
                s.start()
                processes[ticker] = s
                self._logger_queue.put(["DEBUG", f"  Assistant: {ticker} started"])
                gc.collect()
        else:
            for ticker in tickers:
                self._logger_queue.put(["DEBUG", f"  Assistant: Starting {ticker}"])
                s = Stock(ticker, queue=self._q, logger_queue=self._logger_queue, additional_queue=self._additional_queue)
                s.name = ticker
                s.start()
                processes[ticker] = s
                self._logger_queue.put(["DEBUG", f"  Assistant: {ticker} started"])
                gc.collect()

        return processes

    def start_console_interface(self):
        self._logger_queue.put(["INFO", "  Assistant: Starting console interface"])
        interface = Process(target=handle_console_interface, args=(self._logger_queue, self._q, self._max_processes,
                                                                   self._surpriver_tickers, self._console_interface_queue))
        interface.name = "console_interface"
        interface.start()

        return interface

    def handle_input(self):
        self._logger_queue.put(["INFO", "  Assistant: Handling input started"])

        try:
            while True:
                inp = input()

                if inp in self._processes.keys() or inp.split(" ")[0] in self._processes.keys():
                    if inp.split(" ")[-1] == "window" and inp.split(" ")[0] in self._processes.keys():
                        self._processes[inp.split(" ")[0]].show_chart(window=True)
                    elif inp in self._processes.keys():
                        self._processes[inp].show_chart(window=False)
                    else:
                        print("[-] Wrong command")
                elif inp.lower() == "exit":
                    break
                elif len(inp) > 0 and inp[0] == '+' and not inp.isnumeric():
                    if len(inp) > 1:
                        symbols_tmp = inp.replace("+", "").split(" ")
                        symbols = []

                        for symbol in symbols_tmp:
                            if symbol.upper() not in self._processes.keys():
                                symbols.append(symbol)
                            else:
                                print(f"[-] {symbol} is already added")

                        if len(symbols) > 0:
                            self._processes.update(self.start_monitoring(symbols, show_progress=False))
                            self._tickers.append(inp[1:])
                            self._q.put({"max_processes": "+1"})
                elif inp == "surpriver":
                    if self._run_surpriver:
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
                    else:
                        print("[-] Surpriver is not running.")
                elif "show" in inp:
                    self._q.put({"get_worth_buying": ""})

                    worth_buying = self._console_interface_queue.get()

                    splitted_inp = inp.split(" ")

                    if len(splitted_inp) == 3:
                        show_from = int(splitted_inp[1])
                        if show_from >= len(worth_buying):
                            show_from = 0
                        show_to = int(splitted_inp[2])
                    elif len(splitted_inp) == 2:
                        show_from = 0
                        show_to = int(splitted_inp[1])
                    else:
                        show_to = 0
                        show_from = 0
                        print("[-] Wrong command")

                    for stock in worth_buying[show_from:show_to]:
                        self._processes[stock].show_chart(window=True)
                elif inp == "help" or inp == "?":
                    print("Commands:")
                    print("\t <TICKER>                      = Shows chart of given ticker")
                    print("\t <TICKER> window               = Shows chart of given ticker with another chart window")
                    print("\t +<TICKER> <TICKER2> ...       = Adds tickers for analysis")
                    print("\t surpriver                     = Shows stocks picked by surpriver")
                    print("\t show <a> <b>                  = Shows charts for stocks from a to b that are worth buying\n"+
                                                            "ie. show 0 5  = Show charts for stocks on positions from 0 to 5")
                    print("\t exit                          = Close day trading assistant")
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

