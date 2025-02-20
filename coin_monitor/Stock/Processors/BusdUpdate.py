
from math import floor
from threading import Thread
from time import sleep, time
import orjson
from datetime import datetime as dt
from Backtest.Processors.BusdProcessor import BusdProcessor
from helper.Redis import Redis
from helper.Defaults import *
from helper.Indicator import *
from helper.Data import *
from pymongo import ASCENDING
from models.Mongo.AggTradeModel import AggTradeModel

import pandas as pd
import numpy as np

from models.Mongo.BusdModel import BusdModel
from models.Mongo.CandleModel import Candle_Model

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')


class BusdUpdate(BusdProcessor):

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
    def __init__(self, symbol, database) -> None:
        super().__init__(symbol)    
        self.busdModel = BusdModel(database)
        self.klineModel = Candle_Model(database)
        self.symbol = symbol
        #MACD_TIMES = [[timeframe, ma_window, ticker]]
        self.MACD_TIMES = [
            [60, 1200, 3], 
            [1440, 28800, 60]
        ] 
        self.FORCE_CAL = {
            'BUSD': False,
            'Price': True
        }

        self.initial()

    def getAggtradeData(self, startTime, stopTime):
        print(f"{self.symbol} Get BUSD data from {startTime} {datetime.fromtimestamp(startTime/1000, tz=VN_TZ)} to {stopTime} {datetime.fromtimestamp(stopTime/1000, tz=VN_TZ)}")
        busd = list(self.busdModel.collection.find({'symbol': self.symbol, 'timestamp':{'$gte': startTime/1000, '$lte': stopTime/1000}}, {
            '_id': False,
            'symbol':1,
            'timestamp':1,
            'BU':1,
            'SD':1
        }))
        if(len(busd) == 0): return []
        df = pd.DataFrame(busd).set_index('timestamp', drop=False)

        prices = list(self.klineModel.collection.find({'symbol': self.symbol, 'timestamp':{'$gte': startTime/1000, '$lte': stopTime/1000}}, {
            '_id': False,
            'timestamp':1,
            'close': 1,
        }))

        if(len(prices) == 0): return []
        pricedf = pd.DataFrame(prices).set_index('timestamp', drop=True)
        df = df.join(pricedf, how='left')

        return df


    def calBUSDBlock(self, busd:pd.DataFrame, isMacd=False):
        
        if(len(busd) == 0): return []
        timeIndex = busd['timestamp'].to_list()
        if(self.busd is None):
            self.busd = busd
        else:
            self.busd = pd.concat([self.busd.iloc[-self.maxLeng:][['close']], busd])
        self.busd['close'] = self.busd['close'].pad()
        # self.busd = self.busd.drop_duplicates(subset=['timestamp'], keep='last')

       

        
        for timeframe in self.BUSD_TIMEFRAMES:
            # self.busd[f'BU_{timeframe}'] =  self.busd['BU'].rolling(timeframe * 60).sum()
            # self.busd[f'SD_{timeframe}'] =  self.busd['SD'].rolling(timeframe * 60).sum()
            self.busd[f'Price_{timeframe}'] =  self.busd['close'].rolling(timeframe * 60).sum()
            for ma_window in self.BUSD_MA_WINDOW:
                # self.busd[f'BU_{timeframe}_{ma_window}'] =  self.busd[f'BU_{timeframe}'].rolling(ma_window).mean()
                # self.busd[f'SD_{timeframe}_{ma_window}'] =  self.busd[f'SD_{timeframe}'].rolling(ma_window).mean()
                self.busd[f'Price_{timeframe}_{ma_window}'] =  self.busd[f'Price_{timeframe}'].rolling(ma_window).mean()

        self.busd['symbol'] = self.symbol
        if(isMacd):
            for ticker in self.MACD_TICKER:
                macd = self.macd[ticker].calMacdBlock(self.busd)
                self.busd = self.busd.merge(macd, left_index=True, right_index=True, suffixes=('', ''), how='left').pad()
    
        self.busd['timestamp'] = self.busd.index

        return timeIndex
        
    
                


    

    


    


    


                
    


    
