
from math import floor
from threading import Thread
from time import sleep, time
import orjson
from datetime import datetime as dt
from helper.Redis import Redis
from helper.Defaults import *
from helper.Indicator import *
from helper.Data import *
from pymongo import ASCENDING
from models.Mongo.KlineModel import KlineModel

import pandas as pd
import numpy as np

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')


class kline1mBUSDProcessor():

    indicatorData = None
    '''
    An array of order book data
    max leng: 500
    ```
    [
        {
            symbol: symbol
            tran_time: Transaction time
            event_time: Event Time
            ready_time: Time data is ready on redis
            timestamp: time by second
            ....
        },
        ....
    ]
    ```
    '''
    
    periodEventTime = None #for check package loss

    def __init__(self, symbol, srcDb) -> None:
        self.symbol = symbol

        self.BUSD_TIMEFRAMES = [15, 60, 240, 1440]
        self.BUSD_MA_WINDOW = [300, 1200, 4800, 28800]
        self.MACD_TICKER = [3, 5, 60]
        self.maxLeng = 1440

        #[[timeframe, ma_window]]
        self.BUSD_MA_WINDOW_TIMEFRAMES = list(zip(self.BUSD_TIMEFRAMES, self.BUSD_MA_WINDOW))
        
        #MACD_TIMES = [[timeframe, ma_window, ticker]]
        self.MACD_TIMES = [[15, 300, 3], [60, 1200, 3], [60, 1200, 5], [240, 4800, 5], [60, 1200, 60], [240, 4800, 60], [1440, 28800, 60]] 

        self.columns = self.getColumns()
        self.busd = pd.DataFrame(columns=self.columns).set_index("timestamp", drop=False)
        self.macd = {}
        for ticker in self.MACD_TICKER :
            self.macd[ticker] = Macd(ticker, self.MACD_TIMES)

        self.currentTime = 0 #save clock time
        self.rawKlineModel = KlineModel(srcDb, f'{self.symbol}_kline_1m')
        self.saveDataBlock = []
        self.unstableTimePoint = 0

    def getColumns(self):
        columns = [
            'symbol',
            'tran_time', 
            'event_time', 
            'ready_time', 
            'stable_time', #stable time of data in second
            'timestamp', 
            'BU',
            'SD'
        ]
        for timeFrame, window in self.BUSD_MA_WINDOW_TIMEFRAMES:
            columns.append(f"BU_{timeFrame}")
            columns.append(f"SD_{timeFrame}")
            columns.append(f"BU_{timeFrame}_{window}")
            columns.append(f"SD_{timeFrame}_{window}")

        for timeFrame, window, ticker in self.MACD_TIMES:
            
            columns.append(f"BU_{timeFrame}_{window}_{ticker}_SUM")
            columns.append(f"BU_{timeFrame}_{window}_{ticker}_FAST")
            columns.append(f"BU_{timeFrame}_{window}_{ticker}_SLOW")
            columns.append(f"BU_{timeFrame}_{window}_{ticker}_SMOOTH")
            columns.append(f"BU_{timeFrame}_{window}_{ticker}_MACD")
            columns.append(f"BU_{timeFrame}_{window}_{ticker}_MACDh")

            columns.append(f"SD_{timeFrame}_{window}_{ticker}_SUM")
            columns.append(f"SD_{timeFrame}_{window}_{ticker}_FAST")
            columns.append(f"SD_{timeFrame}_{window}_{ticker}_SLOW")
            columns.append(f"SD_{timeFrame}_{window}_{ticker}_SMOOTH")
            columns.append(f"SD_{timeFrame}_{window}_{ticker}_MACD")
            columns.append(f"SD_{timeFrame}_{window}_{ticker}_MACDh")

            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_FAST")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_SLOW")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_SMOOTH")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACD")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACDh")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACDh_p1")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACDh_p2")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACDh_p3")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACDh_p4")

            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACD_p1")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACD_p2")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACD_p3")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACD_p4")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACD_p5")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACD_p6")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACD_p7")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACD_p8")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACD_p9")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACD_p10")
            columns.append(f"BUSD_{timeFrame}_{window}_{ticker}_MACD_p11")

        return columns    

    def getKlineData(self, startTime, stopTime):

        print(f"{self.symbol} Get kline 1m on DB from {startTime} {datetime.fromtimestamp(startTime/1000, tz=VN_TZ)} to {stopTime} {datetime.fromtimestamp(stopTime/1000, tz=VN_TZ)}")
        
        datas = list(self.rawKlineModel.collection.find({
            'close_time': {'$gte': startTime, '$lte': stopTime}
        }).sort('close_time', ASCENDING))

        pandasData = pd.DataFrame(datas)
        if(len(pandasData) == 0): return []
        pandasData = pandasData.drop(['_id'], axis=1)
        pandasData['timestamp'] = pandasData['event_time']//1000
        pandasData = pandasData.groupby('timestamp').last().reset_index()
        return pandasData.to_dict(orient='records')

    
    def getData(self, startTime, stopTime):
        '''
        Get AggTrade by start and stoptime form raw database.
        '''
        return self.getKlineData(startTime, stopTime)

    def processData(self, timeStamp):
        '''
        Update macd to a row of self.busd and return that row
        '''
        returnData = False
        rowData = self.busd.loc[timeStamp].to_dict()
        for ticker in self.MACD_TICKER:
            macd = self.macd[ticker].updateMacd(self.busd, timeStamp)
            rowData.update(macd)
        rowData['stable_time'] = timeStamp - self.unstableTimePoint
        self.saveDataBlock.append(rowData)
        if(len(self.saveDataBlock) >= 200):
            returnData = self.saveDataBlock
            self.saveDataBlock = []
        return returnData
            



    def calBUSDBlock(self, data, isMacd=False):
        if(len(data) == 0): return []
        dff = pd.DataFrame(data)
        busd = dff[['bu_base', 'sd_base', 'timestamp']].copy().rename(columns={'bu_base': 'BU', 'sd_base':'SD'}).set_index('timestamp')

        self.busd = pd.concat([self.busd.iloc[-self.maxLeng:][['BU','SD']], busd])
        
        
        for timeframe, ma_window in self.BUSD_MA_WINDOW_TIMEFRAMES:
            self.busd[f'BU_{timeframe}'] =  self.busd['BU'].rolling(timeframe).sum()
            self.busd[f'BU_{timeframe}_{ma_window}'] =  self.busd[f'BU_{timeframe}'].rolling(ma_window//60).mean()
            self.busd[f'SD_{timeframe}'] =  self.busd['SD'].rolling(timeframe).sum()
            self.busd[f'SD_{timeframe}_{ma_window}'] =  self.busd[f'SD_{timeframe}'].rolling(ma_window//60).mean()

        self.busd['symbol'] = self.symbol
        if(isMacd):
            for ticker in self.MACD_TICKER:
                macd = self.macd[ticker].calMacdBlock(self.busd)
                self.busd = self.busd.merge(macd, left_index=True, right_index=True, suffixes=('', ''), how='left').pad()
    
        self.busd['timestamp'] = self.busd.index

        
        return self.busd['timestamp'].to_list()
        
    
                
class Macd():

    def __init__(self, ticker, macd_times) -> None:
        self.ticker = ticker
        self.macdTimes = []
        for timeframe, windown, ticker in macd_times:
            if(ticker == self.ticker):
                self.macdTimes.append([timeframe, windown]) #[(timeFrame, window)]

        self.macdCol = self.getMacdColumns()
        self.macd = []
        

    def getMacdColumns(self):
        columns = ['timestamp_macd']
        for timeFrame, window in self.macdTimes:
            
            columns.append(f"BU_{timeFrame}_{window}_{self.ticker}_SUM")
            columns.append(f"BU_{timeFrame}_{window}_{self.ticker}_FAST")
            columns.append(f"BU_{timeFrame}_{window}_{self.ticker}_SLOW")
            columns.append(f"BU_{timeFrame}_{window}_{self.ticker}_SMOOTH")
            columns.append(f"BU_{timeFrame}_{window}_{self.ticker}_MACD")
            columns.append(f"BU_{timeFrame}_{window}_{self.ticker}_MACDh")

            columns.append(f"SD_{timeFrame}_{window}_{self.ticker}_SUM")
            columns.append(f"SD_{timeFrame}_{window}_{self.ticker}_FAST")
            columns.append(f"SD_{timeFrame}_{window}_{self.ticker}_SLOW")
            columns.append(f"SD_{timeFrame}_{window}_{self.ticker}_SMOOTH")
            columns.append(f"SD_{timeFrame}_{window}_{self.ticker}_MACD")
            columns.append(f"SD_{timeFrame}_{window}_{self.ticker}_MACDh")

            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_FAST")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_SLOW")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_SMOOTH")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACD")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACDh")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACDh_p1")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACDh_p2")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACDh_p3")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACDh_p4")

            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACD_p1")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACD_p2")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACD_p3")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACD_p4")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACD_p5")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACD_p6")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACD_p7")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACD_p8")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACD_p9")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACD_p10")
            columns.append(f"BUSD_{timeFrame}_{window}_{self.ticker}_MACD_p11")

        return columns


    # def setMacdData(self, macdDf):
    #     self.macd = pd.concat([self.macd, macdDf])

    # def getMacdData(self, timestamp):
    #     if(timestamp in self.macd.index):      
    #         p1Data = self.macd.loc[timestamp].to_dict()
    #     else:
    #         p1Data = {}
    #     return p1Data


    def calMacdBlock(self, df_busd:pd.DataFrame):
        '''
        Calculate MACD values
        '''
        df_busd['timestamp_macd'] = df_busd.index.map(lambda x: int(x//(self.ticker*60)*(self.ticker*60)))
        agg = {}
        rename = {}
        for timeframe, ma_window in self.macdTimes:
            agg[f'BU_{timeframe}_{ma_window}'] = 'sum'
            agg[f'SD_{timeframe}_{ma_window}'] = 'sum'
            rename[f'BU_{timeframe}_{ma_window}'] = f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'
            rename[f'SD_{timeframe}_{ma_window}'] = f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'
        
        df_macd = df_busd.groupby('timestamp_macd').agg(agg).reset_index().set_index('timestamp_macd').rename(columns=rename)
        df_macd['timestamp_macd'] = df_macd.index
        del df_busd['timestamp_macd']

        for timeframe, ma_window in self.macdTimes:
           
            df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'].ewm(span=12, adjust=False, min_periods=12).mean()
            df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'].ewm(span=26, adjust=False, min_periods=26).mean()
            df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST'] - df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW']
            df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'].ewm(span=9, adjust=False, min_periods=9).mean()
            df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'] - df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']

            df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'].ewm(span=12, adjust=False, min_periods=12).mean()
            df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'].ewm(span=26, adjust=False, min_periods=26).mean()
            df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST'] - df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW']
            df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'].ewm(span=9, adjust=False, min_periods=9).mean()
            df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'] - df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']
            
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'] - df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM']
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_FAST'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}'].ewm(span=12, adjust=False, min_periods=12).mean()
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}'].ewm(span=26, adjust=False, min_periods=26).mean()
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_FAST'] - df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SLOW']
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'].ewm(span=9, adjust=False, min_periods=9).mean()
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'] - df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p1'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(1)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p2'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(2)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p3'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(3)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p4'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(4)

            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p1'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'].shift(1)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p2'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'].shift(2)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p3'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'].shift(3)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p4'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'].shift(4)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p5'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'].shift(5)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p6'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'].shift(6)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p7'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'].shift(7)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p8'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'].shift(8)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p9'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'].shift(9)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p10'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'].shift(10)
            df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p11'] = df_macd[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'].shift(11)
        
        self.macd = df_macd.to_dict(orient='records')

        return df_macd


    def updateMacd(self, busd:pd.DataFrame, secondTime):

        # startTime = dt.now().timestamp()
        macdTimeStamp = int(secondTime//(self.ticker*60)*(self.ticker*60))
        macdBusdBlock = busd.loc[macdTimeStamp:secondTime]
        
        newData = {'timestamp_macd': macdTimeStamp}

        for timeframe, ma_window in self.macdTimes:
            newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'] = macdBusdBlock[f'BU_{timeframe}_{ma_window}'].sum()
            newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'] = macdBusdBlock[f'SD_{timeframe}_{ma_window}'].sum()
        
        #calculate MACD for last row
        
        if(len(self.macd) == 0):
            self.macd.append(newData)
        else:
            p0Data = self.macd[-1]
            if(macdTimeStamp > p0Data['timestamp_macd']):
                self.macd.append(newData)
                if(len(self.macd) > 10): self.macd.pop(0)
                
        p1Data = get(self.macd, -2, {})
        p2Data = get(self.macd, -3, {})
        p3Data = get(self.macd, -4, {})
        p4Data = get(self.macd, -5, {})
        p5Data = get(self.macd, -6, {})
        p6Data = get(self.macd, -7, {})
        p7Data = get(self.macd, -8, {})
        p8Data = get(self.macd, -9, {})
        p9Data = get(self.macd, -10, {})
        p10Data = get(self.macd, -11, {})
        p11Data = get(self.macd, -12, {})

        for timeframe, ma_window in self.macdTimes:
            newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST'] = ema(get(p1Data, f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST', None), newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'], 12)
            newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = ema(get(p1Data, f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW', None), newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'], 26)
            newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'] = newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST'] - newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW']
            newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = ema(get(p1Data, f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH', None), newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'], 9)
            newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'] - newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']

            newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST'] = ema(get(p1Data, f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST', None), newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'], 12)
            newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = ema(get(p1Data, f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW', None), newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'], 26)
            newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'] = newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST'] - newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW']
            newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = ema(get(p1Data, f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH', None), newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'], 9)
            newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'] - newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']

            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}'] = newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'] - newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM']
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_FAST'] = ema(get(p1Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_FAST', None), newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}'], 12)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = ema(get(p1Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SLOW', None), newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}'], 26)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'] = newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_FAST'] - newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SLOW']
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = ema(get(p1Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH', None), newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'], 9)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'] - newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p1'] = get(p1Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p2'] = get(p2Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p3'] = get(p3Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p4'] = get(p4Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)

            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p1'] = get(p1Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p2'] = get(p2Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p3'] = get(p3Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p4'] = get(p4Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p5'] = get(p5Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p6'] = get(p6Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p7'] = get(p7Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p8'] = get(p8Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p9'] = get(p9Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p10'] = get(p10Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD', None)
            newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD_p11'] = get(p11Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD', None)
        
        self.macd[-1] = newData
            
        # print(f"macd ticker {self.ticker} update time {(dt.now().timestamp() - startTime) * 1000} ms")
        return newData

    

    


    


    


                
    


    
