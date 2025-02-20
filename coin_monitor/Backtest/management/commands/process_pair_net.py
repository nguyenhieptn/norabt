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
    help = 'python manage.py process_pair_net -d 2022_01_24 --reset'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        parser.add_argument("-d","--day", type=str)
        parser.add_argument("-del","--delete", type=str)
        parser.add_argument("--reset", action='store_true', default=False)
        
    def getCollection(self):
        collections = {}
        historyCollSSD = self.rawDbSSD.database.list_collection_names(filter = {"name": {"$regex": r".*_MATICUSDT_kline_1m$"}})
        for collection in historyCollSSD:
            collections[collection[:10]] = 'SSD'
        historyCollHDD = self.rawDbHDD.database.list_collection_names(filter = {"name": {"$regex": r".*_MATICUSDT_kline_1m$"}})
        for collection in historyCollHDD:
            collections[collection[:10]] = 'HDD'
        return collections
        
        
        

    def handle(self, *args, **options):
        self.database = MongoModel('backtest_data').setCollection('pair_net')
        self.database.collection.create_index([('symbol', ASCENDING), ('timestamp', ASCENDING)])
        self.database.collection.create_index([('day', ASCENDING)])
        self.rawDbSSD = MongoModel('raw_data')
        self.rawDbHDD = MongoModel('raw_data_01')
        self.collections = self.getCollection()
        self.day = options.get('day', None)
        self.reset = options.get('reset', False)
        self.delDay = options.get('delete', None)
        self.F1Symbols = ['MATICUSDT']
        self.F2Symbols = ['THETAUSDT']
        self.symbols = self.F1Symbols + self.F2Symbols
        if(self.reset):
            print("Clean data")
            self.database.collection.drop()
            
        if(self.delDay is not None):
            print(f"Delete data from {self.delDay}")
            delTimestamp = datetime.strptime(self.delDay, '%Y_%m_%d').replace(tzinfo=VN_TZ).timestamp()
            self.database.collection.delete_many({'symbol':'USDTPERP', 'timestamp':{'$gte': delTimestamp}})
            
 
        startDayStr = self.getStartDay()
        historyLeng = 1
        historyColls = list(self.collections.keys())
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
        if(day not in self.collections): return []
        if(self.collections[day] == 'SSD'):
            rawDb = self.rawDbSSD
        else:
            rawDb = self.rawDbHDD
            
        symbolDatas = []
        for symbol in self.symbols:
            
            symbKlineDb = f"{day}_{symbol}_kline_1m"
            symbDepthDb = f"{day}_{symbol}_depth20"
            klineData = list(rawDb.setCollection(symbKlineDb).collection.find({}, {'_id':0, 'E':1, 'k.c':1}))
            if(len(klineData) == 0):
                logger.warning(f"{day} {symbol} Kline No data")
                return
            klineData = pd.DataFrame(klineData)
            klineData['timestamp'] = klineData['E']//1000
            klineData = klineData.groupby('timestamp').last().reset_index()
            priceColumn = klineData['k'].apply(pd.Series)
            klineData = pd.concat([klineData.drop('k', axis=1), priceColumn], axis=1).set_index('timestamp')
            klineData = klineData.drop('E', axis=1)
            klineData['c'] = klineData['c'].astype(float)
            
            depthData = list(rawDb.setCollection(symbDepthDb).collection.find({}, {'_id':0, 'E':1, 'b':1, 'a':1}))
            if(len(depthData) == 0):
                logger.warning(f"{day} {symbol} Depth No data")
                return
            depthData = pd.DataFrame(depthData)
            depthData['timestamp'] = depthData['E']//1000
            depthData = depthData.groupby('timestamp').last().reset_index()
            bidAsk = depthData.apply(lambda x: pd.Series({
                'best1Bid': float(x['b'][0][0]),
                'best1BidVol': float(x['b'][0][1]),
                'best1Offer': float(x['a'][0][0]),
                'best1OfferVol': float(x['a'][0][1]),
                'best2Bid': float(x['b'][1][0]),
                'best2BidVol': float(x['b'][1][1]),
                'best2Offer': float(x['a'][1][0]),
                'best2OfferVol': float(x['a'][1][1]),
            }), axis=1)
            bidAsk = bidAsk.loc[bidAsk['best1Bid'] < bidAsk['best1Offer']]
            
            depthData = pd.concat([depthData.drop(['a','b'], axis=1), bidAsk], axis=1).set_index('timestamp')
            depthData = depthData.drop('E', axis=1)
            fullData = pd.concat([klineData, depthData], axis=1).sort_index().ffill()
            fullData = fullData.rename(columns={'c':'lastPrice'}).add_prefix(f"{symbol}_")
            symbolDatas.append(fullData)
            
        datas:pd.DataFrame = pd.concat(symbolDatas, axis=1)
        datas = datas.sort_index()
        datas = datas.ffill()
        
        datas['F1_best1Bid'] = 0
        for symbol in self.F1Symbols:
            datas['F1_best1Bid'] = datas['F1_best1Bid'] + datas[f'{symbol}_best1Bid']
            
        datas['F2_best1Bid'] = 0
        for symbol in self.F2Symbols:
            datas['F2_best1Bid'] = datas['F2_best1Bid'] + datas[f'{symbol}_best1Bid']
            
        datas['F1_best1Offer'] = 0
        for symbol in self.F1Symbols:
            datas['F1_best1Offer'] = datas['F1_best1Offer'] + datas[f'{symbol}_best1Offer']
            
        datas['F2_best1Offer'] = 0
        for symbol in self.F2Symbols:
            datas['F2_best1Offer'] = datas['F2_best1Offer'] + datas[f'{symbol}_best1Offer']
        
        datas['NET_F1B1_F2A1'] = datas['F1_best1Bid'] - datas['F2_best1Offer']
        datas['NET_F1A1_F2B1'] = datas['F1_best1Offer'] - datas['F2_best1Bid']
        datas['timestamp'] = datas.index
        datas['symbol'] = 'USDTPERP'
        datas['day'] = day
        
        datas = datas.to_dict(orient='records')
    
        return datas
                


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
        





        
        
        
        

    
        
        





        

        

        







        

        


    