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

def handle_console_interface(logger_queue, q, max_processes):
    logger_queue.put(["INFO", "  Assistant-interface: Console interface started"])
    print_banner('Trades for today', "yellow")

    table_data = [["Ticker", "Recommendation", "Profit", "Near support", "Price", "Support", "Resistance"]]

    count = 0
    while True:
        stock = q.get()

        if count == max_processes:
            count = 0
            print_banner('Trades for today', "yellow")
            table_data = [["Ticker", "Recommendation", "Profit", "Near support", "Price", "Support", "Resistance"]]

        logger_queue.put(["DEBUG", f"  Assistant-interface: Received: {stock}"])
        if stock['ticker'] == "exit":
            print_banner("Goodbye !", "green")
            logger_queue.put(["INFO", "  Assistant-interface: Got exit flag. Exiting..."])
            break

        table_data.append([stock["ticker"],
                           stock["recommendation"],
                           str(int(stock["profit"]))+" %",
                           stock["is_near_support"],
                           round(stock["price"], 2),
                           round(stock["support"], 2),
                           round(stock["resistance"], 2)])

        count += 1
        if count == max_processes:
            table_data = sorted(table_data, key=lambda x: x[1])
            table = AsciiTable(table_data)
            print(table.table)
            print("Ticker (type exit to exit): ", end="")
