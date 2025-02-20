
from math import floor
from threading import Thread
from time import sleep, time
import orjson
from datetime import datetime as dt
from helper.Redis import Redis
from helper.Defaults import *
from helper.Data import *
from pymongo import ASCENDING
from models.Mongo.KlineModel import KlineModel
from models.Mongo.DepthModel import DepthModel


import pandas as pd
import numpy as np

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')


class deepProcessor():

    indicatorData = None
    '''
    An array of order book data
    max leng: 500
    ```
    [
        {
            symbol: symbol
            tran_time: Transaction time
            event_time: Event Time
            ready_time: Time data is ready on redis
            timestamp: time by second
            best_ask: min ask price
            best_bid: max bid price
            mid_price : Mid price
            askV_1 : Ask Volume in 1% 
            bidV_1 : Bid Volume in 1% 
            askV_2 : Ask Volume in 2% 
            bidV_2 : Bid Volume in 2% 
            askV_5 : Ask Volume in 5% 
            bidV_5 : Bid Volume in 5% 
            bidV_ma_5 : Bid Volume ma in 5% 
            askV_ma_5 : Ask Volume ma in 5% 
            NetBA_5
            NetBA_std_5
            NetBA_mean_5
            NetBA_BOLU_5
            NetBA_BOLD_5
        },
        ....
    ]
    ```
    '''

    bidInSecond = None # bid price and volume in a second
    askInSecond = None # ask price and volume in a second

    bidInSecondDic = {}
    askInSecondDic = {}

    # bidInSecond = np.empty([])
    # askInSecond
    
    periodEventTime = None #for check package loss

    def __init__(self, symbol) -> None:
        self.symbol = symbol
    
        self.diff = [1,2,5] # diff for calculating askV, bidV
        self.indexDiff=[5] # diff for calculating bidV_ma, askV_ma, NetBA

        self.indicatorData = []
        self.indicatorBlock = 1000 #number of indicator row calculate 1 time
        self.indicatorUnprocessed = 0 #number of indicator still not be processed

        self.ma = 2 * 600 # leng of data for ma calculating
        self.bol_ma = 3 * 3600 # leng of data for bol_ma calculating
        self.maxLeng = self.ma + self.bol_ma + self.indicatorBlock + 100 # max leng of self.indicatorData. must be greater than self.ma and self.bol_m

        # params for testting
        # self.ma = 5 # leng of data for ma calculating
        # self.bol_ma = 10 # leng of data for bol_ma calculating
        # self.maxLeng = 15 # max leng of self.indicatorData. must be greater than self.ma and self.bol_ma
        
        self.columns = self.getDataColumn()
        
        self.currentTime = 0 #save clock time

        self.rawDepthModel = DepthModel('raw_data')
        self.rawKlineModel = KlineModel('raw_data')

        self.unstableTimePoint = 0

        

    def getDeepData(self, startTime, stopTime):
       
        collNames = splitCollName(startTime, stopTime, self.symbol, 'depth')
        returnData = []
        for collName in collNames:
            print(f"{self.symbol} Get deep data from {collName['startTime']} {datetime.fromtimestamp(collName['startTime']/1000, tz=VN_TZ)} to {collName['stopTime']} {datetime.fromtimestamp(collName['stopTime']/1000, tz=VN_TZ)}")
            data = self.rawDepthModel.setCollection(collName['collection']).collection.find({
                "s": self.symbol, 
                "T":{'$gte':collName['startTime'], '$lte':collName['stopTime']}
            })
            returnData += list(data)
        return returnData

    def getPriceData(self, startTime, stopTime):
        collNames = splitCollName(startTime, stopTime, self.symbol, 'kline_1m')
        returnData = []
        for collName in collNames:
            print(f"{self.symbol} Get price data from {collName['startTime']} {datetime.fromtimestamp(collName['startTime']/1000, tz=VN_TZ)} to {collName['stopTime']} {datetime.fromtimestamp(collName['stopTime']/1000, tz=VN_TZ)}")
            data = self.rawDepthModel.setCollection(collName['collection']).collection.find({
                "s": self.symbol, 
                "E":{'$gte':collName['startTime'], '$lte':collName['stopTime']}
            }, {'E':1, 'k.c':1}).sort('E', ASCENDING)
            returnData += list(data)
        pandasData = pd.DataFrame(returnData)
        if(len(pandasData) == 0): return pandasData
        pandasData['timestamp'] = pandasData['E']//1000
        pandasData = pandasData.groupby('timestamp').last()
        return pandasData

    def getData(self, startTime, stopTime):
        '''
        Get deepData and KlineDatas by start and stoptime form raw database.
        '''
        self.priceDatas = self.getPriceData(startTime, stopTime)
        return self.getDeepData(startTime, stopTime)


    def updateOrderBook(self, data):
        '''
        Update volumne of each deepData to orderBook
        '''
        tranTime = Number(data['T'])

        #check loss package
        if(tranTime - self.currentTime > 30000):
            self.unstableTimePoint = int(tranTime/1000)

        self.currentTime = tranTime
        
        for dt in data['b']:
            v = float(dt[1])
            p = float(dt[0])
            self.bidInSecondDic[p] = v
            if(v == 0): del(self.bidInSecondDic[p])
            
                
        for dt in data['a']:
            v = float(dt[1])
            p = float(dt[0])
            self.askInSecondDic[p] = v
            if(v == 0): del(self.askInSecondDic[p])
           
                


    def getCurrentSecond(self):
        return int(self.currentTime/1000)

    def processData(self, data):
        '''
        update raw data to Order book and caluclate if finished a second
        return False if don't need to update to database
        return List of Object to add to database
        '''
        tranTime = Number(data['T'])
        timestamp = int(tranTime/1000) 
        currentSecond = int(self.currentTime/1000)

        if(timestamp - currentSecond > 30):
            self.unstableTimePoint = timestamp
        
        returnData = False

        if(timestamp > currentSecond):
            returnData = self.calculateData()

        self.updateOrderBook(data)

        return returnData

    def calculateData(self):
        '''
        Calculate block data and return block of result data
        '''
        if(len(self.askInSecondDic) == 0 or len(self.bidInSecondDic) == 0): return False
        secondTime = int(self.currentTime/1000)
       
        price = None
        if(secondTime in self.priceDatas.index):
            price = Number(self.priceDatas.loc[secondTime, 'k']['c'])
            
        realTimeData = self.calVolDataNumpy(price)
        realTimeData['symbol'] = self.symbol
        realTimeData['timestamp'] = secondTime

        if(len(self.indicatorData) == 0):
            # self.indicatorData = pd.concat([self.indicatorData, pd.DataFrame([realTimeData], columns=self.columns)])
            self.indicatorData = [realTimeData]
            self.indicatorUnprocessed = 1
        else:
            lastRealTimeData = self.indicatorData[-1]
            if(lastRealTimeData['timestamp'] == secondTime):
                self.indicatorData[-1].update(realTimeData)
                # self.indicatorData.iloc[-1] = pd.Series(lastRealTimeData, index=self.columns)
            else:
                # lastRealTimeData = realTimeData
                # self.indicatorData = pd.concat([self.indicatorData, pd.DataFrame([realTimeData], columns=self.columns)], ignore_index=True)
                # make sure len of realtimeData less than self.maxLeng
                self.indicatorData.append(realTimeData)
                self.indicatorUnprocessed += 1
                if(len(self.indicatorData) > self.maxLeng):
                    self.indicatorData.pop(0)

        self.indicatorData[-1]['stable_time'] = int(self.currentTime/1000) - self.unstableTimePoint
        #after update self.indicatorData calculate index
        if(self.indicatorUnprocessed >= self.indicatorBlock):
            return self.calIndicatorBlock()
        else:
            return False
        

    def getDataColumn(self):
        '''
        Return list of column
        '''
        columns = [
            'symbol',
            'tran_time', 
            'event_time', 
            'ready_time', 
            'stable_time', #stable time of data in second
            'timestamp', 
            'best_ask',
            'best_bid',
            'mid_price'
        ]
        for i,diff in enumerate(self.diff):
            columns.append(f"askV_{diff}")
            columns.append(f"bidV_{diff}")
            if(i == 0):
                columns.append(f"askV_0_{diff}")
                columns.append(f"bidV_0_{diff}")
            else:
                columns.append(f"askV_{self.diff[i-1]}_{diff}")
                columns.append(f"bidV_{self.diff[i-1]}_{diff}")

        for diff in self.indexDiff:
            columns.append(f"bidV_ma_{diff}")
            columns.append(f"askV_ma_{diff}")
            columns.append(f"NetBA_{diff}")
            columns.append(f"NetBA_std_{diff}")
            columns.append(f"NetBA_mean_{diff}")
            columns.append(f"NetBA_BOLU_{diff}")
            columns.append(f"NetBA_BOLD_{diff}")
        return columns

   

    def calVolData(self, closePrice):
        '''
            Calculate bid ask volume by diff for new row
        '''
        self.askInSecond = pd.DataFrame.from_dict(self.askInSecondDic, orient='index', columns=['v'])
        self.bidInSecond = pd.DataFrame.from_dict(self.bidInSecondDic, orient='index', columns=['v'])

        self.bidInSecond = self.bidInSecond.loc[(self.bidInSecond.index < closePrice)]
        self.askInSecond = self.askInSecond.loc[(self.askInSecond.index > closePrice)]

        realTimeData = {}
        bestAsk = self.askInSecond.index.min()
        bestBid = self.bidInSecond.index.max()
        midPrice = (bestAsk + bestBid)/2

        # askDiff = map(lambda x: [x, bestAsk * (100 + x)/100], self.diff)
        # bidDiff = map(lambda x: [x, bestBid * (100 - x)/100], self.diff)

        askDiff = [[x, bestAsk*(1+x/100), self.diff[i-1] if i > 0 else 0, bestAsk*(1+self.diff[i-1]/100) if i > 0 else bestAsk] for i,x in enumerate(self.diff)]
        #askDiff = [[1, 6.065, 0, 6], [2, 6.12, 1, 6.065], [5, 6.31, 2, 6.12]]
        
        bidDiff = [[x, bestBid*(1-x/100), self.diff[i-1] if i > 0 else 0, bestBid*(1-self.diff[i-1]/100) if i > 0 else bestBid] for i,x in enumerate(self.diff)]
        #bidDiff = [[1(diff), 3.96(diff price from best), 0(period diff), 4(period diff price)], [2, 3.92, 1, 3.96], [5, 3.8, 2, 3.92]]
        
        realTimeData['best_ask'] = bestAsk
        realTimeData['best_bid'] = bestBid
        realTimeData['mid_price'] = midPrice

        dataLeng = len(self.indicatorData)

        for diffPrice in askDiff:
            realTimeData[f'askV_{diffPrice[0]}'] = self.askInSecond.loc[(self.askInSecond.index>=bestAsk) & (self.askInSecond.index <= diffPrice[1])]['v'].sum()
            realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] = self.askInSecond.loc[(self.askInSecond.index>=diffPrice[3]) & (self.askInSecond.index <= diffPrice[1])]['v'].sum()
            
            #check missing data
            if(realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] == 0):
                self.unstableTimePoint = int(self.currentTime/1000)
            if(dataLeng > 100):
                if (realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData.iloc[-5, self.indicatorData.columns.get_loc(f'askV_{diffPrice[2]}_{diffPrice[0]}')]
                and realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData.iloc[-10, self.indicatorData.columns.get_loc(f'askV_{diffPrice[2]}_{diffPrice[0]}')]
                and realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData.iloc[-20, self.indicatorData.columns.get_loc(f'askV_{diffPrice[2]}_{diffPrice[0]}')]
                and realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData.iloc[-30, self.indicatorData.columns.get_loc(f'askV_{diffPrice[2]}_{diffPrice[0]}')]
                ):
                    self.unstableTimePoint = int(self.currentTime/1000)
            
        
        for diffPrice in bidDiff:
            realTimeData[f'bidV_{diffPrice[0]}'] = self.bidInSecond.loc[(self.bidInSecond.index>=diffPrice[1]) & (self.bidInSecond.index <= bestBid)]['v'].sum()
            realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] = self.bidInSecond.loc[(self.bidInSecond.index>=diffPrice[1]) & (self.bidInSecond.index <= diffPrice[3])]['v'].sum()
            
            #check missing data
            if(realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] == 0):
                self.unstableTimePoint = int(self.currentTime/1000)
            if(dataLeng > 100):
                if (realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData.iloc[-5, self.indicatorData.columns.get_loc(f'bidV_{diffPrice[2]}_{diffPrice[0]}')]
                and realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData.iloc[-10, self.indicatorData.columns.get_loc(f'bidV_{diffPrice[2]}_{diffPrice[0]}')]
                and realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData.iloc[-20, self.indicatorData.columns.get_loc(f'bidV_{diffPrice[2]}_{diffPrice[0]}')]
                and realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData.iloc[-30, self.indicatorData.columns.get_loc(f'bidV_{diffPrice[2]}_{diffPrice[0]}')]
                ):
                    self.unstableTimePoint = int(self.currentTime/1000)

        return realTimeData


    def calVolDataNumpy(self, closePrice):
        '''
            Calculate bid ask volume by diff for new row
        '''
        self.askInSecond = np.array(list(self.askInSecondDic.items()))
        self.bidInSecond = np.array(list(self.bidInSecondDic.items()))

        if(closePrice is not None):
            self.bidInSecond = self.bidInSecond[self.bidInSecond[:,0] < closePrice]
            self.askInSecond = self.askInSecond[self.askInSecond[:,0] > closePrice]

        realTimeData = {}
        bestAsk = self.askInSecond[:,0].min()
        bestBid = self.bidInSecond[:,0].max()
        midPrice = (bestAsk + bestBid)/2

        askDiff = [[x, bestAsk*(1+x/100), self.diff[i-1] if i > 0 else 0, bestAsk*(1+self.diff[i-1]/100) if i > 0 else bestAsk] for i,x in enumerate(self.diff)]
        #askDiff = [[1, 6.065, 0, 6], [2, 6.12, 1, 6.065], [5, 6.31, 2, 6.12]]
        
        bidDiff = [[x, bestBid*(1-x/100), self.diff[i-1] if i > 0 else 0, bestBid*(1-self.diff[i-1]/100) if i > 0 else bestBid] for i,x in enumerate(self.diff)]
        #bidDiff = [[1(diff), 3.96(diff price from best), 0(period diff), 4(period diff price)], [2, 3.92, 1, 3.96], [5, 3.8, 2, 3.92]]
        
        realTimeData['best_ask'] = bestAsk
        realTimeData['best_bid'] = bestBid
        realTimeData['mid_price'] = midPrice

        dataLeng = len(self.indicatorData)

        for diffPrice in askDiff:

            realTimeData[f'askV_{diffPrice[0]}'] = self.askInSecond[np.where((self.askInSecond[:,0] >= bestAsk) & (self.askInSecond[:,0] <= diffPrice[1]))][:,1].sum()
            if(f'askV_{diffPrice[2]}' in realTimeData):
                realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] = realTimeData[f'askV_{diffPrice[0]}'] - realTimeData[f'askV_{diffPrice[2]}']
            elif(diffPrice[2] == 0):
                realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] = realTimeData[f'askV_{diffPrice[0]}']
            else:
                realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] = self.askInSecond[np.where((self.askInSecond[:,0] >= diffPrice[3]) & (self.askInSecond[:,0] < diffPrice[1]))].sum(axis=0)[1]



            #check missing data
            if(realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] == 0):
                self.unstableTimePoint = int(self.currentTime/1000)
            if(dataLeng > 100):
                if (realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData[-5][f'askV_{diffPrice[2]}_{diffPrice[0]}']
                and realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData[-10][f'askV_{diffPrice[2]}_{diffPrice[0]}']
                and realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData[-20][f'askV_{diffPrice[2]}_{diffPrice[0]}']
                and realTimeData[f'askV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData[-30][f'askV_{diffPrice[2]}_{diffPrice[0]}']
                ):
                    self.unstableTimePoint = int(self.currentTime/1000)
            
        
        for diffPrice in bidDiff:

            realTimeData[f'bidV_{diffPrice[0]}'] = self.bidInSecond[np.where((self.bidInSecond[:,0] >= diffPrice[1]) & (self.bidInSecond[:,0] <= bestBid))][:,1].sum()
            if(f'bidV_{diffPrice[2]}' in realTimeData):
                realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] = realTimeData[f'bidV_{diffPrice[0]}'] - realTimeData[f'bidV_{diffPrice[2]}']
            elif(diffPrice[2] == 0):
                realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] = realTimeData[f'bidV_{diffPrice[0]}']
            else:
                realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] = self.bidInSecond[np.where((self.bidInSecond[:,0] > diffPrice[1]) & (self.bidInSecond[:,0] <= diffPrice[3]))].sum(axis=0)[1]

            #check missing data
            if(realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] == 0):
                self.unstableTimePoint = int(self.currentTime/1000)
            if(dataLeng > 100):
                if (realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData[-5][f'bidV_{diffPrice[2]}_{diffPrice[0]}']
                and realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData[-10][f'bidV_{diffPrice[2]}_{diffPrice[0]}']
                and realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData[-20][f'bidV_{diffPrice[2]}_{diffPrice[0]}']
                and realTimeData[f'bidV_{diffPrice[2]}_{diffPrice[0]}'] == self.indicatorData[-30][f'bidV_{diffPrice[2]}_{diffPrice[0]}']
                ):
                    self.unstableTimePoint = int(self.currentTime/1000)

        return realTimeData

    
    def calIndicator(self):
        
        '''
            Calculate index for bid ask volume for last realtime data
        '''
        realTimeData = {}
        for diff in self.indexDiff:

            realTimeData[f"bidV_ma_{diff}"] = 0
            realTimeData[f"askV_ma_{diff}"] = 0
            realTimeData[f"NetBA_{diff}"] = 0
            
            maData = self.indicatorData[-self.ma:]
            
            if(len(maData) == self.ma): 

                realTimeData[f"bidV_ma_{diff}"] = np.mean([x[f'bidV_{diff}'] for x in maData])
                realTimeData[f"askV_ma_{diff}"] = np.mean([x[f'askV_{diff}'] for x in maData])
                realTimeData[f"NetBA_{diff}"] = realTimeData[f"bidV_ma_{diff}"] - realTimeData[f"askV_ma_{diff}"]
                self.indicatorData[-1][f"NetBA_{diff}"] = realTimeData[f"NetBA_{diff}"] #update NetBA for NetBA_std and NetBA_mean
                
                if(len(self.indicatorData) > self.ma + self.bol_ma):
                    bolMaData = [x[f'NetBA_{diff}'] for x in self.indicatorData[-self.bol_ma:]]
                    if(len(bolMaData) == self.bol_ma): 
                        realTimeData[f"NetBA_mean_{diff}"] = np.mean(bolMaData)
                        realTimeData[f"NetBA_std_{diff}"] = np.std(bolMaData)
                        realTimeData[f"NetBA_BOLU_{diff}"] = realTimeData[f'NetBA_mean_{diff}'] + 2*realTimeData[f'NetBA_std_{diff}']
                        realTimeData[f'NetBA_BOLD_{diff}'] = realTimeData[f'NetBA_mean_{diff}'] - 2*realTimeData[f'NetBA_std_{diff}']
        
        return realTimeData
    
    def calIndicatorBlock(self):
        # print("cal indicator data")
        '''
            Calculate index for bid ask volume for last realtime data
        '''
        maData = pd.DataFrame.from_dict(self.indicatorData)
        for diff in self.indexDiff:
            maData[f"bidV_ma_{diff}"] = maData[f'bidV_{diff}'].rolling(self.ma, min_periods=self.ma).mean()
            maData[f"askV_ma_{diff}"] = maData[f'askV_{diff}'].rolling(self.ma, min_periods=self.ma).mean()
            maData[f"NetBA_{diff}"] = maData[f"bidV_ma_{diff}"] - maData[f"askV_ma_{diff}"]
            maData[f"NetBA_mean_{diff}"] = maData[f'NetBA_{diff}'].rolling(self.bol_ma, min_periods=self.bol_ma).mean()
            maData[f"NetBA_std_{diff}"] = maData[f'NetBA_{diff}'].rolling(self.bol_ma, min_periods=self.bol_ma).std()
            maData[f"NetBA_BOLU_{diff}"] = maData[f'NetBA_mean_{diff}'] + 2*maData[f'NetBA_std_{diff}']
            maData[f'NetBA_BOLD_{diff}'] = maData[f'NetBA_mean_{diff}'] - 2*maData[f'NetBA_std_{diff}']

        self.indicatorData = maData.to_dict(orient='records')
        returnData = self.indicatorData[-self.indicatorUnprocessed:]
        self.indicatorUnprocessed = 0
        return returnData
        # print(f"cal indicator block in {dt.now().timestamp()*1000000 - startTime}ns")        
                
        
        



        



    


    


                
    


    
