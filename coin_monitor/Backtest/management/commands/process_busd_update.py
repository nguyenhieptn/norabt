from datetime import datetime
from dateutil import tz

from django.core.management.base import BaseCommand
from sqlalchemy import true
from Backtest.Processors.BusdProcessor import BusdProcessor
from Backtest.Processors.BusdUpdate import BusdUpdate
from helper.Defaults import *
from helper.Data import *

from helper.Defaults import *

from models.Mongo.BusdModel import BusdModel
from pymongo import ASCENDING, DESCENDING


VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'Generate testnet chart'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        parser.add_argument("-s","--symbol", nargs='?', required=True, default=None, type=str)
        parser.add_argument("-db","--database", nargs='?', required=False, default='backtest_data', type=str)
        parser.add_argument("-d","--day", nargs='?', default=None, type=str)
        parser.add_argument("-sd","--sday", nargs='?', default=None, type=str)
        

    def handle(self, *args, **options):
        self.symbol = options.get('symbol').upper()
        self.database = options.get('database')
        self.day = options.get('day', None)
        self.sday = options.get('sday', None)
        self.busdModel = BusdModel(self.database)
        self.busdModel.collection.create_index([(BusdModel.symbol, ASCENDING), (BusdModel.timestamp, ASCENDING)])
        self.processor = BusdProcessor(self.symbol, [
            [15, 100, 3], 
            # [15, 300, 3], 
            [60, 100, 240], 
            [60, 1200, 3], 
            # [60, 1200, 5], 
            # [60, 1200, 60], 
            # [240, 4800, 5], 
            [240, 4800, 30], 
            # [240, 4800, 60], 
            [1440, 28800, 60]
        ],{
            'BUSD':False,
            'Price':True
        })
        startTime = self.getStartTime()
        if(startTime is None): return
        stopTime = self.getStopTime()
        historyTime = startTime - self.processor.maxLeng * 1000

        #get history data to reate first block data
        print(f"\r{self.symbol} Get Calculate first Block from {historyTime} {datetime.fromtimestamp(historyTime/1000, tz=VN_TZ)} to {startTime} {datetime.fromtimestamp(startTime/1000, tz=VN_TZ)}")
        historyDatas = self.processor.getData(historyTime, startTime - 1)
        print(f"{self.symbol} Calculating first block {len(historyDatas)} points...")
        
        processed = 0
        if len(historyDatas) > 0:
            self.processor.calBUSDBlock(historyDatas, True)
            print(f"{self.symbol} Completed Calculating first block")

        workingTime = startTime
        startPoint = datetime.now().timestamp()
        while(workingTime < stopTime):
            newWorkingTime = workingTime + 12 * 60 * 60 * 1000 - 1
            datas = self.processor.getData(workingTime, newWorkingTime)
            if len(datas) == 0:
                workingTime = newWorkingTime + 1
                continue
            timeSeconds = self.processor.calBUSDBlock(datas, False)
            processed = 0
            for timeSecond in timeSeconds:
                returnData = self.processor.processData(timeSecond)
                self.busdModel.collection.update_one({'symbol': returnData['symbol'], 'timestamp': returnData['timestamp']}, {'$set': returnData})
                processed += 1
                if(processed % 1000 == 0):
                    checkTimePoint = datetime.now().timestamp()
                    print(f"\r{self.symbol} Speed {int(1000/(checkTimePoint - startPoint))} package/s processed:{processed}/{len(timeSeconds)} len={len(self.processor.busd)}   ", end='')
                    startPoint = checkTimePoint

            workingTime = newWorkingTime + 1


    def getStartTime(self):
        if(self.day is None):
            lastData = list(self.busdModel.collection.find({'symbol': self.symbol}).sort('timestamp', ASCENDING).limit(1))
            if(len(lastData) > 0):
                return lastData[0]['timestamp'] * 1000 
            return None
        else:
            return int(datetime.strptime(self.day, '%Y_%m_%d').replace(tzinfo=VN_TZ).timestamp() * 1000)
    
    def getStopTime(self):
        if(self.sday is None):
            return int(datetime.now().timestamp()) * 1000 - 1
        else:
            return int(datetime.strptime(self.sday, '%Y_%m_%d').replace(tzinfo=VN_TZ).timestamp() * 1000)





        
        
        
        

    
        
        





        

        

        







        

        


    