from datetime import datetime
from dateutil import tz

from django.core.management.base import BaseCommand
from py import process
from Backtest.Processors.deepProcessor import deepProcessor
from helper.Defaults import *
from helper.Data import *

from math import floor
from threading import Thread
from time import sleep, time
import orjson
from datetime import datetime as dt
from helper.Redis import Redis
from helper.Defaults import *
import pandas as pd


import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots
from models.Mongo.KlineModel import KlineModel
from models.Wrappers.backtestDataWrapper import BacktestOrderBookWrapper
from models.nora_realtime import OrderBook
from models.Mongo.AggTradeModel import AggTradeModel
from pymongo import ASCENDING


VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'Generate testnet chart'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
        
        
    def add_arguments(self, parser):
        parser.add_argument("-s","--symbol", nargs='?', required=True, default=None, type=str)
        parser.add_argument("-d","--day", nargs='?', default=None, type=str)
        parser.add_argument("--reset", action='store_true', default=False)

    def handle(self, *args, **options):
        self.symbol = options.get('symbol').upper()
        self.day = options.get('day', None)
        self.processor = deepProcessor(self.symbol)
        self.reset = options.get('reset', False)
        if(self.reset):
            print("Clean data")
            BacktestOrderBookWrapper().filter({BacktestOrderBookWrapper.symbol: self.symbol}).delete()
        startTime = self.getStartTime()
        stopTime = int(datetime.now().timestamp()) * 1000 - 1
        historyTime = startTime - 8 * 60 * 60 * 1000

        #get history data to reate first block data
        print(f"{self.symbol} Get Calculate first Block from {historyTime} {datetime.fromtimestamp(historyTime/1000, tz=VN_TZ)} to {startTime} {datetime.fromtimestamp(startTime/1000, tz=VN_TZ)}")
        historyDatas = self.processor.getData(historyTime, startTime)
        print(f"{self.symbol} Calculating first block {len(historyDatas)} points...")
        startPoint = datetime.now().timestamp()
        processed = 0
        for historyData in historyDatas:
            self.processor.processData(historyData)
            processed += 1
            if(processed % 5000 == 0):
                checkTimePoint = datetime.now().timestamp()
                print(f"\r{self.symbol} Speed {int(5000/(checkTimePoint - startPoint))} package/s processed:{processed}/{len(historyDatas)} {len(self.processor.askInSecondDic)} len={len(self.processor.indicatorData)}   ", end='')
                startPoint = checkTimePoint

        print(f"{self.symbol} Completed Calculating first block")

        workingTime = startTime
        while(workingTime < stopTime):
            newWorkingTime = workingTime + 12 * 60 * 60 * 1000 - 1
            datas = self.processor.getData(workingTime, newWorkingTime)
            processed = 0
            for data in datas:
                returnData = self.processor.processData(data)
                if(returnData is not False):
                    BacktestOrderBookWrapper().bulk_create([OrderBook(**value) for value in returnData], 500)
                processed += 1
                if(processed % 5000 == 0):
                    checkTimePoint = datetime.now().timestamp()
                    print(f"\r{self.symbol} Speed {int(5000/(checkTimePoint - startPoint))} package/s processed:{processed}/{len(datas)} {len(self.processor.askInSecondDic)} len={len(self.processor.indicatorData)}   ", end='')
                    startPoint = checkTimePoint

            workingTime = newWorkingTime + 1



        


    def getStartTime(self):

        
            lastData = list(BacktestOrderBookWrapper().filter({BacktestOrderBookWrapper.symbol: self.symbol}).order_by(f"-{BacktestOrderBookWrapper.timestamp}")[:1])
            if(len(lastData) > 0):
                return (lastData[0].timestamp + 1) * 1000
            else:
                if(self.day is None):
                    startTime = int(datetime.now().timestamp() * 1000) - 7 * 86400000
                    startTime = startTime//86400000 * 86400000
                    return startTime
                else:
                    return int(datetime.strptime(self.day, '%Y_%m_%d').replace(tzinfo=VN_TZ).timestamp() * 1000)





        
        
        
        

    
        
        





        

        

        







        

        


    