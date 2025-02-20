
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
from models.Mongo.AggTradeModel import AggTradeModel

import pandas as pd
import numpy as np

from models.nora_realtime import Busd

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')


class aggtradeProcessor():

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

    def __init__(self, symbol) -> None:
        self.symbol = symbol

        self.BUSD_TIMEFRAMES = [15, 60, 240, 1440]
        self.BUSD_MA_WINDOW = [300, 1200, 4800, 28800]
        self.MACD_TICKER = [3, 5, 60]
        self.maxLeng = 30000

        #[[timeframe, ma_window]]
        self.BUSD_MA_WINDOW_TIMEFRAMES = list(zip(self.BUSD_TIMEFRAMES, self.BUSD_MA_WINDOW))
        
        #MACD_TIMES = [[timeframe, ma_window, ticker]]
        self.MACD_TIMES = [[15, 300, 3], [60, 1200, 5], [240, 4800, 5], [60, 1200, 60], [240, 4800, 60], [1440, 28800, 60]] 

        self.columns = self.getColumns()
        self.busd = pd.DataFrame(columns=self.columns).set_index("timestamp", drop=False)
        self.macd = {}
        for ticker in self.MACD_TICKER :
            self.macd[ticker] = Macd(ticker, self.MACD_TIMES)

        self.currentTime = 0 #save clock time
        self.rawAggTradeModel = AggTradeModel('raw_data')
        self.saveDataBlock = []

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

        return columns    

    def getAggtradeData(self, startTime, stopTime):
        self.unstableTimePoint = int(startTime/1000)
        collNames = splitCollName(startTime, stopTime, self.symbol, 'agg_trades')
        returnData = []
        for collName in collNames:
            print(f"{self.symbol} Get Aggtrade data from {collName['startTime']} {datetime.fromtimestamp(collName['startTime']/1000, tz=VN_TZ)} to {collName['stopTime']} {datetime.fromtimestamp(collName['stopTime']/1000, tz=VN_TZ)}")
            data = self.rawAggTradeModel.setCollection(collName['collection']).collection.find({
                "s": self.symbol, 
                "T":{'$gte':collName['startTime'], '$lte':collName['stopTime']}
            })
            returnData += list(data)
        return returnData

    
    def getData(self, startTime, stopTime):
        '''
        Get AggTrade by start and stoptime form raw database.
        '''
        return self.getAggtradeData(startTime, stopTime)

    def processData(self, secondTime):
        '''
        Update macd to a row of self.busd and return that row
        '''
        returnData = False
        rowData = self.busd.loc[secondTime].to_dict()
        for ticker in self.MACD_TICKER:
            macd = self.macd[ticker].updateMacd(self.busd, secondTime)
            rowData.update(macd)
        self.saveDataBlock.append(Busd(**rowData))
        if(len(self.saveDataBlock) >= 200):
            returnData = self.saveDataBlock
            self.saveDataBlock = []
        return returnData
            



    def calBUSDBlock(self, data, isMacd=False):

        dff = pd.DataFrame(data).astype({'p':float, 'q':float})
        dff['timestamp'] = dff['T'].map(lambda x: int(x / 1000))
        dff['tran_time'] = dff['T']
        startTime = dff['timestamp'].min()
        endTime = dff['timestamp'].max()
        taker = dff[dff['m'] == False]
        maker = dff[dff['m']]

        taker = taker.groupby('timestamp').agg({'q': sum}).reset_index().set_index('timestamp')
        maker = maker.groupby('timestamp').agg({'q': sum}).reset_index().set_index('timestamp')

        timeIndex = range(startTime, endTime + 1)
        busd = pd.merge(taker, maker, on='timestamp', how='outer').rename(columns={'q_x':'BU', 'q_y':'SD'})
        busd = busd.reindex(timeIndex).fillna(0) #type: pd.DataFrame

        self.busd = pd.concat([self.busd.iloc[-self.maxLeng:][['BU','SD']], busd])
        
        
        for timeframe, ma_window in self.BUSD_MA_WINDOW_TIMEFRAMES:
            self.busd[f'BU_{timeframe}'] =  self.busd['BU'].rolling(timeframe * 60).sum()
            self.busd[f'BU_{timeframe}_{ma_window}'] =  self.busd[f'BU_{timeframe}'].rolling(ma_window).mean()
            self.busd[f'SD_{timeframe}'] =  self.busd['SD'].rolling(timeframe * 60).sum()
            self.busd[f'SD_{timeframe}_{ma_window}'] =  self.busd[f'SD_{timeframe}'].rolling(ma_window).mean()

        self.busd['symbol'] = self.symbol
        if(isMacd):
            for ticker in self.MACD_TICKER:
                macd = self.macd[ticker].calMacdBlock(self.busd)
                self.busd = self.busd.merge(macd, left_index=True, right_index=True, suffixes=('', ''), how='left').pad()
    
        self.busd['timestamp'] = self.busd.index

        
        return timeIndex
        
    
                
class Macd():

    def __init__(self, ticker, macd_times) -> None:
        self.ticker = ticker
        self.macdTimes = []
        for timeframe, windown, ticker in macd_times:
            if(ticker == self.ticker):
                self.macdTimes.append([timeframe, windown]) #[(timeFrame, window)]

        self.macdCol = self.getMacdColumns()
        self.macd = pd.DataFrame(columns=self.macdCol).set_index("timestamp_macd", drop=False)
        

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

        return columns


    def setMacdData(self, macdDf):
        self.macd = pd.concat([self.macd, macdDf])

    def getMacdData(self, timestamp):
        if(timestamp in self.macd.index):      
            periodRowData = self.macd.loc[timestamp].to_dict()
        else:
            periodRowData = {}
        return periodRowData


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
        
        self.setMacdData(df_macd)

        return df_macd


    def updateMacd(self, busd:pd.DataFrame, secondTime):

        # startTime = dt.now().timestamp()
        macdTimeStamp = int(secondTime//(self.ticker*60)*(self.ticker*60))
        macdBusdBlock = busd.loc[macdTimeStamp:secondTime]
        
        newData = {}

        for timeframe, ma_window in self.macdTimes:
            newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'] = macdBusdBlock[f'BU_{timeframe}_{ma_window}'].sum()
            newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'] = macdBusdBlock[f'SD_{timeframe}_{ma_window}'].sum()
        
        #calculate MACD for last row
        if(len(self.macd) > 4):

            periodTime = macdTimeStamp - (self.ticker*60) 
            periodRowData = self.getMacdData(periodTime)
            p2Data = self.getMacdData(macdTimeStamp - 2*(self.ticker*60))
            p3Data = self.getMacdData(macdTimeStamp - 3*(self.ticker*60))
            p4Data = self.getMacdData(macdTimeStamp - 4*(self.ticker*60))

            for timeframe, ma_window in self.macdTimes:
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST'] = ema(get(periodRowData, f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST', None), newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'], 12)
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = ema(get(periodRowData, f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW', None), newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'], 26)
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'] = newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST'] - newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW']
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = ema(get(periodRowData, f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH', None), newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'], 9)
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'] - newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']

                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST'] = ema(get(periodRowData, f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST', None), newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'], 12)
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = ema(get(periodRowData, f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW', None), newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'], 26)
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'] = newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST'] - newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW']
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = ema(get(periodRowData, f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH', None), newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'], 9)
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'] - newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']

                newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}'] = newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'] - newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM']
                newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_FAST'] = ema(get(periodRowData, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_FAST', None), newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}'], 12)
                newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = ema(get(periodRowData, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SLOW', None), newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}'], 26)
                newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'] = newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_FAST'] - newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SLOW']
                newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = ema(get(periodRowData, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH', None), newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'], 9)
                newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACD'] - newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']
                newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p1'] = get(periodRowData, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
                newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p2'] = get(p2Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
                newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p3'] = get(p3Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
                newData[f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p4'] = get(p4Data, f'BUSD_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
            
            newDataSeri = pd.Series(newData, index=self.macdCol)
            
            self.macd.loc[macdTimeStamp] = newDataSeri
            self.macd = self.macd.iloc[-10:]
            
        # print(f"macd ticker {self.ticker} update time {(dt.now().timestamp() - startTime) * 1000} ms")
        return newDataSeri.to_dict()

    

    


    


    


                
    


    
