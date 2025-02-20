from datetime import datetime, timedelta
from dateutil import tz

from django.core.management.base import BaseCommand
from helper.Defaults import *
from helper.Data import *

from math import floor
from threading import Thread
from time import sleep, time
import orjson
from helper.Redis import Redis
from helper.Defaults import *
from helper.Logger import logger
import pandas as pd
from pymongo import DESCENDING, ASCENDING

from Backtest.Processors.PairProcessorLongTerm import PairProcessorLongTerm


VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'python manage.py process_pair_indicator -d 2023_03_13 --reset'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        parser.add_argument("-d","--day", type=str)
        parser.add_argument("-del","--delete", type=str)
        parser.add_argument("--reset", action='store_true', default=False)
        
        

    def handle(self, *args, **options):
        self.database = MongoModel('backtest_data').setCollection('pair_indicator_eth')
        self.database.collection.create_index([('symbol', ASCENDING), ('timestamp', ASCENDING)])
        self.database.collection.create_index([('day', ASCENDING)])
        self.rawDb = MongoModel('backtest_data').setCollection('pair_net_eth')
        self.day = options.get('day', None)
        self.reset = options.get('reset', False)
        self.delDay = options.get('delete', None)
        
        if(self.reset):
            print("Clean data")
            self.database.collection.drop()
            
        if(self.delDay is not None):
            print(f"Delete data from {self.delDay}")
            delTimestamp = datetime.strptime(self.delDay, '%Y_%m_%d').replace(tzinfo=VN_TZ).timestamp()
            self.database.collection.delete_many({'symbol':'USDTPERP', 'timestamp':{'$gte': delTimestamp}})
            
 
        startDayStr = self.getStartDay()
        historyLeng = 1
        historyColls = list(self.rawDb.collection.distinct('day'))
        historyColls.sort()
        
        olderColls = [x for x in historyColls if x < startDayStr]
        olderColls.sort()
        if(len(olderColls) >= historyLeng):
            listOfHistory = olderColls[-historyLeng:]
        else:
            listOfHistory = []
        
        startDay = datetime.strptime(startDayStr, '%Y_%m_%d').replace(tzinfo=VN_TZ)
        stopDay = datetime.now(tz=VN_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        listOfDay = [(startDay + timedelta(days=x)).strftime('%Y_%m_%d') for x in range((stopDay - startDay).days + 1)]
        
        self.processor = PairProcessorLongTerm()
        
        for day in listOfHistory:
            logger.info(f'Process history data {day}')
            datas = self.processDay(day)
        
        for day in listOfDay:
            logger.info(f'Process PS data {day}')
            datas = self.processDay(day)
            if(datas is not None and len(datas) > 0):
                self.database.collection.insert_many(datas)
            
            

           
    def processDay(self, day):
        datas = list(self.rawDb.collection.find({'day':day}))
        insertDatas = self.processor.processBlockData(datas)
        return insertDatas
                


    def getStartDay(self):
        lastData = list(self.database.collection.find({'symbol':'USDTPERP'}).sort('timestamp', DESCENDING).limit(1))
        
        if(len(lastData) > 0):
            timestamp = lastData[0]['timestamp']
            startDate = datetime.fromtimestamp(float(timestamp)/1000, tz=VN_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
            logger.warning(f"Delete data from {startDate}")
            self.database.collection.delete_many({'symbol':'USDTPERP', 'timestamp':{'$gte': startDate.timestamp()}})
            startDate=startDate.strftime('%Y_%m_%d')
        else:
            startDate = self.day
        return startDate
        





        
        
        
        

    
        
        





        

        

        







        

        


    