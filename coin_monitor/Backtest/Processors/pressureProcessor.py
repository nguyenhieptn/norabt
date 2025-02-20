
from math import floor
from threading import Thread
from time import sleep, time
import orjson
from datetime import datetime, timedelta
import requests
from helper.Indicator import rsi, ema, wma
from helper.Defaults import *
from helper.Data import *
from pymongo import ASCENDING, DESCENDING

import pandas as pd
import numpy as np

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')


class pressureProcessor():

    def __init__(self, symbol) -> None:
        self.symbol = symbol
        self.indicator = [
            {"indicator":"mean", "source":"BP", "params": 600},
            {"indicator":"mean", "source":"AP", "params": 600},
            {"indicator":"mean", "source":"ABP", "params": 600},
            {"indicator":"mean", "source":"BAP", "params": 600},
            {"indicator":"ema", "source":"ABP", "params": 600},
            {"indicator":"ema", "source":"BAP", "params": 600},
            {"indicator":"mean", "source":"ABP", "params": 300},
            {"indicator":"mean", "source":"BAP", "params": 300},
            {"indicator":"ema", "source":"ABP", "params": 300},
            {"indicator":"ema", "source":"BAP", "params": 300},
            {"indicator":"mean", "source":"ABP", "params": 60},
            {"indicator":"mean", "source":"BAP", "params": 60},
            {"indicator":"ema", "source":"ABP", "params": 60},
            {"indicator":"ema", "source":"BAP", "params": 60},
        ]
        self.data = None
        self.maxLeng = 500
        self.priceIndex = None
        self.price = None

    def getPriceData(self, startTime, stopTime):

        collNames = splitCollName(startTime, stopTime, self.symbol, 'kline_1m')

        returnData = []
        for collName in collNames:
            print(f"{self.symbol} Get price data from {collName['startTime']} {datetime.fromtimestamp(collName['startTime']/1000, tz=VN_TZ)} to {collName['stopTime']} {datetime.fromtimestamp(collName['stopTime']/1000, tz=VN_TZ)}")
            if(collName['model'] is None): continue
            data = collName['model'].setCollection(collName['collection']).collection.find({
                "s": self.symbol, 
                "E":{'$gte':collName['startTime'], '$lte':collName['stopTime']}
            }, {'E':1, 'k.c':1}).sort('E', ASCENDING)
            returnData += list(data)

        pandasData = pd.DataFrame(returnData)
        if(len(pandasData) == 0): return pandasData
        pandasData['timestamp'] = pandasData['E']//1000
        pandasData = pandasData.groupby('timestamp').last()
        self.priceIndex = pandasData
        return pandasData
        
    def getData(self, startTime, stopTime):

        self.getPriceData(startTime, stopTime)
        collNames = splitCollName(startTime, stopTime, self.symbol, 'depth20')

        returnData = []
        for collName in collNames:
            
            print(f"{self.symbol} Get depth20 data from {collName['startTime']} {datetime.fromtimestamp(collName['startTime']/1000, tz=VN_TZ)} to {collName['stopTime']} {datetime.fromtimestamp(collName['stopTime']/1000, tz=VN_TZ)}")
            
            if(collName['model'] is None): continue
            collName['model'].setCollection(collName['collection']).collection.create_index([('E', ASCENDING)])
            datas = collName['model'].setCollection(collName['collection']).collection.find({
                "E":{'$gte':collName['startTime'], '$lte':collName['stopTime']}
            }).sort('E', ASCENDING)



            leng = datas.count()

            for dt in datas:
                #process price
                timestamp = Number(dt['E'])//1000
                if(timestamp in self.priceIndex.index):
                    self.price = float(self.priceIndex.loc[timestamp]['k']['c'])
                
                if(self.price is None): continue

                bids = np.array(dt['b'], dtype=float)
                asks = np.array(dt['a'], dtype=float)
                if(len(bids) == 0 or len(asks) == 0): continue
                bestBid = float(bids[0,0])
                bestAsk = float(asks[0,0])
                price = self.price
                if(price > bestAsk or price < bestBid):
                    continue
                
                # if(price == bestBid):
                #     bids[0,0] = bids[1,0]
                    
                # if(price == bestAsk): 
                #     asks[0,0] = asks[1,0]

                VA = asks[:,1].sum()
                VB = bids[:,1].sum()

                bids[:,0] = price - bids[:,0]
                asks[:,0] = asks[:,0] - price

                maxdiff = max(bids[:,0].max(), asks[:,0].max())

                bids[:,0] = 1 - (0.99 * bids[:,0])/maxdiff
                asks[:,0] = 1 - (0.99 * asks[:,0])/maxdiff

                

                bpres = bids[:,0] * bids[:,1]
                apres = asks[:,0] * asks[:,1]

                BP = bpres.sum()
                AP = apres.sum()

                BAP = BP/AP
                ABP = AP/BP

                # if(BAP > 100 or ABP > 100):
                #     print("===========")
                #     print(dt['b'])
                #     print(dt['a'])
                #     print(bids[:,0])
                #     print(asks[:,0])
                #     print(bpres)
                #     print(apres)
                #     print(BP)
                #     print(AP)


                returnData.append({
                    'symbol': self.symbol,
                    'event_time': Number(dt['E']),
                    'Price': price,
                    'BP': BP,
                    'AP': AP,
                    'ABP': ABP,
                    'BAP': BAP,
                    'VA': VA,
                    'VB': VB

                })

                print(f"Processed: {len(returnData)}/{leng}", end="\r")


        pandasData = pd.DataFrame(returnData)
        if(len(pandasData) == 0): return pandasData
        pandasData['timestamp'] = pandasData['event_time']//1000
        pandasData = pandasData.groupby('timestamp').last().reset_index()
        return pandasData


    


    def calIndicatorBlock(self, data:pd.DataFrame):

        dataLeng = len(data)
        if(dataLeng == 0): return []
        if(self.data is None):
            self.data = data
        else:
            self.data = pd.concat([self.data[-self.maxLeng:], data])
        
        for indicator in self.indicator:
            indicatorType = indicator['indicator']
            if(indicatorType == 'mean'):
                params = indicator['params']
                source = indicator['source']
                name = get(indicator, 'name', f"{indicatorType}_{params}_{source}")
                self.data[name] = self.data[source].rolling(params).mean()
            if(indicatorType == 'ema'):
                params = indicator['params']
                source = indicator['source']
                name = get(indicator, 'name', f"{indicatorType}_{params}_{source}")
                self.data[name] = self.data[source].ewm(span=params, adjust=False, min_periods=params).mean()
            if(indicatorType == 'iema'):
                params = indicator['params']
                source = indicator['source']
                name = get(indicator, 'name', f"{indicatorType}_{params}_{source}")
                meanName = f"ema_{params}_{source}"
                self.data[name] = self.data[source]/self.data[meanName]

        return self.data[-dataLeng:].to_dict(orient='records')
        


        

    

            










    


    


                
    


    
