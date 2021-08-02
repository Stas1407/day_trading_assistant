import os
from pyfiglet import Figlet
from termcolor import colored
from colorama import init
from terminaltables import AsciiTable
import requests
from bs4 import BeautifulSoup

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

        logger_queue.put(["DEBUG", f"  Assistant-interface: Received: {stock}"])

        if "max_processes" in stock.keys():
            max_processes += 1
            continue

        if stock['ticker'] == "exit":
            print_banner("Goodbye !", "green")
            logger_queue.put(["INFO", "  Assistant-interface: Got exit flag. Exiting..."])
            break
        elif stock['recommendation'] == "skip":
            max_processes -= 1
        elif stock['recommendation'] != "watch":
            if stock['profit'] == "Unknown":
                table_data.append([stock["ticker"],
                                   stock["recommendation"],
                                   stock["profit"],
                                   stock["is_near_support"],
                                   round(stock["price"], 2),
                                   round(stock["support"], 2),
                                   stock["resistance"]])
            else:
                table_data.append([stock["ticker"],
                                   stock["recommendation"],
                                   str(int(stock["profit"])) + " %",
                                   stock["is_near_support"],
                                   round(stock["price"], 2),
                                   round(stock["support"], 2),
                                   round(stock["resistance"], 2)])
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
            table_data = [["Ticker", "Recommendation", "Profit", "Near support", "Price", "Support", "Resistance"]]


def scraper():
    response = requests.get("https://sampom100.github.io/UnusualVolumeDetector_Dynamic/")
    s = BeautifulSoup(response.content, "html.parser")

    tab = []

    for row in s.find_all('tr'):
        ticker = row.find("th")
        if len(ticker.text) <= 4:
            tab.append(ticker.text)

    return tab
