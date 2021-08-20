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

## Usage:
Install requirements: `pip3 install -r requirements.txt`
If you have problems installing requirements I recommend to use conda virtual environment.
Run program with command: `python3 run.py`
Than it will ask you a few simple questions about the mode that you would like to run the program in.
More important ones are:
  - `How many processes can it run?` = The more processes it runs the more memory (RAM) it uses (40 processes = around 4GB)
  - `Do you want to run surpriver?` = Running surpriver equals longer startup time but more results
  - `Do you want to run surpriver with new data?` = Download and prepare new data for surpriver. Otherwise it will use data from previous run. **If this is your first time using        day trading assistant and you want to run surpriver you have to agree.**

