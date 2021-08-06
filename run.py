from utilities import print_banner
from multiprocessing import Queue
from Assistant import Assistant
from CentralLogger import CentralLogger

def main():
    print_banner('Welcome to day trading assistant', 'green')

    TICKERS = []
    MAX_PROCESSES = 50
    create_dictionary = False
    create_stocks_list = False
    dict_path = "surpriver/stocks/best_stocks.txt"
    stocks_path = "surpriver/dictionaries/data"

    q = Queue()
    logging_queue = Queue()
    additional_data_queue = Queue()

    logger = CentralLogger(logging_queue)
    logger.start()

    a = Assistant(q, logging_queue, additional_data_queue, MAX_PROCESSES, create_dictionary, create_stocks_list,
                  dict_path, stocks_path, tickers=TICKERS)
    a.run()


if __name__ == '__main__':
    main()
