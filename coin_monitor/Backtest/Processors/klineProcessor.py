from math import floor
from threading import Thread
from time import sleep, time
import orjson
from datetime import datetime, timedelta
import requests
from helper.Indicator import rsi, ema, wma, rma, sma
from helper.Defaults import *
from helper.Data import *
from pymongo import ASCENDING, DESCENDING
from models.Mongo.CandleModel import Candle_Model
from models.Mongo.KlineModel import KlineModel


import pandas as pd
import numpy as np

VN_TZ = tz.gettz("Asia/Ho_Chi_Minh")


class klineProcessor:

    def __init__(self, symbol) -> None:
        self.symbol = symbol
        self.rawKlineModel = KlineModel("raw_data")
        self.unstableTimePoint = 0
        self.frames = ["1m", "3m", "15m", "1h", "4h", "1d", "1w"]
        self.indicators = [
            ["all", "rsi", "close", 14],
            ["1w", "wma", "rsi_close_14", 45],
            ["1d", "wma", "rsi_close_14", 45],
        ]
        self.frameInstances = {}
        for fr in self.frames:
            self.frameInstances[fr] = Frame(self, fr)

    def getKlineData(self, startTime, stopTime):
        collNames = splitCollName(startTime, stopTime, self.symbol, "kline_1m")
        returnData = []
        for collName in collNames:
            print(
                f"{self.symbol} Get price data from {collName['startTime']} {datetime.fromtimestamp(collName['startTime']/1000, tz=VN_TZ)} to {collName['stopTime']} {datetime.fromtimestamp(collName['stopTime']/1000, tz=VN_TZ)}"
            )
            datas = (
                self.rawKlineModel.setCollection(collName["collection"])
                .collection.find(
                    {
                        "s": self.symbol,
                        "E": {
                            "$gte": collName["startTime"],
                            "$lte": collName["stopTime"],
                        },
                    }
                )
                .sort("E", ASCENDING)
            )

            for dt in datas:
                closeTime = Number(dt["k"]["T"])
                returnData.append(
                    {
                        "symbol": self.symbol,
                        "open_time": Number(dt["k"]["t"]),
                        "close_time": closeTime,
                        "open": Number(dt["k"]["o"]),
                        "high": Number(dt["k"]["h"]),
                        "low": Number(dt["k"]["l"]),
                        "close": Number(dt["k"]["c"]),
                        "volume": Number(dt["k"]["v"]),
                        "quote": Number(dt["k"]["q"]),
                        "trades": Number(dt["k"]["n"]),
                        "bu_base": Number(dt["k"]["V"]),
                        "bu_quote": Number(dt["k"]["Q"]),
                        "sd_base": Number(dt["k"]["v"]) - Number(dt["k"]["V"]),
                        "sd_quote": Number(dt["k"]["q"]) - Number(dt["k"]["Q"]),
                        "is_close": Number(dt["k"]["x"]),
                        "event_time": (
                            Number(dt["E"])
                            if closeTime > Number(dt["E"])
                            else closeTime
                        ),
                    }
                )

        pandasData = pd.DataFrame(returnData)
        if len(pandasData) == 0:
            return pandasData
        pandasData["timestamp"] = pandasData["event_time"] // 1000
        pandasData = pandasData.groupby("timestamp").last().reset_index()
        return pandasData.to_dict(orient="records")

    def cleanData(self):
        for fr in self.frameInstances:
            frameInstance = self.frameInstances[fr]  # type: Frame
            frameInstance.cleanData()

    def getStartTime(self):
        return self.frameInstances["1m"].getStartTime()

    def processData(self, data):
        for fr in self.frameInstances:

            frameInstance = self.frameInstances[fr]  # type: Frame
            fullData = frameInstance.updateKline(data)

            frameInstance.insertData(fullData)


class klineProcessor1m:

    def __init__(self, symbol, sourceDb, destDb) -> None:
        self.symbol = symbol
        self.rawKlineModel = KlineModel(sourceDb, f"{self.symbol}_kline_1m")
        self.unstableTimePoint = 0
        self.frames = [
            "1m",
            # "3m",
            # "5m",
            # "15m",
            # "30m",
            # "1h",
            # "2h",
            "4h",
            "8h",
            "12h" "1d",
            "1w",
        ]
        self.frames = ["1m", "1d", "4h", "1w"]
        self.indicators = [
            ["all", "rsi", "close", 14, "rsi"],
            ["all", "tr", "", "", "tr"],
            ["all", "atr", "tr", 14, "atr"],
            ["all", "ema", "close", 3, "price_ema3"],
            # ["5m", "wma", "rsi", 45],
            # ["5m", "ema", "close", 9, "price_ema9"],
            # ["5m", "wma", "close", 45, "price_wma45"],
            # ["5m", "net", "", ["price_ema9", "price_wma45"], "net_ema9_wma45"],
            # ["5m", "ema", "rsi", 9, "rsi_ema9"],
            # ["5m", "wma", "rsi", 45, "rsi_wma45"],
            # ["15m", "wma", "rsi", 45],
            # ["15m", "ema", "close", 9, "price_ema9"],
            # ["15m", "wma", "close", 45, "price_wma45"],
            # ["15m", "net", "", ["price_ema9", "price_wma45"], "net_ema9_wma45"],
            # ["15m", "ema", "rsi", 9, "rsi_ema9"],
            # ["15m", "wma", "rsi", 45, "rsi_wma45"],
            # ["30m", "wma", "rsi", 45],
            # ["30m", "ema", "close", 9, "price_ema9"],
            # ["30m", "wma", "close", 45, "price_wma45"],
            # ["30m", "net", "", ["price_ema9", "price_wma45"], "net_ema9_wma45"],
            # ["30m", "ema", "rsi", 9, "rsi_ema9"],
            # ["30m", "wma", "rsi", 45, "rsi_wma45"],
            # ["1h", "wma", "rsi", 45],
            # ["1h", "ema", "close", 9, "price_ema9"],
            # ["1h", "wma", "close", 45, "price_wma45"],
            # ["1h", "net", "", ["price_ema9", "price_wma45"], "net_ema9_wma45"],
            # ["1h", "ema", "rsi", 9, "rsi_ema9"],
            # ["1h", "wma", "rsi", 45, "rsi_wma45"],
            # ["1h", "ema", "close", 100, "price_ema100"],
            # ["2h", "wma", "rsi", 45],
            # ['2h', 'macdh', 'wma_45_rsi', [12,26,9], 'macdh_wma_45_rsi'],
            # ["4h", "wma", "rsi", 45],
            # ["4h", "ema", "close", 9, "price_ema9"],
            # ["4h", "wma", "close", 45, "price_wma45"],
            # ["4h", "net", "", ["price_ema9", "price_wma45"], "net_ema9_wma45"],
            # ["4h", "ema", "rsi", 9, "rsi_ema9"],
            # ["4h", "ema", "close", 15, "price_ema15"],
            # ["4h", "ema", "close", 17, "price_ema17"],
            # ["4h", "wma", "rsi", 45, "rsi_wma45"],
            # ["4h", "ema", "close", 100, "price_ema100"],
            # ["4h", "rbb", "", 5, ""],
            # [
            #     "4h",
            #     "keltner",
            #     ["price_ema15", "atr"],
            #     [15, 14, 0.5],
            #     ["KUP15", "KLO15"],
            # ],
            # [
            #     "4h",
            #     "keltner",
            #     ["price_ema17", "atr"],
            #     [17, 14, 0.5],
            #     ["KUP17", "KLO17"],
            # ],
            # ["1d", "ema", "rsi", 9, "rsi_ema9"],
            ["1d", "wma", "rsi", 45, "rsi_wma45"],
            # ['4h', 'macdh', 'wma_45_rsi', [12,26,9], 'macdh_wma_45_rsi'],
            # ["8h", "wma", "rsi", 45],
            # ['8h', 'macdh', 'wma_45_rsi', [12,26,9], 'macdh_wma_45_rsi'],
            ["1d", "wma", "rsi", 45],
            # ["1d", "ema", "close", 9, "price_ema9"],
            ["1d", "ema", "close", 15, "price_ema15"],
            # ["1d", "ema", "close", 17, "price_ema17"],
            # ["1d", "wma", "close", 45, "price_wma45"],
            # ["1d", "net", "", ["price_ema9", "price_wma45"], "net_ema9_wma45"],
            # ["1d", "ema", "rsi", 9, "rsi_ema9"],
            # ["1d", "wma", "rsi", 45, "rsi_wma45"],
            # ['1d', 'macdh', 'wma_45_rsi', [12,26,9], 'macdh_wma_45_rsi'],
            # ["1d", "rbb", "", 5, ""],
            ["1d", "ema", "close", 30, "price_ema30"],
            ["1d", "ema", "close", 45, "price_ema45"],
            [
                "1d",
                "keltner",
                ["price_ema15", "atr"],
                [15, 14, 1],
                ["KUP15", "KLO15"],
            ],
            [
                "1d",
                "keltner",
                ["price_ema30", "atr"],
                [30, 14, 1],
                ["KUP30", "KLO30"],
            ],
            [
                "1d",
                "keltner",
                ["price_ema45", "atr"],
                [45, 14, 1],
                ["KUP45", "KLO45"],
            ],
            # [
            #     "1d",
            #     "keltner",
            #     ["price_ema17", "atr"],
            #     [17, 14, 0.5],
            #     ["KUP17", "KLO17"],
            # ],
            #
            ["1w", "wma", "rsi", 45],
            # ["1w", "ema", "close", 9, "price_ema9"],
            ["1w", "ema", "close", 7, "price_ema7"],
            [
                "1w",
                "keltner",
                ["price_ema7", "atr"],
                [7, 14, 1],
                ["KUP7", "KLO7"],
            ],
            # ["1w", "wma", "close", 45, "price_wma45"],
            # ["1w", "net", "", ["price_ema9", "price_wma45"], "net_ema9_wma45"],
            # ["1w", "ema", "rsi", 9, "rsi_ema9"],
            ["1w", "wma", "rsi", 45, "rsi_wma45"],
            # ['1w', 'macdh', 'wma_45_rsi', [12,26,9], 'macdh_wma_45_rsi'],
        ]
        self.frameInstances = {}
        for fr in self.frames:
            self.frameInstances[fr] = Frame(self, fr, destDb)

    def getKlineData(self, startTime, stopTime):

        print(
            f"{self.symbol} Get kline 1m on DB from {startTime} {datetime.fromtimestamp(startTime/1000, tz=VN_TZ)} to {stopTime} {datetime.fromtimestamp(stopTime/1000, tz=VN_TZ)}"
        )

        datas = list(
            self.rawKlineModel.collection.find(
                {"close_time": {"$gte": startTime, "$lte": stopTime}}
            ).sort("close_time", ASCENDING)
        )

        pandasData = pd.DataFrame(datas)
        if len(pandasData) == 0:
            return []
        pandasData = pandasData.drop(["_id"], axis=1)
        pandasData["timestamp"] = pandasData["event_time"] // 1000
        pandasData = pandasData.groupby("timestamp").last().reset_index()
        return pandasData.to_dict(orient="records")

    def cleanData(self):
        for fr in self.frameInstances:
            frameInstance = self.frameInstances[fr]  # type: Frame
            frameInstance.cleanData()

    def getStartTime(self):
        return self.frameInstances["1m"].getStartTime()

    def processData(self, data):
        for fr in self.frameInstances:

            frameInstance = self.frameInstances[fr]  # type: Frame
            fullData = frameInstance.updateKline(data)

            frameInstance.insertData(fullData)

    def createIndex(self):
        for fr in self.frameInstances:
            frameInstance = self.frameInstances[fr]  # type: Frame
            frameInstance.createIndex()


class Frame:
    def __init__(self, processor, frame, destDb="backtest_data") -> None:
        self.count = 0
        self.intervals = {
            "1m": 60000,
            "3m": 3 * 60000,
            "5m": 5 * 60000,
            "15m": 15 * 60000,
            "30m": 30 * 60000,
            "1h": 60 * 60000,
            "2h": 2 * 60 * 60000,
            "4h": 4 * 60 * 60000,
            "8h": 8 * 60 * 60000,
            "1d": 24 * 60 * 60000,
            "1w": 7 * 24 * 60 * 60000,
        }
        self.symbol = processor.symbol
        self.frame = frame
        self.indicators = []
        for params in processor.indicators:
            fr = params[0]
            if fr == self.frame or fr == "all":
                self.indicators.append(params[1:])

        self.interval = self.intervals[frame]
        self.candleData = None
        self.maxLength = 500

        self.currentVolume = 0
        self.currentQuote = 0
        self.currentBuBase = 0
        self.currentBuQuote = 0
        self.currentTrades = 0

        self.collection = f"candle_{self.frame}"
        self.model = Candle_Model(destDb, self.collection)
        self.mongoBlock = []

    def cleanData(self):
        print(f"{self.symbol} clean kline frame {self.frame}")
        self.model.collection.delete_many({"symbol": self.symbol})

    def insertData(self, data):
        if (
            len(self.mongoBlock) > 0
            and self.mongoBlock[-1]["timestamp"] == data["timestamp"]
        ):
            self.mongoBlock[-1] = data
        else:
            self.mongoBlock.append(data)

        if len(self.mongoBlock) >= 100:
            self.model.collection.insert_many(
                self.mongoBlock[: len(self.mongoBlock) - 1]
            )
            self.mongoBlock = self.mongoBlock[-1:]

    def createIndex(self):
        self.model.collection.create_index(
            [
                (Candle_Model.symbol, ASCENDING),
                (Candle_Model.timestamp, ASCENDING),
            ]
        )
        self.model.collection.create_index(
            [
                (Candle_Model.symbol, ASCENDING),
                (Candle_Model.is_close, ASCENDING),
                (Candle_Model.close_time, ASCENDING),
            ]
        )

    def getStartTime(self):
        lastData = (
            self.model.collection.find({"symbol": self.symbol})
            .sort("timestamp", DESCENDING)
            .limit(1)
        )

        if lastData.count() > 0:
            return int((lastData[0]["timestamp"] + 1) * 1000)
        else:
            return None

    def getHistoryDataOnline(self, startTime, endTime=None):
        if endTime is None:
            endTime = int(datetime.now().timestamp() * 1000)
        data = []

        while True:
            try:
                queryTime = int(datetime.now().timestamp() * 1000)
                print(
                    f"Get history data from {datetime.fromtimestamp(startTime/1000, tz=VN_TZ)} to {datetime.fromtimestamp(endTime/1000, tz=VN_TZ)}"
                )
                block = requests.get(
                    f"https://fapi.binance.com/fapi/v1/klines?symbol={self.symbol}&startTime={startTime}&interval={self.frame}&limit=1000"
                )
                block = block.json()
                if isset(block, "code"):
                    break
                if len(block) == 0:
                    break
                for dt in block:

                    closeTime = Number(dt[6])
                    data.append(
                        {
                            "symbol": self.symbol,
                            "open_time": Number(dt[0]),
                            "close_time": closeTime,
                            "open": Number(dt[1]),
                            "high": Number(dt[2]),
                            "low": Number(dt[3]),
                            "close": Number(dt[4]),
                            "volume": Number(dt[5]),
                            "quote": Number(dt[7]),
                            "trades": Number(dt[8]),
                            "bu_base": Number(dt[9]),
                            "bu_quote": Number(dt[10]),
                            "sd_base": Number(dt[5]) - Number(dt[9]),
                            "sd_quote": Number(dt[7]) - Number(dt[10]),
                            "is_close": 1,
                            "event_time": (
                                Number(dt[6])
                                if Number(dt[6]) < queryTime
                                else queryTime
                            ),
                            "timestamp": (
                                Number(dt[6]) / 1000
                                if Number(dt[6]) < queryTime
                                else queryTime / 1000
                            ),
                        }
                    )
                    if closeTime > endTime:
                        break
                startTime = Number(data[-1]["event_time"]) + 1
                if startTime >= endTime:
                    break

            except Exception as e:
                break
        return data

    def createFirstData(self, endTime):
        firstData = self.getHistoryDataOnline(
            endTime - 500 * self.interval, endTime
        )
        for data in firstData:
            self.updateKline(data)

    def updateKline(self, data):
        # print(data)
        openTime1m = data["open_time"]

        # create first data for first time
        if self.candleData is None:
            self.candleData = []
            self.createFirstData(openTime1m)

        if self.frame == "1w":
            startOfDay = openTime1m // 86400000 * 86400000
            eventDate = datetime.fromtimestamp(startOfDay / 1000)
            startOfweek = eventDate - timedelta(days=eventDate.weekday())
            openTime = int(startOfweek.timestamp() * 1000)
        else:
            openTime = int(openTime1m / self.interval) * self.interval

        closeTime = openTime + self.interval - 1

        if len(self.candleData) == 0:
            newData = data.copy()
            newData["open_time"] = openTime
            newData["close_time"] = closeTime
            self.candleData.append(newData)
        else:
            lastCancle = self.candleData[-1]
            if openTime > lastCancle["close_time"]:
                newData = data.copy()
                newData["open_time"] = openTime
                newData["close_time"] = closeTime
                newData["is_close"] = (
                    1
                    if (
                        data["is_close"] == 1
                        and data["close_time"] == closeTime
                    )
                    else 0
                )
                self.candleData.append(newData)
                if len(self.candleData) > 100:
                    self.candleData.pop(0)
                self.currentVolume = 0
                self.currentQuote = 0
                self.currentTrades = 0
                self.currentBuBase = 0
                self.currentBuQuote = 0
            else:
                if self.frame == "1m":
                    lastCancle.update(data)
                else:
                    open = lastCancle["open"]
                    low = (
                        data["low"]
                        if data["low"] < lastCancle["low"]
                        else lastCancle["low"]
                    )
                    high = (
                        data["high"]
                        if data["high"] > lastCancle["high"]
                        else lastCancle["high"]
                    )
                    volume = self.currentVolume + data["volume"]
                    quote = self.currentQuote + data["quote"]
                    trades = self.currentTrades + data["trades"]
                    buBase = self.currentBuBase + data["bu_base"]
                    buQuote = self.currentBuQuote + data["bu_quote"]
                    sdBase = volume - buBase
                    sdQuote = quote - buQuote

                    lastCancle["timestamp"] = data["timestamp"]
                    lastCancle["event_time"] = data["event_time"]
                    lastCancle["open"] = open
                    lastCancle["low"] = low
                    lastCancle["high"] = high
                    lastCancle["close"] = data["close"]
                    lastCancle["open_time"] = openTime
                    lastCancle["close_time"] = closeTime
                    lastCancle["volume"] = volume
                    lastCancle["quote"] = quote
                    lastCancle["trades"] = trades
                    lastCancle["bu_base"] = buBase
                    lastCancle["bu_quote"] = buQuote
                    lastCancle["sd_base"] = sdBase
                    lastCancle["sd_quote"] = sdQuote
                    lastCancle["is_close"] = 0

                    if data["is_close"]:
                        if data["close_time"] == lastCancle["close_time"]:
                            lastCancle["is_close"] = 1
                        self.currentVolume = volume
                        self.currentQuote = quote
                        self.currentTrades = trades
                        self.currentBuBase = buBase
                        self.currentBuQuote = buQuote

        self.updateIndicator()

        return self.candleData[-1].copy()

    def updateIndicator(self):
        if len(self.candleData) < 2:
            return
        if len(self.indicators) == 0:
            return

        for param in self.indicators:
            indicator = param[0]
            obj = param[1]
            N = param[2]
            name = get(param, 3, None)
            result = self.calIndicator(self.candleData, indicator, obj, N, name)
            self.candleData[-1].update(result)

    def calIndicator(self, candleData, indicator, obj, N, name):

        if indicator == "ema":
            if name is None:
                name = f"{indicator}_{N}_{obj}"
            p1Data = self.candleData[-2]
            lastData = self.candleData[-1]
            periodValue = get(p1Data, name, None)
            objValue = get(lastData, obj, None)
            historyValue = None
            if periodValue is None:
                historyValue = [
                    get(candle, obj, None) for candle in self.candleData[-N:]
                ]
            return {name: ema(periodValue, objValue, N, historyValue)}
        elif indicator == "rsi":
            if name is None:
                name = f"{indicator}_{N}_{obj}"
            p1Data = self.candleData[-2]
            lastData = self.candleData[-1]
            avgUName = f"avgU_{N}_{obj}"
            avgDName = f"avgD_{N}_{obj}"
            periodValue = get(p1Data, obj, None)
            periodAvgU = get(p1Data, avgUName, None)
            periodAvgD = get(p1Data, avgDName, None)
            objValue = get(lastData, obj, None)
            historyValue = None
            if periodAvgU is None or periodAvgD is None:
                historyValue = [
                    get(candle, obj, None)
                    for candle in self.candleData[-N - 1 :]
                ]
            result = rsi(
                periodValue, periodAvgU, periodAvgD, objValue, N, historyValue
            )
            return {
                name: result["rsi"],
                avgUName: result["avgU"],
                avgDName: result["avgD"],
            }
        elif indicator == "wma":
            if name is None:
                name = f"{indicator}_{N}_{obj}"
            historyValue = [
                get(candle, obj, None) for candle in self.candleData[-N:]
            ]
            return {name: wma(N, historyValue)}
        elif indicator == "macd":
            fast, slow = N
            if name is None:
                name = f"{indicator}_{fast}_{slow}_{obj}"
            emaSlowName = f"ema_{slow}_{obj}"
            emaFastName = f"ema_{fast}_{obj}"
            slow = self.calIndicator(candleData, "ema", obj, slow, emaSlowName)[
                emaSlowName
            ]
            fast = self.calIndicator(candleData, "ema", obj, fast, emaFastName)[
                emaFastName
            ]
            if slow is not None and fast is not None:
                macd = fast - slow
            else:
                macd = None
            return {name: macd, emaSlowName: slow, emaFastName: fast}
        elif indicator == "macdh":

            lastData = self.candleData[-1]
            fast, slow, smooth = N
            if name is None:
                name = f"{indicator}_{fast}_{slow}_{smooth}_{obj}"
            macdName = f"macd_{fast}_{slow}_{obj}"
            smoothName = f"ema_{smooth}_{macdName}"

            macdResult = self.calIndicator(
                candleData, "macd", obj, [fast, slow], macdName
            )
            lastData[macdName] = macdResult[macdName]
            smooth = self.calIndicator(
                candleData, "ema", macdName, smooth, smoothName
            )[smoothName]
            if macdResult[macdName] is not None and smooth is not None:
                macdh = macdResult[macdName] - smooth
            else:
                macdh = None
            return {**macdResult, smoothName: smooth, name: macdh}

        elif indicator == "net":
            number_1, number_2 = N
            if name is None:
                name = f"{indicator}_{number_1}_{number_2}"
            lastData = self.candleData[-1]
            if (
                lastData is not None
                and number_1 in lastData
                and number_2 in lastData
                and None not in [lastData[number_1], lastData[number_2]]
            ):
                net = lastData[number_1] - lastData[number_2]
            else:
                net = None
            return {name: net}

        elif indicator == "tr":
            if name is None:
                name = f"{indicator}_{obj}"
            if len(self.candleData) < 2:
                return {name: None}
            pCandle = self.candleData[-2]
            lastData = self.candleData[-1]
            tr = max(
                [
                    lastData["high"] - lastData["low"],
                    abs(lastData["high"] - pCandle["close"]),
                    abs(lastData["low"] - pCandle["close"]),
                ]
            )
            return {name: tr}
        elif indicator == "atr":
            if name is None:
                name = f"{indicator}_{N}"
            prevData = self.candleData[-2]
            atr = self.calIndicator(candleData, "ema", obj, N, name)[name]
            # print(name, atr)
            return {
                name: atr,
                f"p{name}": (
                    (atr / prevData["close"]) * 100
                    if atr is not None and prevData["close"] != 0
                    else None
                ),
                f"2p{name}": (
                    2 * (atr / prevData["close"]) * 100
                    if atr is not None and prevData["close"] != 0
                    else None
                ),
                f"3p{name}": (
                    3 * (atr / prevData["close"]) * 100
                    if atr is not None and prevData["close"] != 0
                    else None
                ),
                f"4p{name}": (
                    4 * (atr / prevData["close"]) * 100
                    if atr is not None and prevData["close"] != 0
                    else None
                ),
            }
        elif indicator == "rbb":  # Range Breakout Band
            name_up = f"dcup{N}"
            name_lo = f"dclo{N}"
            name_net = f"net_dc{N}"
            if len(self.candleData) < N:
                return {name_up: None, name_lo: None, name_net: None}
            highest = max(
                [get(candle, "high", None) for candle in self.candleData[-N:]]
            )
            lowest = min(
                [get(candle, "low", None) for candle in self.candleData[-N:]]
            )
            return {
                name_up: highest,
                name_lo: lowest,
                name_net: highest - lowest,
            }
        elif indicator == "keltner":
            if name is None:
                name_up = "KUP15"
                name_lo = "KLO15"
            else:
                name_up, name_lo = name

            N1, N2, factor = N
            lastData: dict = self.candleData[-1]

            param1, param2 = obj
            ema_val1 = lastData.get(param1, None)
            atr_val1 = lastData.get(param2, None)
            rData = {}
            rData[name_up] = (
                ema_val1 + factor * atr_val1
                if None not in [ema_val1, atr_val1]
                else None
            )
            rData[name_lo] = (
                ema_val1 - factor * atr_val1
                if None not in [ema_val1, atr_val1]
                else None
            )
            # print(rData)
            return rData
