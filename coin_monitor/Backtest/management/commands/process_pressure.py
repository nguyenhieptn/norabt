from dateutil import tz
from time import time

from django.core.management.base import BaseCommand
from Backtest.Processors.pressureProcessor import pressureProcessor
from helper.Defaults import *
from helper.Data import *

import pandas as pd

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
        self.processor = pressureProcessor(self.symbol)
        self.saveModel = MongoModel('backtest_data', 'pressure')
        self.saveModel.collection.create_index([('symbol', 1), ('timestamp', 1)])
        self.reset = options.get('reset', False)
        if(self.reset):
            print("Clean data")
            self.saveModel.collection.delete_many({"symbol":self.symbol})
            
        startTime = self.getStartTime()//1000 * 1000
        stopTime = int(datetime.now().timestamp()) * 1000 - 1
        
        processed = 0
        
        workingTime = startTime
        startPoint = datetime.now().timestamp()

        while(workingTime < stopTime):
            newWorkingTime = workingTime + 12 * 60 * 60 * 1000 - 1
            datas = self.processor.getData(workingTime, newWorkingTime)
            datas = self.processor.calIndicatorBlock(datas)
            print("\n")
            print("Insert data")
            print("\n")
            total = len(datas)
            inserted = 0
            block = 1000

            while inserted < total:
                insertData = datas[inserted:inserted + block]
                self.saveModel.collection.insert_many(insertData)
                inserted = inserted + block
                print(f"Inserted: {inserted}/{total}", end="\r")

            workingTime = newWorkingTime + 1



    def getStartTime(self):

        lastData = list(self.saveModel.collection.find({'symbol': self.symbol}).sort('timestamp',-1).limit(1))
        if(len(lastData) > 0):
            return int((lastData[0]['timestamp'] + 1) * 1000)
        else:
            if(self.day is None):
                startTime = int(datetime.now().timestamp() * 1000) - 7 * 86400000
                startTime = startTime//86400000 * 86400000
                return startTime
            else:
                return int(datetime.strptime(self.day, '%Y_%m_%d').replace(tzinfo=VN_TZ).timestamp() * 1000)
        





        
        
        
        

    
        
        





        

        

        







        

        


    