
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

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')


class BusdProcessor():

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
        #MACD_TIMES = [[timeframe, ma_window, ticker]]
        self.MACD_TIMES = [
            [15, 300, 3], 
            [60, 1200, 3], 
            [60, 1200, 5], 
            [240, 4800, 5], 
            [60, 1200, 60], 
            [240, 4800, 60], 
            [1440, 28800, 60]
        ] 
        self.FORCE_CAL = {'BUSD':True, 'Price':False} #define data need to be calculate at Frame
        self.initial()
        

    def initial(self):
        self.BUSD_TIMEFRAMES = []
        self.BUSD_MA_WINDOW = []
        self.MACD_TICKER = []
        
        for timeframe, ma, ticker in self.MACD_TIMES:
            if(timeframe not in self.BUSD_TIMEFRAMES): self.BUSD_TIMEFRAMES.append(timeframe)
            if(ma not in self.BUSD_MA_WINDOW): self.BUSD_MA_WINDOW.append(ma)
            if(ticker not in self.MACD_TICKER): self.MACD_TICKER.append(ticker)

        self.maxLeng = max(self.BUSD_TIMEFRAMES) * 60 + max(self.BUSD_MA_WINDOW) + 10

        self.busd = None
        self.macd = {}
        for ticker in self.MACD_TICKER :
            self.macd[ticker] = Frame(ticker, self.MACD_TIMES, self.FORCE_CAL)

        self.currentTime = 0 #save clock time
        self.rawAggTradeModel = AggTradeModel('raw_data')
        self.saveDataBlock = []
        self.unstableTimePoint = 0

    def getAggtradeData(self, startTime, stopTime):
        
        collNames = splitCollName(startTime, stopTime, self.symbol, 'agg_trades')
        returnData = []
        for collName in collNames:
            if(collName['model'] is not None):
                print(f"{self.symbol} Get Aggtrade data from {collName['startTime']} {datetime.fromtimestamp(collName['startTime']/1000, tz=VN_TZ)} to {collName['stopTime']} {datetime.fromtimestamp(collName['stopTime']/1000, tz=VN_TZ)}")
                data = collName['model'].setCollection(collName['collection']).collection.find({
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
        rowData = self.busd.loc[secondTime].to_dict()
        for ticker in self.MACD_TICKER:
            macd = self.macd[ticker].updateMacd(self.busd, secondTime)
            rowData.update(macd)
        rowData['stable_time'] = secondTime - self.unstableTimePoint
        return rowData
            



    def calBUSDBlock(self, data, isMacd=False):
        if(len(data) == 0): return []
        dff = pd.DataFrame(data).astype({'p':float, 'q':float})
        dff['timestamp'] = dff['T'].map(lambda x: int(x / 1000))
        dff['tran_time'] = dff['T']
        startTime = dff['timestamp'].min()
        if(self.busd is not None and len(self.busd) > 0):
            startTime = self.busd.index[-1] + 1
        endTime = dff['timestamp'].max()
        taker = dff[dff['m'] == False]
        maker = dff[dff['m']]

        taker = taker.groupby('timestamp').agg({'q': sum}).reset_index().set_index('timestamp')
        maker = maker.groupby('timestamp').agg({'q': sum}).reset_index().set_index('timestamp')

        timeIndex = range(startTime, endTime + 1)
        busd = pd.merge(taker, maker, on='timestamp', how='outer').rename(columns={'q_x':'BU', 'q_y':'SD'})
        busd = busd.reindex(timeIndex).fillna(0) #type: pd.DataFrame
        if(self.busd is None):
            self.busd = busd
        else:
            self.busd = pd.concat([self.busd.iloc[-self.maxLeng:][['BU','SD']], busd])
        # self.busd = self.busd.drop_duplicates(subset=['timestamp'], keep='last')

        for timeframe in self.BUSD_TIMEFRAMES:
            self.busd[f'BU_{timeframe}'] =  self.busd['BU'].rolling(timeframe * 60).sum()
            self.busd[f'SD_{timeframe}'] =  self.busd['SD'].rolling(timeframe * 60).sum()
            for ma_window in self.BUSD_MA_WINDOW:
                self.busd[f'BU_{timeframe}_{ma_window}'] =  self.busd[f'BU_{timeframe}'].rolling(ma_window).mean()
                self.busd[f'SD_{timeframe}_{ma_window}'] =  self.busd[f'SD_{timeframe}'].rolling(ma_window).mean()

        self.busd['symbol'] = self.symbol
        if(isMacd):
            for ticker in self.MACD_TICKER:
                macd = self.macd[ticker].calMacdBlock(self.busd)
                self.busd = self.busd.merge(macd, left_index=True, right_index=True, suffixes=('', ''), how='left').pad()
    
        self.busd['timestamp'] = self.busd.index

        return timeIndex
        
    
                
class Frame():

    def __init__(self, ticker, macd_times, forceCal) -> None:
        self.ticker = ticker
        self.macdTimes = []
        self.forceCal = forceCal # Define data require to calculate

        self.BUSD_TIMEFRAMES = []
        self.BUSD_MA_WINDOW = []
        self.MACD_TICKER = []
        
        for timeframe, ma, ticker in macd_times:
            if(ticker == self.ticker):
                if(timeframe not in self.BUSD_TIMEFRAMES): self.BUSD_TIMEFRAMES.append(timeframe)
                if(ma not in self.BUSD_MA_WINDOW): self.BUSD_MA_WINDOW.append(ma)
                if(ticker not in self.MACD_TICKER): self.MACD_TICKER.append(ticker)
                self.macdTimes.append([timeframe, ma]) #[(timeFrame, ma)]

        self.macd = []
        

    def calMacdBlock(self, df_busd:pd.DataFrame):
        '''
        Calculate MACD values
        '''
        df_busd['timestamp_macd'] = df_busd.index.map(lambda x: int(x//(self.ticker*60)*(self.ticker*60)))
        agg = {}
        rename = {}
        for timeframe, ma_window in self.macdTimes:
            if(self.forceCal['BUSD']):
                agg[f'BU_{timeframe}_{ma_window}'] = 'sum'
                agg[f'SD_{timeframe}_{ma_window}'] = 'sum'
                rename[f'BU_{timeframe}_{ma_window}'] = f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'
                rename[f'SD_{timeframe}_{ma_window}'] = f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'
            if(self.forceCal['Price']):
                agg[f'Price_{timeframe}_{ma_window}'] = 'sum'
                rename[f'Price_{timeframe}_{ma_window}'] = f'Price_{timeframe}_{ma_window}_{self.ticker}_SUM'
        
        df_macd = df_busd.groupby('timestamp_macd').agg(agg).reset_index().set_index('timestamp_macd').rename(columns=rename)
        df_macd['timestamp_macd'] = df_macd.index
        del df_busd['timestamp_macd']

        for timeframe, ma_window in self.macdTimes:
            if(self.forceCal['Price']):
                df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_FAST'] = df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_SUM'].ewm(span=12, adjust=False, min_periods=12).mean()
                df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_SUM'].ewm(span=26, adjust=False, min_periods=26).mean()
                df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACD'] = df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_FAST'] - df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_SLOW']
                df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACD'].ewm(span=9, adjust=False, min_periods=9).mean()
                df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACD'] - df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']
                
                df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh_p1'] = df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(1)
                df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh_p2'] = df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(2)
                df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh_p3'] = df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(3)
                df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh_p4'] = df_macd[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(4)
           
            if(self.forceCal['BUSD']):
                df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'].ewm(span=12, adjust=False, min_periods=12).mean()
                df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'].ewm(span=26, adjust=False, min_periods=26).mean()
                df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST'] - df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW']
                df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'].ewm(span=9, adjust=False, min_periods=9).mean()
                df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'] - df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']
                
                df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh_p1'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(1)
                df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh_p2'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(2)
                df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh_p3'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(3)
                df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh_p4'] = df_macd[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(4)

                df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'].ewm(span=12, adjust=False, min_periods=12).mean()
                df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'].ewm(span=26, adjust=False, min_periods=26).mean()
                df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST'] - df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW']
                df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'].ewm(span=9, adjust=False, min_periods=9).mean()
                df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'] - df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']
                
                df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p1'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(1)
                df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p2'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(2)
                df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p3'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(3)
                df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p4'] = df_macd[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh'].shift(4)
                
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
            
        
        self.macd = df_macd.to_dict(orient='records')

        return df_macd


    def updateMacd(self, busd:pd.DataFrame, secondTime):

        # startTime = dt.now().timestamp()
        macdTimeStamp = int(secondTime//(self.ticker*60)*(self.ticker*60))
        macdBusdBlock = busd.loc[macdTimeStamp:secondTime]
        
        newData = {'timestamp_macd': macdTimeStamp}

        for timeframe, ma_window in self.macdTimes:
            if(self.forceCal['BUSD']):
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'] = macdBusdBlock[f'BU_{timeframe}_{ma_window}'].sum()
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'] = macdBusdBlock[f'SD_{timeframe}_{ma_window}'].sum()
            if(self.forceCal['Price']):
                newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_SUM'] = macdBusdBlock[f'Price_{timeframe}_{ma_window}'].sum()
        
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
        
        for timeframe, ma_window in self.macdTimes:
            if(self.forceCal['Price']):
                newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_FAST'] = ema(get(p1Data, f'Price_{timeframe}_{ma_window}_{self.ticker}_FAST', None), newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_SUM'], 12)
                newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = ema(get(p1Data, f'Price_{timeframe}_{ma_window}_{self.ticker}_SLOW', None), newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_SUM'], 26)
                newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACD'] = newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_FAST'] - newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_SLOW']
                newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = ema(get(p1Data, f'Price_{timeframe}_{ma_window}_{self.ticker}_SMOOTH', None), newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACD'], 9)
                newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACD'] - newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']
                newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh_p1'] = get(p1Data, f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
                newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh_p2'] = get(p2Data, f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
                newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh_p3'] = get(p3Data, f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
                newData[f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh_p4'] = get(p4Data, f'Price_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
            if(self.forceCal['BUSD']):
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST'] = ema(get(p1Data, f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST', None), newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'], 12)
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = ema(get(p1Data, f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW', None), newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SUM'], 26)
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'] = newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_FAST'] - newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SLOW']
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = ema(get(p1Data, f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH', None), newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'], 9)
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACD'] - newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh_p1'] = get(p1Data, f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh_p2'] = get(p2Data, f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh_p3'] = get(p3Data, f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
                newData[f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh_p4'] = get(p4Data, f'BU_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)

                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST'] = ema(get(p1Data, f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST', None), newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'], 12)
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW'] = ema(get(p1Data, f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW', None), newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SUM'], 26)
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'] = newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_FAST'] - newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SLOW']
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH'] = ema(get(p1Data, f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH', None), newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'], 9)
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh'] = newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACD'] - newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_SMOOTH']
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p1'] = get(p1Data, f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p2'] = get(p2Data, f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p3'] = get(p3Data, f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)
                newData[f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh_p4'] = get(p4Data, f'SD_{timeframe}_{ma_window}_{self.ticker}_MACDh', None)

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
            
        
        self.macd[-1] = newData
            
        # print(f"macd ticker {self.ticker} update time {(dt.now().timestamp() - startTime) * 1000} ms")
        return newData


    

    

    


    


    


                
    


    
