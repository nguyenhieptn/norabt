from datetime import datetime
from dateutil import tz

from django.core.management.base import BaseCommand
from Backtest.Processors.BusdProcessor_1m import BusdProcessor_1m
from helper.Defaults import *
from helper.Data import *

from helper.Defaults import *

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

    def handle(self, *args, **options):
        self.symbol = options.get('symbol').upper()
        self.day = options.get('day', None)
        self.busdModel = BusdModel('backtest_data_1m')
        self.busdModel.collection.create_index([(BusdModel.symbol, ASCENDING), (BusdModel.timestamp, ASCENDING)])

        self.processor = BusdProcessor_1m(self.symbol, 'raw_kline1m_future', [
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
        ], {'BUSD': False, 'Price': True})

        startTime = self.getStartTime()
        stopTime = int(datetime.now().timestamp()) * 1000 - 1
        historyTime = startTime - 38 * 60 * 60 * 1000

        #get history data to reate first block data
        print(f"{self.symbol} Get Calculate first Block from {historyTime} {datetime.fromtimestamp(historyTime/1000, tz=VN_TZ)} to {startTime} {datetime.fromtimestamp(startTime/1000, tz=VN_TZ)}")
        historyDatas = self.processor.getData(historyTime, startTime-1)
        print(f"{self.symbol} Calculating first block {len(historyDatas)} points...")
        
        self.processor.calBUSDBlock(historyDatas, True)
        print(f"{self.symbol} Completed Calculating first block")

        workingTime = startTime
        startPoint = datetime.now().timestamp()
    
        while(workingTime < stopTime):
            newWorkingTime = workingTime + 15 * 24 * 60 * 60 * 1000 - 1
            datas = self.processor.getData(workingTime, newWorkingTime)
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





        
        
        
        

    
        
        





        

        

        







        

        


    