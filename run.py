from utilities import print_banner
from multiprocessing import Queue
from Assistant import Assistant
from central_logger import CentralLogger

def main():
    print_banner('Welcome to day trading assistant', 'green')

    TICKERS = []
    MAX_PROCESSES = 50

    q = Queue()
    logging_queue = Queue()

    logger = CentralLogger(logging_queue)
    logger.start()

    a = Assistant(q, logging_queue, MAX_PROCESSES, tickers=TICKERS)
    a.run()


if __name__ == '__main__':
    main()
