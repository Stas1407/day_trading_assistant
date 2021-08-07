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

    surpriver_tickers = [i[0] for i in surpriver_tickers]

    table_data = [["Ticker", "Recommendation", "Profit", "Near support", "Price", "Support", "Resistance", "Volatility"]]
    worth_attention = []
    worth_buying = []

    count = 0
    while True:
        stock = q.get()

        logger_queue.put(["DEBUG", f"  Assistant-interface: Received: {stock}"])
        logger_queue.put(["DEBUG", f"  Assistant-interface: Surpriver tickers {surpriver_tickers}"])

        if "max_processes" in stock.keys():
            max_processes += 1
            continue

        if "get_worth_buying" in stock.keys():
            console_interface_queue.put(worth_buying)
            continue

        if stock['ticker'] == "exit":
            print_banner("Goodbye !", "green")
            logger_queue.put(["INFO", "  Assistant-interface: Got exit flag. Exiting..."])
            break
        elif stock['recommendation'] == "skip":
            max_processes -= 1
        elif stock['recommendation'] != "watch":
            worth_attention.append(stock["ticker"])

            if stock["ticker"] in surpriver_tickers:
                stock["ticker"] += " S"

            if stock['profit'] == "Unknown":
                table_data.append([stock["ticker"],
                                   stock["recommendation"],
                                   stock["profit"],
                                   stock["is_near_support"],
                                   round(stock["price"], 2),
                                   round(stock["support"], 2),
                                   stock["resistance"],
                                   stock["volatility"]])
            else:
                table_data.append([stock["ticker"],
                                   stock["recommendation"],
                                   str(int(stock["profit"])) + " %",
                                   stock["is_near_support"],
                                   round(stock["price"], 2),
                                   round(stock["support"], 2),
                                   round(stock["resistance"], 2),
                                   stock["volatility"]])
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
            table_data = [["Ticker", "Recommendation", "Profit", "Near support", "Price", "Support", "Resistance", "Volatility"]]
            worth_buying = worth_attention.copy()
            worth_attention.clear()
