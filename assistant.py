from support_resistance import Stock
from multiprocessing import Process, Event
import time

class Assistant:
    def __init__(self, tickers, q):        # TODO: Remove tickers and use a class function / another class (scraper) instead
        self.q = q
        self.tickers = tickers

        self.processes = {}
        self.interface = Process()

        self._stop_interface_event = Event()

    def start_monitoring(self, tickers):
        processes = {}

        for ticker in tickers:
            print("[+] Starting ", ticker)
            s = Stock(ticker, interval="1d", period="1y", interval_chart="5m", period_chart="1d", queue=self.q)
            s.name = ticker
            s.start()
            processes[ticker] = s
            print(ticker, " started")

        return processes

    def start_console_interface(self):
        interface = Process(target=self.handle_console_interface, args=(self.q,))
        interface.name = "interface"
        interface.start()

        return interface

    def handle_console_interface(self):
        print("[+] Started reading from queue")
        while True:
            if self._stop_interface_event.is_set():
                break

            state = self.q.get()
            print("Handling queue process: ", state)

    def handle_input(self):
        pass
        # TODO

    def run(self):
        self.processes = self.start_monitoring(self.tickers)
        self.interface = self.start_console_interface()
        self.handle_input()

    def stop(self):
        print("Exiting")
        for ticker, proc in self.processes.items():
            print(ticker, " requesting to stop")
            proc.stop()

        self._stop_interface_event.set()

        time.sleep(3)

        for ticker, proc in self.processes.items():
            if proc.is_alive():
                print(ticker, " did not exit, terminating...")
                proc.terminate()

        if self.interface.is_alive():
            self.interface.terminate()

        while not self.q.empty():
            print("Queue is not empty")
            item = self.q.get()
            print("Cleaning queue ", item)

        self.q.close()
        self.q.join_thread()
