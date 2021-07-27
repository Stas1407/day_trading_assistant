import pandas as pd
import numpy as np
import yfinance
from mplfinance.original_flavor import candlestick_ohlc
import matplotlib.dates as mpl_dates
import matplotlib.pyplot as plt

class SupportResistance:
    def __init__(self, name, interval, period, interval_chart, period_chart):
        self.levels = []

        self.name = name
        # Setting up data for finding levels (support and resistance)
        ticker = yfinance.Ticker(name)
        self.df = ticker.history(interval=interval, period=period)
        self.df['Date'] = pd.to_datetime(self.df.index)
        self.df['Date'] = self.df['Date'].apply(mpl_dates.date2num)
        self.df = self.df.loc[:, ['Date', 'Open', 'High', 'Low', 'Close']]
        
        self.volatility = np.mean(self.df['High'] - self.df['Low'])

        # Setting up data for chart
        self.df_for_chart = ticker.history(interval=interval_chart, period=period_chart)
        self.df_for_chart['Date'] = pd.to_datetime(self.df_for_chart.index)
        self.df_for_chart['Date'] = self.df_for_chart['Date'].apply(mpl_dates.date2num)
        self.df_for_chart = self.df_for_chart.loc[:, ['Date', 'Open', 'High', 'Low', 'Close']]

    def is_support(self, i):
        support = self.df['Low'][i] < self.df['Low'][i - 1] < self.df['Low'][i - 2] and \
                  self.df['Low'][i] < self.df['Low'][i + 1] < self.df['Low'][i + 2]
        return support

    def is_resistance(self, i):
        resistance = self.df['High'][i] > self.df['High'][i - 1] > self.df['High'][i - 2] and \
                     self.df['High'][i] > self.df['Close'][i + 1] > self.df['Close'][i + 2]
        return resistance

    def is_far_from_level(self, l):
        return np.sum([abs(l - x) < self.volatility for x in self.levels]) == 0

    def find_levels(self):
        for i in range(2, self.df.shape[0] - 2):
            if self.is_support(i):
                l = self.df['Low'][i]
                if self.is_far_from_level(l):
                    self.levels.append((i, l))
            elif self.is_resistance(i):
                l = self.df['High'][i]
                if self.is_far_from_level(l):
                    self.levels.append((i, l))

    def get_current_price(self):
        ticker = yfinance.Ticker(self.name)
        data = ticker.history(period='1d')
        return data['Close'][0]

    def show_chart(self, dformat="%d/%b/%Y %H:%M", candle_width=0.6/(24 * 15), show_levels=True):
        fig, ax = plt.subplots()
        candlestick_ohlc(ax, self.df_for_chart.values, width=candle_width,
                         colorup='green', colordown='red', alpha=0.8)
        date_format = mpl_dates.DateFormatter(dformat)
        ax.xaxis.set_major_formatter(date_format)
        ax.xaxis.set_major_locator(mpl_dates.MinuteLocator((0, 30)))

        fig.autofmt_xdate()
        fig.tight_layout()

        t = str(self.df_for_chart.index[0])

        fig.suptitle(self.name + " " + t, fontsize=16, y=0.98)
        fig.subplots_adjust(top=0.8, left=0.08)
        current_price = self.get_current_price()
        print(current_price)

        if show_levels:
            for level in self.levels:
                if current_price + 3 * self.volatility > level[1] > current_price - 3 * self.volatility:
                    print(level)
                    if level[1] > current_price:
                        color = "red"
                    else:
                        color = "green"
                    plt.hlines(level[1], xmin=self.df_for_chart['Date'][2],
                               xmax=max(self.df_for_chart['Date']), colors=color)
                    plt.text(self.df_for_chart['Date'][0], level[1], round(level[1], 2), ha="left", va='center')

        fig.show()

    def run(self):
        self.find_levels()
        self.show_chart()

        input("Press enter to exit")
