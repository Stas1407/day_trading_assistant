from utilities import print_banner
from multiprocessing import Queue
from Assistant import Assistant
from CentralLogger import CentralLogger

def main():
    print_banner('Welcome to day trading assistant', 'green')

    tickers = []

    max_processes = 40
    web_stocks_limit = 35
    max_surpriver_stocks_num = 5

    run_surpriver = False

    show_prepost = False

    create_dictionary = False
    create_stocks_list = False

    max_stocks_list_size = 1200
    dict_path = "surpriver/dictionaries/data"
    stocks_path = "best_stocks.txt"

    if stocks_path == "stocks.txt" and create_stocks_list:
        print("Cannot overwrite this file")
        return

    q = Queue()
    logging_queue = Queue()
    additional_data_queue = Queue()

    logger = CentralLogger(logging_queue)
    logger.start()

    a = Assistant(q, logging_queue, additional_data_queue, max_processes, create_dictionary, create_stocks_list,
                  dict_path, stocks_path, web_stocks_limit, max_stocks_list_size, max_surpriver_stocks_num,
                  show_prepost, run_surpriver, tickers=tickers)
    a.run()


if __name__ == '__main__':
    main()
