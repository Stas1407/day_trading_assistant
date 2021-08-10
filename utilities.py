import os
from pyfiglet import Figlet
from termcolor import colored
from colorama import init
from terminaltables import AsciiTable

def cls():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner(text, color):
    cls()
    init()

    f = Figlet(font="standard")
    print(colored(f.renderText(text), color))

def handle_console_interface(logger_queue, q, max_processes, surpriver_tickers, console_interface_queue):
    logger_queue.put(["INFO", "  Assistant-interface: Console interface started"])
    print_banner('Trades for today', "yellow")

    surpriver_tickers_dict = {}

    for symbol, prediction in surpriver_tickers:
        surpriver_tickers_dict[symbol] = prediction

    table_data = [["Ticker", "state", "Profit", "Near support", "Price", "Support", "Resistance", "Volatility", "Source"]]
    worth_attention = []
    worth_buying = []

    count = 0
    while True:
        stock = q.get()

        logger_queue.put(["DEBUG", f"  Assistant-interface: Received: {stock}"])

        if "max_processes" in stock.keys():
            max_processes += 1
            continue

        if "get_worth_buying" in stock.keys():
            console_interface_queue.put(worth_buying)
            continue

        if stock['ticker'] == "exit":
            print_banner("Goodbye !", "green")
            print("[+] Exiting...")
            logger_queue.put(["INFO", "  Assistant-interface: Got exit flag. Exiting..."])
            break
        elif stock['state'] == "skip":
            max_processes -= 1
        elif stock['state'] == "worth attention":
            source = "Web scraper"
            worth_attention.append(stock["ticker"])

            if stock["ticker"] in surpriver_tickers_dict.keys():
                source = "Surpriver (" + str(surpriver_tickers_dict[stock["ticker"]]) + ") "

            if stock['profit'] == "Unknown":
                table_data.append([stock["ticker"],
                                   stock["state"],
                                   stock["profit"],
                                   stock["is_near_support"],
                                   round(stock["price"], 2),
                                   round(stock["support"], 2),
                                   stock["resistance"],
                                   stock["volatility"],
                                   source])
            else:
                table_data.append([stock["ticker"],
                                   stock["state"],
                                   str(int(stock["profit"])) + " %",
                                   stock["is_near_support"],
                                   round(stock["price"], 2),
                                   round(stock["support"], 2),
                                   round(stock["resistance"], 2),
                                   stock["volatility"],
                                   source])
            count += 1
        else:
            count += 1

        logger_queue.put(["DEBUG", f"  Assistant-interface: Max_processes: {max_processes}, count: {count}"])
        if count == max_processes:
            print_banner('Trades for today', "yellow")
            table_data = sorted(table_data, key=lambda x: x[1])
            table = AsciiTable(table_data)
            print(table.table)
            print("Ticker (type exit to exit): ", end="")

            count = 0
            table_data = [["Ticker", "State", "Profit", "Near support", "Price", "Support", "Resistance", "Volatility", "Source"]]
            worth_buying = worth_attention.copy()
            worth_attention.clear()
