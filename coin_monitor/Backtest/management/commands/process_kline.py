from datetime import datetime
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


import pandas as pd

from models.Mongo.KlineModel import KlineModel


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
        self.processor = klineProcessor(self.symbol)
        self.reset = options.get('reset', False)
        if(self.reset):
            print("Clean data")
            self.processor.cleanData()
            
        startTime = self.getStartTime()//1000 * 1000
        stopTime = int(datetime.now().timestamp()) * 1000 - 1
        
        processed = 0
        
        workingTime = startTime
        startPoint = datetime.now().timestamp()
        while(workingTime < stopTime):
            newWorkingTime = workingTime + 12 * 60 * 60 * 1000 - 1
            datas = self.processor.getKlineData(workingTime, newWorkingTime)
            print(len(datas))
            processed = 0
            for data in datas:
                self.processor.processData(data)
                
                processed += 1
                if(processed % 1000 == 0):
                    checkTimePoint = datetime.now().timestamp()
                    print(f"\r{self.symbol} Speed {int(1000/(checkTimePoint - startPoint))} package/s processed:{processed}/{len(datas)}  ", end='')
                    startPoint = checkTimePoint

            workingTime = newWorkingTime + 1



        


    def getStartTime(self):

        
            startTime = self.processor.getStartTime()
            if(startTime is None):
                if(self.day is None):
                    startTime = int(datetime.now().timestamp() * 1000) - 7 * 86400000
                    startTime = startTime//86400000 * 86400000
                    return startTime
                else:
                    return int(datetime.strptime(self.day, '%Y_%m_%d').replace(tzinfo=VN_TZ).timestamp() * 1000)
            else:
                return startTime
        





        
        
        
        

    
        
        





        

        

        







        

        


    