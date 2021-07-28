from pyfiglet import Figlet
from termcolor import colored
from colorama import init
import os


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    cls()
    init()

    f = Figlet(font="standard")
    print(colored(f.renderText('Welcome to day trading assistant'), "green"))