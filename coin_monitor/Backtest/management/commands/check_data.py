from datetime import datetime
from os import stat
import subprocess
import sys
from dateutil import tz

from django.core.management.base import BaseCommand
from Backtest.Processors.klineProcessor import klineProcessor
from helper.Defaults import *
from helper.Data import *

from math import floor
from threading import Thread
from time import sleep, time
import orjson
from helper.Redis import Redis
from helper.Defaults import *
import pandas as pd
from pymongo import DESCENDING, ASCENDING


import pandas as pd

from models.Mongo.CandleModel import Candle_Model
from models.Mongo.BusdModel import BusdModel
from models.Mongo.OrderbookModel import Order_bookModel


VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'Generate testnet chart'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        parser.add_argument("-db","--database", nargs='?', default=None, type=str)
        parser.add_argument("-t","--type", nargs='?', default='all', type=str)

    def handle(self, *args, **options):
        self.database = options.get('database', None)
        self.checkType = options.get('type', 'all')
        if(self.database is None): self.database = 'backtest_data'
        self.candleModel = Candle_Model(self.database)
        self.busdModel = BusdModel(self.database)
        self.orderBookModel = Order_bookModel(self.database)
        print(f'=============={self.database}================')
        if(self.checkType == 'all' or self.checkType == 'busd'):
            self.checkBUSD()
        if(self.checkType == 'all' or self.checkType == 'orderbook'):
            self.checkOrderBook()
        if(self.checkType == 'all' or self.checkType == 'candle'):
            for frame in ['1m', '3m', '15m', '1h', '4h', '1d', '1w']:
                self.checkCandle(frame)

    def checkBUSD(self):
        symbols = list(self.busdModel.collection.distinct(BusdModel.symbol))
        busdData = []
        for symbol in symbols:
            rowData = {'symbol': symbol}
            startTime = list(self.busdModel.collection.find({BusdModel.symbol: symbol}).sort(BusdModel.timestamp, ASCENDING).limit(1))
            if(len(startTime) > 0): startTime = startTime[0][BusdModel.timestamp]
            rowData['startTime'] = datetime.fromtimestamp(startTime, VN_TZ)

            stopTime = list(self.busdModel.collection.find({BusdModel.symbol: symbol}).sort(BusdModel.timestamp, DESCENDING).limit(1))
            if(len(stopTime) > 0): stopTime = stopTime[0][BusdModel.timestamp]
            rowData['stopTime'] = datetime.fromtimestamp(stopTime, VN_TZ)

            busdData.append(rowData)
        df = pd.DataFrame.from_records(busdData)
        print(f'==============BUSD================')
        print(df) 

    def checkOrderBook(self):
        symbols = list(self.orderBookModel.collection.distinct(Order_bookModel.symbol))
        orderBook = []
        for symbol in symbols:
            rowData = {'symbol': symbol}
            startTime = list(self.orderBookModel.collection.find({Order_bookModel.symbol: symbol}).sort(Order_bookModel.timestamp, ASCENDING).limit(1))
            if(len(startTime) > 0): startTime = startTime[0][Order_bookModel.timestamp]
            rowData['startTime'] = datetime.fromtimestamp(startTime, VN_TZ)

            stopTime = list(self.orderBookModel.collection.find({Order_bookModel.symbol: symbol}).sort(Order_bookModel.timestamp, DESCENDING).limit(1))
            if(len(stopTime) > 0): stopTime = stopTime[0][Order_bookModel.timestamp]
            rowData['stopTime'] = datetime.fromtimestamp(stopTime, VN_TZ)

            orderBook.append(rowData)
        df = pd.DataFrame.from_records(orderBook)
        print(f'==============ORDER BOOK================')
        print(df) 
        # if 'startTime' in df:
        #     df['year'] = df['startTime'].map(lambda x: x.year)
        #     print(df[df['year'] == 2019])

    def checkCandle(self, frame):
        self.candleModel.setCollection(f'candle_{frame}')
        symbols = list(self.candleModel.collection.distinct(Candle_Model.symbol))
        candleData = []
        for symbol in symbols:
            rowData = {'symbol': symbol}
            startTime = list(self.candleModel.collection.find({Candle_Model.symbol: symbol}).sort(Candle_Model.timestamp, ASCENDING).limit(1))
            if(len(startTime) > 0): startTime = startTime[0][Candle_Model.timestamp]
            rowData['startTime'] = datetime.fromtimestamp(startTime, VN_TZ)

            stopTime = list(self.candleModel.collection.find({Candle_Model.symbol: symbol}).sort(Candle_Model.timestamp, DESCENDING).limit(1))
            if(len(stopTime) > 0): stopTime = stopTime[0][Candle_Model.timestamp]
            rowData['stopTime'] = datetime.fromtimestamp(stopTime, VN_TZ).year

            candleData.append(rowData)
        df = pd.DataFrame.from_records(candleData)
        print(f'==============Candle {frame}================')
        print(df)
        # df['year'] = df['startTime'].map(lambda x: x.year)
        # print(df[df['year'] == 2019])



        

    




        


    





        
        
        
        

    
        
        





        

        

        







        

        


    