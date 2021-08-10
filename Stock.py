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
    def __init__(self, ticker, data, data_for_chart, queue, logger_queue, additional_queue):
        Process.__init__(self)

        # Config
        self._chrome_path = "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s"
        self._url = "https://www.tradingview.com/chart/?symbol=" + ticker
        self._min_profit = 10        # Percent %

        # Queues
        self._q = queue
        self._additional_queue = additional_queue
        self._logger_queue = logger_queue

        # Events
        self._stop_event = Event()
        self._get_data_event = Event()
        self._show_chart_event = Event()

        # Data for finding levels (support and resistance)
        self._df = data
        self._df['Date'] = pd.to_datetime(self._df.index)
        self._df['Date'] = self._df['Date'].apply(mpl_dates.date2num)
        self._df = self._df.loc[:, ['Date', 'Open', 'High', 'Low', 'Close']]

        # Data for chart
        self._df_for_chart = data_for_chart
        self._df_for_chart['Date'] = pd.to_datetime(self._df_for_chart.index)
        self._df_for_chart['Date'] = self._df_for_chart['Date'].apply(mpl_dates.date2num)
        self._df_for_chart = self._df_for_chart.loc[:, ['Date', 'Open', 'High', 'Low', 'Close']]

        # Variables used by class
        self._levels = []
        self.__ticker = ticker
        self.__volatility = np.mean(self._df['High'] - self._df['Low'])

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

    def get_data(self):
        self._get_data_event.set()

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

        try:
            return data['Close'][0]
        except IndexError:
            return -1

    def get_nearest_support_resistance(self, current_price):
        # Find two nearest levels = support and resistance
        resistance = [10000000, 10000000]
        support = [0, 0]
        for level in self.levels:
            if current_price - level[1] < 0 and resistance[1] > level[1]:
                resistance = level
            elif current_price - level[1] >= 0 and support[1] < level[1]:
                support = level

        return support, resistance

    def check_if_worth_attention(self):
        self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Checking if worth buying"])

        current_price = self.get_current_price()

        (support, resistance) = self.get_nearest_support_resistance(current_price)

        self._logger_queue.put(["DEBUG", f"  Stock {self.ticker} - Price: {current_price}"])
        self._logger_queue.put(["INFO", f"  Stock {self.ticker} - Nearest resistance: {resistance[1]}"])
        self._logger_queue.put(["INFO", f"  Stock {self.ticker} - Nearest support: {support[1]}"])

        profit = (resistance[1]-current_price)/current_price
        is_near_support = abs(current_price-support[1]) < self.volatility

        self._logger_queue.put(["DEBUG", f"  Stock {self.ticker} - Estimated profit: {round(profit, 2)*100}"])
        self._logger_queue.put(["DEBUG", f"  Stock {self.ticker} - Is near support: {is_near_support}"])
        self._logger_queue.put(["INFO", f"  Stock {self.ticker} - Volatility: {self.volatility}"])

        if resistance[1] == 10000000:
            resistance[1] = "Not found"
            profit = "Unknown"
        else:
            profit = round(profit, 2)*100

        info = {'ticker': self.ticker,
                'state': "",
                'price': current_price,
                'resistance': resistance[1],
                'support': support[1],
                'profit': profit,
                'is_near_support': is_near_support,
                'volatility': round(float(self.volatility), 3)}

        if support[0] == 0 and support[1] == 0:
            self._logger_queue.put(["WARNING", f"  Stock {self.ticker}: Skipping, resistance and support not found"])
            info['state'] = "skip"
            self._q.put(info)
            self._stop_event.set()
            return
        elif profit == "Unknown":
            if is_near_support:
                self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Worth attention, but resistance not found"])
                info['state'] = 'worth attention no resistance'
            else:
                self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Not worth attention. Keeping an eye on this one."])
                info['state'] = 'watch'
        elif is_near_support and profit >= self._min_profit:
            self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Worth attention"])
            info['state'] = 'worth attention'
        else:
            self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Not worth attention. Keeping an eye on this one."])
            info['state'] = 'watch'

        self._q.put(info)

    def _show_chart(self, dformat="%d/%b/%Y %H:%M", candle_width=0.6/(24 * 15), show_levels=True):
        self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Showing chart"])

        webbrowser.get(self._chrome_path).open(self._url)

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

        try:
            t = str(self._df_for_chart.index[0])
        except Exception as e:
            print("\n[-] Something went wrong. Check logs for details")
            print("Try running with --prepost False  (It disables pre and post market data)")          # TODO
            self._logger_queue.put(["ERROR", f" Stock {self.ticker} - {e} while showing chart"])
            self._logger_queue.put(["ERROR", f" Stock {self.ticker} - {self._df_for_chart}"])
            self._logger_queue.put(["ERROR", f" Stock {self.ticker} - length: {len(self._df_for_chart)}"])

            return

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
        self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Started watching"])
        schedule.every(4).minutes.do(self.check_if_worth_attention)

        chart_process = Process(target=self._show_chart)

        while True:
            if self._stop_event.is_set():
                self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Got exit flag. Exiting."])

                if chart_process.is_alive():
                    self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Terminating chart process"])
                    chart_process.terminate()
                break

            if self._show_chart_event.is_set():
                self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Got flag, showing chart"])

                if chart_process.is_alive():
                    self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Chart is already shown"])
                else:
                    chart_process = Process(target=self._show_chart)
                    chart_process.start()

                self._show_chart_event.clear()

            if self._get_data_event.is_set():
                price = self.get_current_price()
                support, resistance = self.get_nearest_support_resistance(price)
                profit = (resistance[1] - price) / price
                self._additional_queue.put([round(price, 2), round(support[1], 2), round(resistance[1], 2), str(round(profit, 2)*100)+"%", round(float(self.volatility), 3)])

            schedule.run_pending()
            time.sleep(1)

    def run(self):
        self._find_levels(self._df)
        self._find_levels(self._df_for_chart)

        self._logger_queue.put(["INFO", f"  Stock {self.ticker} - levels: {self.levels}"])

        self.check_if_worth_attention()
        self.__watch()
