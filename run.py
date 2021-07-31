from utilities import print_banner
from multiprocessing import Queue
from assistant import Assistant
from central_logger import CentralLogger

if __name__ == '__main__':
    print_banner()

    tickers = ["NAOV", "XBIO"]

    q = Queue()
    logging_queue = Queue()

    logger = CentralLogger(logging_queue)
    logger.start()

    a = Assistant(tickers, q, logging_queue)
    a.run()

    # if logger.is_alive():
    #     logger.terminate()

