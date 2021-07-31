from support_resistance import Stock
from multiprocessing import Process, Event
import time

class Assistant:
    def __init__(self, tickers, q, logger_queue):        # TODO: Remove tickers and use a class function / another class (scraper) instead
        self.q = q
        self.tickers = tickers
        self.logger_queue = logger_queue

        self.processes = {}
        self.interface = Process()

        self._stop_interface_event = Event()

    def start_monitoring(self, tickers):
        self.logger_queue.put(["INFO", "  Assistant: Starting monitoring given tickers"])
        processes = {}

        for ticker in tickers:
            self.logger_queue.put(["DEBUG", f"  Assistant: Starting {ticker}"])
            s = Stock(ticker, interval="1d", period="1y", interval_chart="5m", period_chart="1d", queue=self.q,
                      logger_queue=self.logger_queue)
            s.name = ticker
            s.start()
            processes[ticker] = s
            self.logger_queue.put(["DEBUG", f"  Assistant: {ticker} started"])

        return processes

    def start_console_interface(self):
        self.logger_queue.put(["INFO", "  Assistant: Starting console interface"])
        interface = Process(target=self.handle_console_interface, args=(self.q,))
        interface.name = "interface"

        return interface

    def handle_console_interface(self):
        self.logger_queue.put(["INFO", "  Assistant-interface: Console interface started"])

        while True:
            if self._stop_interface_event.is_set():
                self.logger_queue.put(["INFO", "  Assistant-interface: Got exit flag. Exiting..."])
                break

            state = self.q.get()
            self.logger_queue.put(["DEBUG", f"  Assistant-interface: Received: {state}"])

            print(state[0])

    def handle_input(self):
        self.logger_queue.put(["INFO", "  Assistant: Handling input started"])

        while True:
            inp = input("Ticker (type exit to exit): ")

            if inp.isnumeric():
                self.processes[self.tickers[int(inp)]].show_chart()
            elif inp in self.processes.keys():
                self.processes[inp].show_chart()
            elif inp.lower() == "exit":
                print("[+] Exiting. Goodbye.")
                break
            else:
                print("[-] Wrong ticker")
        self.stop()

    def run(self):
        self.processes = self.start_monitoring(self.tickers)
        self.interface = self.start_console_interface()    # TODO
        self.handle_input()

    def stop(self):
        self.logger_queue.put(["INFO", "  Assistant: Exiting"])
        for ticker, proc in self.processes.items():
            self.logger_queue.put(["DEBUG", f"[*] Assistant: {ticker} requesting to stop"])
            proc.stop()

        self.logger_queue.put(["DEBUG", "  Assistant: Requesting console interface to stop"])
        self._stop_interface_event.set()

        time.sleep(3)

        for ticker, proc in self.processes.items():
            if proc.is_alive():
                self.logger_queue.put(["WARNING", f"  Assistant: {ticker} did not exit, terminating..."])
                proc.terminate()

        if self.interface.is_alive():
            self.logger_queue.put(["WARNING", "  Assistant: console interface did not exit, terminating..."])
            self.interface.terminate()

        while not self.q.empty():
            item = self.q.get()
            self.logger_queue.put(["WARNING", f"  Assistant: Cleaning queue {item}"])

        self.logger_queue.put(["INFO", "  Assistant: Exited"])

        self.logger_queue.put(["DEBUG", "  Requesting logger to stop"])
        self.logger_queue.put(["stop", ""])

        self.q.close()
        self.logger_queue.close()

        self.q.join_thread()
        self.logger_queue.join_thread()

