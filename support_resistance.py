import pandas as pd
import numpy as np
import yfinance
from mplfinance.original_flavor import candlestick_ohlc
import matplotlib.dates as mpl_dates
import matplotlib.pyplot as plt
from pytz import timezone
from multiprocessing import Process, Event
import time
import schedule
import webbrowser

class Stock(Process):
    def __init__(self, ticker, interval, period, interval_chart, period_chart, queue, logger_queue):
        Process.__init__(self)

        self._q = queue
        self._stop_event = Event()
        self._show_chart_event = Event()
        
        self.logger_queue = logger_queue

        self.url = "https://www.tradingview.com/chart/?symbol="+ticker

        self._levels = []

        self.__ticker = ticker

        # Setting up data for finding levels (support and resistance)
        yticker = yfinance.Ticker(ticker)
        self._df = yticker.history(interval=interval, period=period)
        self._df['Date'] = pd.to_datetime(self._df.index)
        self._df['Date'] = self._df['Date'].apply(mpl_dates.date2num)
        self._df = self._df.loc[:, ['Date', 'Open', 'High', 'Low', 'Close']]
        
        self.__volatility = np.mean(self._df['High'] - self._df['Low'])

        # Setting up data for chart
        self._df_for_chart = yticker.history(interval=interval_chart, period=period_chart)
        self._df_for_chart['Date'] = pd.to_datetime(self._df_for_chart.index)
        self._df_for_chart['Date'] = self._df_for_chart['Date'].apply(mpl_dates.date2num)
        self._df_for_chart = self._df_for_chart.loc[:, ['Date', 'Open', 'High', 'Low', 'Close']]

    @property
    def ticker(self):
        return self.__ticker
    
    @property
    def volatility(self):
        return self.__volatility

    @property
    def levels(self):
        return self._levels

    def stop(self):
        self._stop_event.set()

    def show_chart(self):
        self._show_chart_event.set()

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

    def _find_levels(self, df):
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
        ticker = yfinance.Ticker(self.ticker)
        data = ticker.history(period='1d')
        return data['Close'][0]

    def check_if_worth_buying(self):
        self.logger_queue.put(["INFO", f"  Stock {self.ticker}: Checking if worth buying"])

        current_price = self.get_current_price()

        # Find two nearest levels = support and resistance
        resistance = (10000000, 10000000)
        support = (0, 0)
        for level in self.levels:
            if current_price - level[1] < 0 and resistance[1] > level[1]:
                resistance = level
            elif current_price - level[1] >= 0 and support[1] < level[1]:
                support = level

        self.logger_queue.put(["DEBUG", f"  Stock {self.ticker} - Price: {current_price}"])
        self.logger_queue.put(["INFO", f"  Stock {self.ticker} - Nearest resistance: {resistance[1]}"])
        self.logger_queue.put(["INFO", f"  Stock {self.ticker} - Nearest support: {support[1]}"])

        profit = (resistance[1]-current_price)/current_price
        is_near_support = current_price < support[1] * 1.03

        self.logger_queue.put(["DEBUG", f"  Stock {self.ticker} - Estimated profit: {round(profit, 2)*100}"])
        self.logger_queue.put(["DEBUG", f"  Stock {self.ticker} - Is near support: {is_near_support}"])

        if support[0] == 0 and support[1] == 0:
            self.logger_queue.put(["WARNING", f"  Stock {self.ticker}: Skipping, resistance and support not found"])
            self._q.put([self.ticker, "skip"])
        elif resistance[0] == 0 and resistance[1] == 0:
            if is_near_support:
                self.logger_queue.put(["INFO", f"  Stock {self.ticker}: Worth buying, but resistance not found"])

                self._q.put([self.ticker, "buy, no resistance"])
            else:
                self.logger_queue.put(["INFO", f"  Stock {self.ticker}: Not worth buying. Keeping an eye on this one."])
                self._q.put([self.ticker, "watch"])
        elif is_near_support and profit >= 0.2:
            self.logger_queue.put(["INFO", f"  Stock {self.ticker}: Worth buying"])
            self._q.put([self.ticker, "buy"])
        else:
            self.logger_queue.put(["INFO", f"  Stock {self.ticker}: Not worth buying. Keeping an eye on this one."])
            self._q.put([self.ticker, "watch"])

    def _show_chart(self, dformat="%d/%b/%Y %H:%M", candle_width=0.6/(24 * 15), show_levels=True):
        self.logger_queue.put(["INFO", f"  Stock {self.ticker}: Showing chart"])
        webbrowser.get("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s").open(self.url)

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

        fig.suptitle(self.ticker + " " + t, fontsize=16, y=0.98)
        fig.subplots_adjust(top=0.8, left=0.08)
        current_price = self.get_current_price()

        if show_levels:
            for level in self._levels:
                if current_price + 5 * self.__volatility > level[1] > current_price - 5 * self.__volatility:
                    if level[1] > current_price:
                        color = "red"
                    else:
                        color = "green"
                    plt.hlines(level[1], xmin=self._df_for_chart['Date'][0],
                               xmax=max(self._df_for_chart['Date']), colors=color)
                    plt.text(self._df_for_chart['Date'][0], level[1]+0.01, round(level[1], 2), ha="left", va='center')

        plt.show()

    def __watch(self):
        self.logger_queue.put(["INFO", f"  Stock {self.ticker}: Started watching"])
        schedule.every(1).minutes.do(self.check_if_worth_buying)

        chart_process = Process(target=self._show_chart)

        while True:
            if self._stop_event.is_set():
                self.logger_queue.put(["INFO", f"  Stock {self.ticker}: Got exit flag. Exiting."])

                if chart_process.is_alive():
                    self.logger_queue.put(["INFO", f"  Stock {self.ticker}: Terminating chart process"])
                    chart_process.terminate()
                break

            if self._show_chart_event.is_set():
                self.logger_queue.put(["INFO", f"  Stock {self.ticker}: Got flag, showing chart"])

                if chart_process.is_alive():
                    self.logger_queue.put(["INFO", f"  Stock {self.ticker}: Chart is already shown"])
                else:
                    chart_process = Process(target=self._show_chart)
                    chart_process.start()

                self._show_chart_event.clear()

            schedule.run_pending()
            time.sleep(1)

    def run(self):
        self._find_levels(self._df)
        self._find_levels(self._df_for_chart)

        self.logger_queue.put(["INFO", f"  Stock {self.ticker} - levels: {self.levels}"])

        self.check_if_worth_buying()
        self.__watch()
