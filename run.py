from utilities import print_banner
from multiprocessing import Queue
from assistant import Assistant

if __name__ == '__main__':
    print_banner()

    tickers = ["NAOV", "XBIO"]

    q = Queue()

    a = Assistant(tickers, q)
    a.run()

