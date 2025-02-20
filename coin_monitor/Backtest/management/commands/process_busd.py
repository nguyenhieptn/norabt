from datetime import datetime
from dateutil import tz

from django.core.management.base import BaseCommand
from sqlalchemy import true
from Backtest.Processors.BusdProcessor import BusdProcessor
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


import pandas as pd
from models.Wrappers.backtestDataWrapper import BacktestBusdWrapper
from models.Mongo.BusdModel import BusdModel
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
        self.busdModel = BusdModel()
        self.busdModel.collection.create_index([(BusdModel.symbol, ASCENDING), (BusdModel.timestamp, ASCENDING)])
        macd_timeframes = [
            [15, 100, 3], 
            [15, 300, 3], 
            [60, 100, 240], 
            [60, 1200, 3], 
            [60, 1200, 5], 
            [60, 1200, 60], 
            [240, 4800, 5], 
            [240, 4800, 30], 
            [240, 4800, 60], 
            [1440, 28800, 60]
        ] 
        cal = {'BUSD':True, 'Price':True}
        self.processor = BusdProcessor(self.symbol, macd_timeframes, cal)
        self.reset = options.get('reset', False)
        if(self.reset):
            print("Clean data")
            self.busdModel.collection.delete_many({'symbol': self.symbol})
        startTime = self.getStartTime()
        stopTime = int(datetime.now().timestamp()) * 1000 - 1
        historyTime = startTime - 38 * 60 * 60 * 1000

        #get history data to reate first block data
        print(f"{self.symbol} Get Calculate first Block from {historyTime} {datetime.fromtimestamp(historyTime/1000, tz=VN_TZ)} to {startTime} {datetime.fromtimestamp(startTime/1000, tz=VN_TZ)}")
        historyDatas = self.processor.getData(historyTime, startTime)
        print(f"{self.symbol} Calculating first block {len(historyDatas)} points...")
        
        processed = 0
        self.processor.calBUSDBlock(historyDatas, True)
       
        print(f"{self.symbol} Completed Calculating first block")

        workingTime = startTime
        startPoint = datetime.now().timestamp()
        mongoBlock = []
        while(workingTime < stopTime):
            newWorkingTime = workingTime + 12 * 60 * 60 * 1000 - 1
            datas = self.processor.getData(workingTime, newWorkingTime)
            # print(type(datas))
            timeSeconds = self.processor.calBUSDBlock(datas, False)
            processed = 0
            for timeSecond in timeSeconds:
                returnData = self.processor.processData(timeSecond)
                mongoBlock.append(returnData)
                if(len(mongoBlock) > 1000):
                    self.busdModel.collection.insert_many(mongoBlock)
                    mongoBlock = []
                processed += 1
                if(processed % 1000 == 0):
                    checkTimePoint = datetime.now().timestamp()
                    print(f"\r{self.symbol} Speed {int(1000/(checkTimePoint - startPoint))} package/s processed:{processed}/{len(timeSeconds)} len={len(self.processor.busd)}   ", end='')
                    startPoint = checkTimePoint

            workingTime = newWorkingTime + 1

        if(len(mongoBlock) > 1000):
            self.busdModel.collection.insert_many(mongoBlock)

    def getStartTime(self):
            lastData = list(BacktestBusdWrapper().filter({BacktestBusdWrapper.symbol: self.symbol}).order_by(f"-{BacktestBusdWrapper.timestamp}")[:1])
            if(len(lastData) > 0):
                return (lastData[0].timestamp + 1) * 1000
            else:
                if(self.day is None):
                    startTime = int(datetime.now().timestamp() * 1000) - 7 * 86400000
                    startTime = startTime//86400000 * 86400000
                    return startTime
                else:
                    return int(datetime.strptime(self.day, '%Y_%m_%d').replace(tzinfo=VN_TZ).timestamp() * 1000)





        
        
        
        

    
        
        





        

        

        







        

        


    