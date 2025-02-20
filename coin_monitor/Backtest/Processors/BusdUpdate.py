
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
    def __init__(self, symbol, database, MACD_TIMES, FORCE_CAL) -> None:
        super().__init__(symbol, MACD_TIMES, FORCE_CAL)    
        self.busdModel = BusdModel(database)
        self.klineModel = Candle_Model(database)
        self.symbol = symbol
        #MACD_TIMES = [[timeframe, ma_window, ticker]]
        self.MACD_TIMES = MACD_TIMES
        # [
        #     [240, 100, 240]
        # ] 
        self.FORCE_CAL = FORCE_CAL
        # {
        #     'BUSD': False,
        #     'Price': True
        # }
        self.lastPrice = None

        self.initial()

    def getAggtradeData(self, startTime, stopTime):
        print(f"\r{self.symbol} Get BUSD data from {startTime} {datetime.fromtimestamp(startTime/1000, tz=VN_TZ)} to {stopTime} {datetime.fromtimestamp(stopTime/1000, tz=VN_TZ)}")
        busd = list(self.busdModel.collection.find({'symbol': self.symbol, 'timestamp':{'$gte': startTime/1000, '$lte': stopTime/1000}}, {
            '_id': False,
            'symbol':1,
            'timestamp':1,
            'BU':1,
            'SD':1,
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
        df = df.drop_duplicates(subset=['timestamp'], keep='last')
        # firstPrice = df['close'].iloc[0]
        # if np.isnan(firstPrice) and self.lastPrice is not None:
        #     df = pd.concat([self.lastPrice, df])
        # df['close'] = df['close'].fillna(method='ffill')
        # self.lastPrice = df[-7410:]
        return df
    
    # def getData(self, startTime, stopTime):
    #     return self.getAggtradeData(startTime, stopTime)


    
        
    
                


    

    


    


    


                
    


    
