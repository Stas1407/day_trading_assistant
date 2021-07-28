import pandas as pd
import numpy as np
import yfinance
from mplfinance.original_flavor import candlestick_ohlc
import matplotlib.dates as mpl_dates
import matplotlib.pyplot as plt
from pytz import timezone

class SupportResistance:
    def __init__(self, name, interval, period, interval_chart, period_chart):
        self._levels = []

        self.__name = name
        # Setting up data for finding levels (support and resistance)
        ticker = yfinance.Ticker(name)
        self._df = ticker.history(interval=interval, period=period)
        self._df['Date'] = pd.to_datetime(self._df.index)
        self._df['Date'] = self._df['Date'].apply(mpl_dates.date2num)
        self._df = self._df.loc[:, ['Date', 'Open', 'High', 'Low', 'Close']]
        
        self.__volatility = np.mean(self._df['High'] - self._df['Low'])

        # Setting up data for chart
        self._df_for_chart = ticker.history(interval=interval_chart, period=period_chart)
        self._df_for_chart['Date'] = pd.to_datetime(self._df_for_chart.index)
        self._df_for_chart['Date'] = self._df_for_chart['Date'].apply(mpl_dates.date2num)
        self._df_for_chart = self._df_for_chart.loc[:, ['Date', 'Open', 'High', 'Low', 'Close']]

    @property
    def ticker(self):
        return self.__name
    
    @property
    def volatility(self):
        return self.__volatility

    @property
    def levels(self):
        return self._levels

    def _is_support(self, i):
        support = self._df['Low'][i] < self._df['Low'][i - 1] < self._df['Low'][i - 2] and \
                  self._df['Low'][i] < self._df['Low'][i + 1] < self._df['Low'][i + 2]
        return support

    def _is_resistance(self, i):
        resistance = self._df['High'][i] > self._df['High'][i - 1] > self._df['High'][i - 2] and \
                     self._df['High'][i] > self._df['Close'][i + 1] > self._df['Close'][i + 2]
        return resistance

    def _is_far_from_level(self, l):
        return np.sum([abs(l - x) < self.__volatility for x in self._levels]) == 0

    def find_levels(self, df):
        for i in range(2, df.shape[0] - 2):
            if self._is_support(i):
                l = df['Low'][i]
                if self._is_far_from_level(l):
                    self._levels.append((i, l))
            elif self._is_resistance(i):
                l = df['High'][i]
                if self._is_far_from_level(l):
                    self._levels.append((i, l))

    def get_current_price(self):
        ticker = yfinance.Ticker(self.__name)
        data = ticker.history(period='1d')
        return data['Close'][0]

    def show_chart(self, dformat="%d/%b/%Y %H:%M", candle_width=0.6/(24 * 15), show_levels=True):
        fig, ax = plt.subplots()
        candlestick_ohlc(ax, self._df_for_chart.values, width=candle_width,
                         colorup='green', colordown='red', alpha=0.8)
        date_format = mpl_dates.DateFormatter(dformat)
        date_format.set_tzinfo(timezone('America/New_york'))
        ax.xaxis.set_major_formatter(date_format)
        ax.xaxis.set_major_locator(mpl_dates.MinuteLocator((0, 30)))

        fig.autofmt_xdate()
        fig.tight_layout()
        fig.set_size_inches(10.5, 6.5)

        t = str(self._df_for_chart.index[0])

        fig.suptitle(self.__name + " " + t, fontsize=16, y=0.98)
        fig.subplots_adjust(top=0.8, left=0.08)
        current_price = self.get_current_price()
        print(current_price)

        if show_levels:
            for level in self._levels:
                if current_price + 5 * self.__volatility > level[1] > current_price - 5 * self.__volatility:
                    if level[1] > current_price:
                        color = "red"
                    else:
                        color = "green"
                    plt.hlines(level[1], xmin=self._df_for_chart['Date'][0],
                               xmax=max(self._df_for_chart['Date']), colors=color)
                    plt.text(self._df_for_chart['Date'][0], level[1]+0.02*current_price, round(level[1], 2), ha="left", va='center')

        fig.show()

    def run(self):
        self.find_levels(self._df)
        self.find_levels(self._df_for_chart)
        self.show_chart()

        input("Press enter to exit")
