from support_resistance import Stock
from multiprocessing import Process, Event
import time
from utilities import handle_console_interface
from tqdm import tqdm

class Assistant:
    def __init__(self, tickers, q, logger_queue, max_processes):        # TODO: Remove tickers and use a class function / another class (scraper) instead
        self._q = q
        self._tickers = tickers
        self._logger_queue = logger_queue

        self._max_processes = max_processes
        self._processes = {}
        self._interface = Process()

    def start_monitoring(self, tickers):
        self._logger_queue.put(["INFO", "  Assistant: Starting monitoring given tickers"])
        processes = {}

        for ticker in tqdm(tickers[:self._max_processes]):
            self._logger_queue.put(["DEBUG", f"  Assistant: Starting {ticker}"])
            s = Stock(ticker, interval="1d", period="1y", interval_chart="5m", period_chart="1d", queue=self._q,
                      logger_queue=self._logger_queue)
            s.name = ticker
            s.start()
            processes[ticker] = s
            self._logger_queue.put(["DEBUG", f"  Assistant: {ticker} started"])

        return processes

    def start_console_interface(self):
        self._logger_queue.put(["INFO", "  Assistant: Starting console interface"])
        interface = Process(target=handle_console_interface, args=(self._logger_queue, self._q, self._max_processes))
        interface.name = "console_interface"
        interface.start()

        return interface

    def handle_input(self):
        self._logger_queue.put(["INFO", "  Assistant: Handling input started"])

        while True:
            inp = input()

            if inp.isnumeric():
                self._processes[self._tickers[int(inp)]].show_chart()
            elif inp in self._processes.keys():
                self._processes[inp].show_chart()
            elif inp.lower() == "exit":
                break
            else:
                print("[-] Wrong ticker")

            print("Ticker (type exit to exit): ", end='')
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

