from support_resistance import SupportResistance
from banner import print_banner
from multiprocessing import Queue, Process
import time
from utilities import handle_console_interface

if __name__ == '__main__':
    print_banner()

    tickers = ["NAOV", "XBIO"]  # EDU
    stocks = {}

    q = Queue()

    for ticker in tickers:
        print("[+] Starting ", ticker)
        s = SupportResistance(ticker, interval="1d", period="1y", interval_chart="5m", period_chart="1d", queue=q)
        s.name = ticker
        s.start()
        stocks[ticker] = s
        print(ticker, " started")

    print("[+] Starting queue reading process")

    q_read_proc = Process(target=handle_console_interface, args=(q,))
    q_read_proc.name = "q_read_proc"
    q_read_proc.start()

    while True:
        inp = input("Type in chart number, -1 to exit: ")
        if inp == "-1":
            break
        elif int(inp) < len(tickers):
            print("Showing chart of ", tickers[int(inp)])
            stocks[tickers[int(inp)]].show_chart()
            print("Chart shown")
        else:
            print("Invalid number")

    # -------------------- Cleaning up ---------------------------
    print("Exiting")
    for ticker, proc in stocks.items():
        print(ticker, " requesting to stop")
        proc.stop()

    time.sleep(3)

    for ticker, proc in stocks.items():
        if proc.is_alive():
            print(ticker, " did not exit, terminating...")
            proc.terminate()

    q_read_proc.terminate()

    while not q.empty():
        print("Queue is not empty")
        item = q.get()
        print("Cleaning queue ", item)

    q.close()
    q.join_thread()

