
from math import floor
from threading import Thread
from time import sleep, time
import orjson
from datetime import datetime as dt
from Backtest.Processors.BusdProcessor import BusdProcessor, Frame
from helper.Redis import Redis
from helper.Defaults import *
from helper.Indicator import *
from helper.Data import *
from pymongo import ASCENDING
from models.Mongo.KlineModel import KlineModel

import pandas as pd
import numpy as np

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')


class BusdProcessor_1m(BusdProcessor):

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

    def __init__(self, symbol, srcDb, MACD_TIMES, FORCE_CAL) -> None:
        
        self.symbol = symbol
        self.srcDb = srcDb
        self.MACD_TIMES = MACD_TIMES 
        self.FORCE_CAL = FORCE_CAL #define data need to be calculate at Frame
        self.initial()

    def initial(self):
        
        self.BUSD_TIMEFRAMES = []
        self.BUSD_MA_WINDOW = []
        self.MACD_TICKER = []
        
        for timeframe, ma, ticker in self.MACD_TIMES:
            if(timeframe not in self.BUSD_TIMEFRAMES): self.BUSD_TIMEFRAMES.append(timeframe)
            if(ma not in self.BUSD_MA_WINDOW): self.BUSD_MA_WINDOW.append(ma)
            if(ticker not in self.MACD_TICKER): self.MACD_TICKER.append(ticker)

        self.maxLeng = max(self.BUSD_TIMEFRAMES) + max(self.BUSD_MA_WINDOW)//60 + 10

        self.busd = None
        self.macd = {}
        for ticker in self.MACD_TICKER :
            self.macd[ticker] = Frame(ticker, self.MACD_TIMES, self.FORCE_CAL)

        self.currentTime = 0 #save clock time
        self.rawKlineModel = KlineModel(self.srcDb, f'{self.symbol}_kline_1m')
        self.saveDataBlock = []
        self.unstableTimePoint = 0


    
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
        data = self.getKlineData(startTime, stopTime)
        if(len(data) == 0): return []
        dff = pd.DataFrame(data)
        busd = dff[['bu_base', 'sd_base', 'close', 'timestamp']].copy().rename(columns={'bu_base': 'BU', 'sd_base':'SD'}).set_index('timestamp')
        return busd
            

    def calBUSDBlock(self, busd, isMacd=False):
        if(len(busd) == 0): return []
    
        timeIndex = busd.index.to_list()
        
        if(self.busd is None):
            self.busd = busd
        else:
            self.busd = pd.concat([self.busd.iloc[-self.maxLeng:][['BU','SD','close']], busd])
        
        for timeframe in self.BUSD_TIMEFRAMES:

            if(self.FORCE_CAL['BUSD']):
                self.busd[f'BU_{timeframe}'] =  self.busd['BU'].rolling(timeframe).sum()
                self.busd[f'SD_{timeframe}'] =  self.busd['SD'].rolling(timeframe).sum()
                for ma_window in self.BUSD_MA_WINDOW:
                    self.busd[f'BU_{timeframe}_{ma_window}'] =  self.busd[f'BU_{timeframe}'].rolling(ma_window//60).mean()
                    self.busd[f'SD_{timeframe}_{ma_window}'] =  self.busd[f'SD_{timeframe}'].rolling(ma_window//60).mean()

            if(self.FORCE_CAL['Price']):        
                self.busd[f'Price_{timeframe}'] =  self.busd['close'].rolling(timeframe).sum()
                for ma_window in self.BUSD_MA_WINDOW:
                    self.busd[f'Price_{timeframe}_{ma_window}'] =  self.busd[f'Price_{timeframe}'].rolling(ma_window//60).mean()

        self.busd['symbol'] = self.symbol

        if(isMacd):
            for ticker in self.MACD_TICKER:
                macd = self.macd[ticker].calMacdBlock(self.busd)
                self.busd = self.busd.merge(macd, left_index=True, right_index=True, suffixes=('', ''), how='left').pad()
    
        self.busd['timestamp'] = self.busd.index

        
        return timeIndex
        
    
                


    


    


    


                
    


    
