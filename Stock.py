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
import json
import gc
from utilities import Group

class Stock(Process):
    def __init__(self, ticker, queue, logger_queue, additional_queue):
        Process.__init__(self)

        # Config
        self._chrome_path = "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s"
        self._url = "https://www.tradingview.com/chart/?symbol=" + ticker
        self._min_profit = 2        # Percent %

        # Queues
        self._q = queue
        self._additional_queue = additional_queue
        self._logger_queue = logger_queue

        # Events
        self._stop_event = Event()
        self._get_data_event = Event()
        self._show_chart_event = Event()
        self._show_chart_event_without_window = Event()

        # Variables used by class
        self._levels = []
        self.__ticker = ticker
        self.groups = []

        # Data for finding levels (support and resistance)
        try:
            try:
                self._df = pd.read_pickle("data/data.pkl")[ticker]
            except KeyError:
                self._df = pd.read_pickle("data/data.pkl")

            self._df['Date'] = pd.to_datetime(self._df.index)
            self._df['Date'] = self._df['Date'].apply(mpl_dates.date2num)
            self._df = self._df.loc[:, ['Date', 'Open', 'High', 'Low', 'Close']]

            # Data in 5 min intervals for analysis
            try:
                self._df5 = pd.read_pickle("data/data_for_chart.pkl")[ticker]
            except KeyError:
                self._df5 = pd.read_pickle("data/data_for_chart.pkl")

            self._df5['Date'] = pd.to_datetime(self._df5.index)
            self._df5['Date'] = self._df5['Date'].apply(mpl_dates.date2num)
            self._df5 = self._df5.loc[:, ['Date', 'Open', 'High', 'Low', 'Close']]
        except KeyError:
            self._stop_event.set()
            return

        # Data for chart
        self._df_for_chart = self._df5.last("1d")

        # Volatility
        returns = np.log(self._df["Close"].last("10d") / self._df["Close"].last("10d").shift(-1))
        self.__volatility = (np.std(returns) * 10 ** 0.5)

        gc.collect()

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

    def show_chart(self, window):
        self._show_chart_event.set()
        if not window:
            self._show_chart_event_without_window.set()

    def get_data(self):
        self._get_data_event.set()

    def _is_support(self, i, df):
        support = df['Low'][i] < df['Low'][i - 1] < df['Low'][i - 2] and \
                  df['Low'][i] < df['Low'][i + 1] < df['Low'][i + 2]
        return support

    def _is_resistance(self, i, df):
        resistance = df['High'][i] > df['High'][i - 1] > df['High'][i - 2] and \
                     df['High'][i] > df['Close'][i + 1] > df['Close'][i + 2]
        return resistance

    def group(self, l):
        grouped = False

        for i in range(len(self.groups)):
            if abs(l - self.groups[i].items[0]) / self.groups[i].items[0] < 0.035:
                self.groups[i].items.append(l)
                self.groups[i].average = sum(self.groups[i].items) / len(self.groups[i].items)
                grouped = True
                break

        if not grouped:
            self.groups.append(Group(l, [l]))

    def iterlines(self, x):
        # a little bit modified function from https://github.com/dysonance/Trendy
        window = 30
        x = np.array(x)
        n = len(x)

        sigs = np.zeros(n, dtype=float)

        i = window
        while i != n:
            if x[i] > max(x[i - window:i]):
                sigs[i] = 1
            elif x[i] < min(x[i - window:i]):
                sigs[i] = -1
            i += 1

        xmin = np.where(sigs == -1.0)[0]
        xmax = np.where(sigs == 1.0)[0]
        ymin = x[xmin]
        ymax = x[xmax]

        result = []
        result.extend(ymin)
        result.extend(ymax)

        return result

    def _find_levels(self, df):
        counter_max = 0
        current_range_max = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        counter_min = 0
        current_range_min = [100000000, 100000000, 100000000, 100000000, 100000000, 100000000, 100000000, 100000000,
                             100000000, 100000000]

        for i in df.index:
            current_max = max(current_range_max, default=0)
            current_min = min(current_range_min, default=100000000)

            value = round(df["High"][i], 2)

            current_range_max = current_range_max[1:]
            current_range_min = current_range_min[1:]

            current_range_max.append(value)
            current_range_min.append(value)

            if current_max == max(current_range_max, default=0):
                counter_max += 1
            else:
                counter_max = 0
            if counter_max == 7 and current_max != 0:
                self.group(round(current_max, 2))

            if current_min == min(current_range_min, default=100000000):
                counter_min += 1
            else:
                counter_min = 0

            if counter_min == 7:
                self.group(round(current_min, 2))

        # Another way to find support and resistance
        for i in range(2, df.shape[0] - 2):
            if self._is_support(i, df):
                l = df['Low'][i]
                self.group(round(l, 2))
            elif self._is_resistance(i, df):
                l = df['High'][i]
                self.group(round(l, 2))

        # Another way - a little bit modified function from https://github.com/dysonance/Trendy
        results = self.iterlines(df["Close"])
        for i in results:
            self.group(i)

    def filter_levels(self):
        current_price = self.get_current_price()
        levels = []

        for group in self.groups:
            levels.append([len(group.items), group.average])

        self._logger_queue.put(["DEBUG", f" Stocks {self.ticker}: Found {len(levels)} levels"])

        filtered_levels = list(filter(lambda x: x[0] > 20, levels))
        levels_len = len([abs(i[1] - current_price) / current_price < 0.3 for i in filtered_levels])

        if levels_len > 12:
            filtered_levels = list(filter(lambda x: x[0] > 30, levels))
            levels_len = len([abs(i[1] - current_price) / current_price < 0.3 for i in filtered_levels])

        if levels_len < 6:
            filtered_levels = list(filter(lambda x: x[0] > 15, levels))
            levels_len = len([abs(i[1] - current_price) / current_price < 0.3 for i in levels])
            if levels_len < 6:
                filtered_levels = levels

        self._logger_queue.put(["DEBUG", f" Stock {self.ticker}: After filtering {len(filtered_levels)} levels left"])
        self._logger_queue.put(["DEBUG", f" Stock {self.ticker}: {filtered_levels}"])

        self._levels.extend(filtered_levels)

    def _get_sma(self, prices, rate):
        return prices.rolling(rate).mean()

    def _get_bollinger_bands(self, prices, rate=20):
        sma = self._get_sma(prices, rate)
        std = prices.rolling(rate).std()
        bollinger_up = sma + std * 2
        bollinger_down = sma - std * 2
        return bollinger_up, bollinger_down

    def get_current_price(self):
        ticker = yfinance.Ticker(self.ticker)
        flag = True

        while flag:
            try:
                data = ticker.history(period='1d')
                flag = False
            except json.decoder.JSONDecodeError:
                print("[-] Failed download current price")
                flag = True

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

        bollinger_up, bollinger_down = self._get_bollinger_bands(self._df5["Close"])

        current_price = self.get_current_price()

        (support, resistance) = self.get_nearest_support_resistance(current_price)

        self._logger_queue.put(["DEBUG", f"  Stock {self.ticker} - Price: {current_price}"])
        self._logger_queue.put(["INFO", f"  Stock {self.ticker} - Nearest resistance: {resistance[1]}"])
        self._logger_queue.put(["INFO", f"  Stock {self.ticker} - Nearest support: {support[1]}"])

        profit = (resistance[1] - current_price) / current_price
        is_near_support = (current_price - support[1]) * 100 / (resistance[1] - support[1]) < 30

        self._logger_queue.put(["DEBUG", f"  Stock {self.ticker} - Estimated profit: {round(profit, 2) * 100}"])
        self._logger_queue.put(["DEBUG", f"  Stock {self.ticker} - Is near support: {is_near_support}"])
        self._logger_queue.put(["INFO", f"  Stock {self.ticker} - Volatility: {self.volatility}"])
        self._logger_queue.put(["INFO", f"  Stock {self.ticker} - Bollinger up: {bollinger_up[-1]}"])
        self._logger_queue.put(["INFO", f"  Stock {self.ticker} - Bollinger down: {bollinger_down[-1]}"])

        if resistance[1] == 10000000:
            resistance[1] = "Not found"
            profit = "Unknown"
        else:
            profit = round(profit, 2) * 100

        info = {'ticker': self.ticker,
                'state': "",
                'price': current_price,
                'resistance': resistance[1],
                'support': support[1],
                'profit': profit,
                'is_near_support': is_near_support,
                'volatility': str(int(round(float(self.volatility) / current_price, 2) * 100)) + " %",
                'strategy': "support & resistance"}

        if (bollinger_up[-1] - bollinger_down[-1]) / current_price < 0.04:
            self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Bollinger bands too narrow, watching..."])
            info['state'] = "watch"
            self._q.put(info)
            return
        elif profit == "Unknown":
            if is_near_support:
                self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Worth attention, but resistance not found"])
                info['state'] = 'worth attention no resistance'
            else:
                self._logger_queue.put(
                    ["INFO", f"  Stock {self.ticker}: Not worth attention. Keeping an eye on this one."])
                info['state'] = 'watch'
        elif is_near_support and profit >= self._min_profit:
            self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Worth attention"])
            info['state'] = 'worth attention'
        else:
            self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Not worth attention. Keeping an eye on this one."])
            info['state'] = 'watch'

        if abs(current_price - bollinger_down[-1]) * 100 / (bollinger_up[-1] - bollinger_down[-1]) <= 30:
            self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Near lower bollinger band"])
            if info['state'] == "worth attention":
                info['strategy'] += " + bollinger bands"
            elif round((bollinger_up[-1] - current_price) / current_price, 2) * 100 > 8:
                info['state'] = "worth attention"
                info['strategy'] = "bollinger bands"
                info['profit'] = round((bollinger_up[-1] - current_price) / current_price, 2) * 100

        self._q.put(info)

    def _show_chart(self, dformat="%d/%b/%Y %H:%M", candle_width=0.6 / (24 * 15), show_levels=True):
        self._logger_queue.put(["INFO", f"  Stock {self.ticker}: Showing chart"])

        webbrowser.get(self._chrome_path).open(self._url)

        if not self._show_chart_event_without_window.is_set():
            bollinger_up, bollinger_down = self._get_bollinger_bands(self._df5["Close"])

            fig, ax = plt.subplots()

            candlestick_ohlc(ax, self._df_for_chart.values, width=candle_width,
                             colorup='green', colordown='red', alpha=0.8)

            date_format = mpl_dates.DateFormatter(dformat)
            date_format.set_tzinfo(timezone('America/New_york'))
            ax.xaxis.set_major_formatter(date_format)
            ax.xaxis.set_major_locator(mpl_dates.MinuteLocator((0, 30)))

            ax.plot(bollinger_up.last("1d"), label="Bollinger Up", c="blue")
            ax.plot(bollinger_down.last("1d"), label="Bollinger Down", c="blue")

            fig.autofmt_xdate()
            fig.tight_layout()
            fig.set_size_inches(10.5, 6.5)

            try:
                t = str(self._df_for_chart.index[0])
            except Exception as e:
                print("\n[-] Something went wrong. Check logs for details")
                self._logger_queue.put(["ERROR", f" Stock {self.ticker} - {e} while showing chart"])
                self._logger_queue.put(["ERROR", f" Stock {self.ticker} - {self._df_for_chart}"])
                self._logger_queue.put(["ERROR", f" Stock {self.ticker} - length: {len(self._df_for_chart)}"])

                return

            fig.suptitle(self.ticker + " " + t, fontsize=16, y=0.98)
            fig.subplots_adjust(top=0.8, left=0.08)
            current_price = self.get_current_price()

            if show_levels:
                for level in self._levels:
                    if abs(level[1] - current_price) / current_price < 0.3:
                        if level[1] > current_price:
                            color = "red"
                        else:
                            color = "green"
                        plt.hlines(level[1], xmin=self._df_for_chart['Date'][0],
                                   xmax=max(self._df_for_chart['Date']), colors=color)
                        plt.text(self._df_for_chart['Date'][0], level[1] + 0.01,
                                 str(round(level[1], 2)) + f" ({level[0]})", ha="left", va='center')

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
                self._additional_queue.put(
                    [round(price, 2), round(support[1], 2), round(resistance[1], 2), str(round(profit, 2) * 100) + "%",
                     round(float(self.volatility), 3)])

            schedule.run_pending()
            time.sleep(1)

    def run(self):
        if self._stop_event.is_set():
            info = {'ticker': self.ticker,
                    'state': "skip"}
            self._q.put(info)
            self._logger_queue.put(["ERROR", f" {self.ticker}: Shutting down. Got stop event on startup"])
            return

        self._find_levels(self._df)
        del self._df
        gc.collect()

        self._find_levels(self._df5)

        self.filter_levels()

        self._logger_queue.put(["INFO", f"  Stock {self.ticker} - levels: {self.levels}"])

        self.check_if_worth_attention()

        self.__watch()
