from utilities import print_banner
from multiprocessing import Queue
from assistant import Assistant
from central_logger import CentralLogger

def main():
    print_banner('Welcome to day trading assistant', 'green')

    tickers = ["MSFT", "ZS", "PANW", "PAYA", "NSA", "SMSI", "PZZA", "SREV"]
    max_processes = len(tickers)

    q = Queue()
    logging_queue = Queue()

    logger = CentralLogger(logging_queue)
    logger.start()

    a = Assistant(tickers, q, logging_queue, max_processes)
    a.run()


if __name__ == '__main__':
    main()
