from datetime import datetime, timedelta
from dateutil import tz

from django.core.management.base import BaseCommand
from helper.Defaults import *
from helper.Data import *
from helper.Data import DataTaker

from math import floor
from threading import Thread
from time import sleep, time
import orjson
from helper.Redis import Redis
from helper.Logger import logger
import pandas as pd
from pymongo import DESCENDING, ASCENDING

from Backtest.Processors.PairProcessorLongTerm import PairProcessorLongTerm


VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'python manage.py process_pair_net_2 -d 2023_03_13 --reset'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        parser.add_argument("-d","--day", type=str)
        parser.add_argument("-del","--delete", type=str)
        parser.add_argument("--reset", action='store_true', default=False)
        
    def handle(self, *args, **options):
        self.dataTaker = DataTaker()
        self.database = MongoModel('backtest_data').setCollection('pair_net_eth')
        self.database.collection.create_index([('symbol', ASCENDING), ('timestamp', ASCENDING)])
        self.database.collection.create_index([('day', ASCENDING)])
       
        self.day = options.get('day', None)
        self.reset = options.get('reset', False)
        self.delDay = options.get('delete', None)
        self.F1Symbols = ['ETHUSDT']
        self.F2Symbols = ['ETHUSDTQ1']
        self.symbols = self.F1Symbols + self.F2Symbols
        if(self.reset):
            print("Clean data")
            self.database.collection.drop()
            
        if(self.delDay is not None):
            print(f"Delete data from {self.delDay}")
            delTimestamp = datetime.strptime(self.delDay, '%Y_%m_%d').timestamp()
            self.database.collection.delete_many({'symbol':'USDTPERP', 'timestamp':{'$gte': delTimestamp}})
            
 
        startDayStr = self.getStartDay()
        historyLeng = 1
        historyColls = self.dataTaker.listOfDays
        historyColls.sort()
        
        olderColls = [x for x in historyColls if x < startDayStr]
        olderColls.sort()
        if(len(olderColls) >= historyLeng):
            listOfHistory = olderColls[-historyLeng:]
        else:
            listOfHistory = []
        
        startDay = datetime.strptime(startDayStr, '%Y_%m_%d')
        stopDay = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
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
        symbolDatas = []
        for symbol in self.symbols:
            
            klineData = list(self.dataTaker.getData(day, symbol, 'kline_1m', {'_id':0, 'E':1, 'k.c':1, 'k.v':1}))
            if(len(klineData) == 0):
                logger.warning(f"{day} {symbol} Kline No data")
                return
            klineData = pd.DataFrame(klineData)
            klineData['timestamp'] = (klineData['E']//250)*250
            klineData = klineData.groupby('timestamp').last().reset_index()
            priceColumn = klineData['k'].apply(pd.Series)
            klineData = pd.concat([klineData.drop('k', axis=1), priceColumn], axis=1).set_index('timestamp')
            klineData = klineData.drop('E', axis=1)
            klineData['c'] = klineData['c'].astype(float)
            klineData['v'] = klineData['v'].astype(float)
            depthData = list(self.dataTaker.getData(day, symbol, 'depth20', {'_id':0, 'E':1, 'b':1, 'a':1}))
            if(len(depthData) == 0):
                logger.warning(f"{day} {symbol} Depth No data")
                return
            depthData = pd.DataFrame(depthData)
            depthData['timestamp'] = (depthData['E']//250)*250
            depthData = depthData.groupby('timestamp').last().reset_index()
            
            def getBidAsk(depthRowDt:dict):
                bid = depthRowDt.get('b', [])
                ask = depthRowDt.get('a', [])
                bidAskRow = {
                    'best1Bid': 0,
                    'best1BidVol': 0,
                    'best1Offer': 0,
                    'best1OfferVol': 0,
                    'best2Bid': 0,
                    'best2BidVol': 0,
                    'best2Offer': 0,
                    'best2OfferVol': 0,
                }
                if(len(bid) > 0):
                    bidAskRow['best1Bid'] = float(bid[0][0])
                    bidAskRow['best1BidVol'] = float(bid[0][1])
                if(len(ask) > 0):
                    bidAskRow['best1Offer'] = float(ask[0][0])
                    bidAskRow['best1OfferVol'] = float(ask[0][1])
                if(len(bid) > 1):
                    bidAskRow['best2Bid'] = float(bid[1][0])
                    bidAskRow['best2BidVol'] = float(bid[1][1])
                if(len(ask) > 1):
                    bidAskRow['best2Offer'] = float(ask[1][0])
                    bidAskRow['best2OfferVol'] = float(ask[1][1])
                return pd.Series(bidAskRow)
              
            bidAsk = depthData.apply(getBidAsk, axis=1)
            bidAsk = bidAsk.loc[bidAsk['best1Bid'] < bidAsk['best1Offer']]
            
            depthData = pd.concat([depthData.drop(['a','b'], axis=1), bidAsk], axis=1).set_index('timestamp')
            depthData = depthData.drop('E', axis=1)
            fullData = pd.concat([klineData, depthData], axis=1).sort_index().ffill()
            fullData = fullData.rename(columns={'c':'lastPrice'}).add_prefix(f"{symbol}_")
            symbolDatas.append(fullData)
            
        datas:pd.DataFrame = pd.concat(symbolDatas, axis=1)
        datas = datas.sort_index()
        datas = datas.ffill()
        
        for symbol in self.F1Symbols + self.F2Symbols:
            datas[f'{symbol}_pv'] = datas[f'{symbol}_v'].shift(1)
            datas[f'{symbol}_matchedVol'] = datas[f'{symbol}_v'] - datas[f'{symbol}_pv']
            datas.loc[datas[f'{symbol}_matchedVol'] < 0, f'{symbol}_matchedVol'] = datas[f'{symbol}_v']
        
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
        





        
        
        
        

    
        
        





        

        

        







        

        


    