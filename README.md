# Day Trading Assistant

Program that finds great stocks for day trading.

## How it works?
It filters out stocks by volume, volatility, price and market cap to find stocks with the largest number of people trading it at the moment.
Then it analyzes selected stocks every 4-5 minutes and looks for patterns:
  - price near support zone and there is place to move up
  - price near lower bollinger band and there is place to move up.

### Sources:
For finding the best stocks to monitor it uses:
  - https://github.com/tradytics/surpriver  (Modyfied by me here: https://github.com/Stas1407/surpriver)
  - https://unusualvolume.info/
  - https://financialmodelingprep.com

## Setup:
Clone day trading assistant repository: `git clone https://github.com/Stas1407/day_trading_assistant.git`  \
Cd into project directory: `cd day_trading_assistant`  \
Clone surpriver repository: `git clone https://github.com/Stas1407/surpriver.git`  \
Install requirements: `pip3 install -r requirements.txt`\
If you have problems installing requirements I recommend to use conda virtual environment.\
You also need to register at https://financialmodelingprep.com to receive a free api key which has to be placed in secrets.py file.  \

## Usage:
Run program with command: `python3 run.py`\
Then it will ask you a few simple questions about the mode that you would like to run the program in.\
More important ones are:
  - `How many processes can it run?` = The more processes it runs the more memory (RAM) it uses (40 processes = around 4GB)
  - `Do you want to run surpriver?` = Running surpriver equals longer startup time but more results
  - `Do you want to run surpriver with new data?` = Download and prepare new data for surpriver. Otherwise it will use data from previous run. **If this is your first time using        day trading assistant and you want to run surpriver you have to agree.**


## Limitations
This program as the name assistant suggests is supposed to help you trading but won't do all of the work for you.
It just finds stocks that can be worth your attention at the moment (ie. they have high volume and volatility and are near support zone).
I recommend using it as a side tool/scanner that can ***help*** you trade.
