import pandas as pd
import numpy as np
import yfinance
from mplfinance.original_flavor import candlestick_ohlc
import matplotlib.dates as mpl_dates
import matplotlib.pyplot as plt
import matplotlib
import time
from datetime import datetime
import pytz

def is_support(df, i):
    support = df['Low'][i] < df['Low'][i - 1] < df['Low'][i - 2] and \
              df['Low'][i] < df['Low'][i + 1] < df['Low'][i + 2]
    return support


def is_resistance(df, i):
    resistance = df['High'][i] > df['High'][i - 1] > df['High'][i - 2] and \
                 df['High'][i] > df['Close'][i + 1] > df['Close'][i + 2]
    return resistance

def is_far_from_level(l, s):
    return np.sum([abs(l-x) < s for x in levels]) == 0

def chart():
    name = "XBIO"
    ticker = yfinance.Ticker(name)
    df5 = ticker.history(interval="5m", period="1d")

    df5.index = df5.index.tz_convert("America/New_York")
    df5['Date'] = pd.to_datetime(df5.index)
    df5['Date'] = df5['Date'].apply(mpl_dates.date2num)
    df5 = df5.loc[:, ['Date', 'Open', 'High', 'Low', 'Close']]

    fig, ax = plt.subplots()
    candlestick_ohlc(ax, df5.values, width=0.6/(24*15),
                     colorup='green', colordown='red', alpha=0.8)
    date_format = mpl_dates.DateFormatter('%d/%b/%Y %H:%M')
    ax.xaxis.set_major_formatter(date_format)
    ax.xaxis.set_major_locator(mpl_dates.MinuteLocator((0, 30)))

    fig.autofmt_xdate()
    fig.tight_layout()

    t = str(df5.index[0])

    fig.suptitle("XBIO "+t, fontsize=16, y=0.98)
    fig.subplots_adjust(top=0.8)
    current_price = df5['Close'][len(df5['Close'])-1]
    print(s)
    for level in levels:
        if current_price + 3*s > level[1] > current_price-3*s:
            print(level)
            plt.hlines(level[1], xmin=df5['Date'][0],
                       xmax=max(df5['Date']), colors='blue')
    fig.show()


name = "XBIO"
ticker = yfinance.Ticker(name)
df = ticker.history(interval="1d", period="1y")

df['Date'] = pd.to_datetime(df.index)
df['Date'] = df['Date'].apply(mpl_dates.date2num)
df = df.loc[:, ['Date', 'Open', 'High', 'Low', 'Close']]
s = np.mean(df['High'] - df['Low'])

levels = []
for i in range(2,df.shape[0]-2):
    if is_support(df, i):
        l = df['Low'][i]
        if is_far_from_level(l, s):
            levels.append((i, l))
    elif is_resistance(df, i):
        l = df['High'][i]
        if is_far_from_level(l, s):
            levels.append((i, l))

chart()
input("")