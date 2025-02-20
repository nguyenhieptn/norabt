from datetime import datetime, timedelta, tzinfo
from heapq import merge
from dateutil import tz
from math import floor
import os

from django.core.management.base import BaseCommand
import requests
from helper.Data import getKline
from helper.Defaults import *

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from plotly.subplots import make_subplots

from models.Wrappers.backtest_wrapper import LabAccountWrapper, LabOrderWrapper, LabResultsWrapper
from models.Mongo.BusdModel import BusdModel
from models.Mongo.OrderbookModel import Order_bookModel
from models.Mongo.CandleModel import Candle_Model
from pymongo import ASCENDING, DESCENDING

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')



class Command(BaseCommand):
    help = 'Generate testnet chart'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        

    def add_arguments(self, parser):
        parser.add_argument("-s","--symbol", nargs='?', default=None, type=str)
        parser.add_argument("-a","--account", nargs='?', default=None, type=int)

    
    def handle(self, *args, **options):
        self.symbol = options.get('symbol').upper()
        self.account = options.get('account')

        accountObj = list(LabAccountWrapper().filter({LabAccountWrapper.lab_account_id: self.account}))
        if(len(accountObj) == 0):
            raise Exception('No account')
        self.accountObj = accountObj[0]

        databaseName = self.accountObj.lab_account_db
        if(databaseName is None or databaseName == ''): databaseName = 'backtest_data'

        self.fileName = f'statistic_{self.account}_{self.symbol}.csv'
        print(f"Generate Statistic for account:{self.fileName}")

        self.busdModel = BusdModel(databaseName, 'busd')
        self.orderbookModel = Order_bookModel(databaseName, 'order_book')
        self.candleModels = Candle_Model(databaseName)

        self.kline2h_btc = None
        self.data = {}

        symbols = self.getSymbols()
        listPandas = []
        for symbol in symbols:
            listPandas.append(self.getData(symbol))
            # break
        
        result = pd.concat(listPandas)

        path = f'./frontend/build/statistic/{self.fileName}'
        result.to_csv(path)


        
        
        # self.getData()

    def getSymbols(self):
        symbols = list(LabResultsWrapper().filter({
            LabResultsWrapper.lab_result_account: self.account,
        }).values(LabResultsWrapper.lab_result_symbol).distinct())
        symbols = pd.DataFrame.from_records(symbols)
        return symbols['lab_result_symbol'].to_list()
        

    def getData(self, symbol):
        print(f"{symbol} get Lab orders")
        result = list(LabOrderWrapper().filter({
            LabOrderWrapper.lab_order_account: self.account,
            LabOrderWrapper.lab_order_symbol: symbol,
        }).order_by(LabOrderWrapper.lab_order_time).values())
        orders = pd.DataFrame.from_records(result)

        print(f"{symbol} get Lab result")
        result = list(LabResultsWrapper().filter({
            LabResultsWrapper.lab_result_account: self.account,
            LabResultsWrapper.lab_result_symbol: symbol,
        }).order_by(LabResultsWrapper.lab_result_chart).values())
        positions = pd.DataFrame.from_records(result)
        if(len(positions) == 0): return positions

        positions = positions.merge(orders, how='left', left_on=LabResultsWrapper.lab_result_id, right_on=LabOrderWrapper.lab_order_action)
        positions = positions.groupby(LabResultsWrapper.lab_result_id).first().reset_index()
        positions['timestamp'] = positions[LabOrderWrapper.lab_order_time]//1000

        #statistic kline 4h 1d heigh
        print(f"{symbol} get candle 4h")
        data = list(self.candleModels.setCollection(f"candle_4h").collection.find({
            Candle_Model.symbol: symbol,
            Candle_Model.timestamp: {"$in":positions['timestamp'].to_list()}
        }))
        kline4h = pd.DataFrame.from_records(data).add_suffix('_4h')
        if(len(kline4h) > 0):
            positions = positions.merge(kline4h, how='left', left_on='timestamp', right_on='timestamp_4h')
            positions['kline_heigh_4h'] = (positions['close_4h'] - positions['open_4h']) / positions['open_4h']

        print(f"{symbol} get candle 1d")
        data = list(self.candleModels.setCollection(f"candle_1d").collection.find({
            Candle_Model.symbol: symbol,
            Candle_Model.timestamp: {"$in":positions['timestamp'].to_list()}
        }))
        kline1d = pd.DataFrame.from_records(data).add_suffix('_1d')
        if(len(kline1d) > 0):
            positions = positions.merge(kline1d, how='left', left_on='timestamp', right_on='timestamp_1d')
            positions['kline_heigh_1d'] = (positions['close_1d'] - positions['open_1d']) / positions['open_1d']

        #statics wma45 btc
        positions = self.addWma45(positions, '2h', 'BTCUSDT')
        positions = self.addWma45(positions, '2h', symbol, '2h')
        

        status = {
            0 : "PENDING",
            1 : "MATCHED",
            2 : "TAKEPROFIT",
            3 : "STOPLOSS",
            4 : "CANCLE",
            5 : "STOP_PENDING",
            6 : "ENTER_WAITTING",
            7 : "MATCHED_PART",
            8 : "PHASE_PENDING",
            9 : "RELEASE_WAITTING",
            10 : "RELEASE_PENDING",
        }

        positions[LabResultsWrapper.lab_result_status] = positions[LabResultsWrapper.lab_result_status].map(status)
        positions['timestamp'] = pd.to_datetime(positions['timestamp'].to_list(), unit='s', utc=True).tz_convert(VN_TZ)
        positions[LabResultsWrapper.lab_result_chart] = pd.to_datetime(positions[LabResultsWrapper.lab_result_chart].to_list(), unit='ms', utc=True).tz_convert(VN_TZ)

        getColumns = [
            'timestamp',
            LabResultsWrapper.lab_result_type,
            LabResultsWrapper.lab_result_eventprofit,
            LabResultsWrapper.lab_result_symbol,
        ]
        if 'kline_heigh_4h' in positions.columns: getColumns.append('kline_heigh_4h')
        if 'kline_heigh_1d' in positions.columns: getColumns.append('kline_heigh_1d')
        
        

        if 'macdh_wma_45_rsi_2h_BTCUSDT_color' in positions.columns: getColumns.append('macdh_wma_45_rsi_2h_BTCUSDT_color')
        if 'macdh_wma_45_rsi_2h_BTCUSDT_p1_color' in positions.columns: getColumns.append('macdh_wma_45_rsi_2h_BTCUSDT_p1_color')
        if f'macdh_wma_45_rsi_2h_color' in positions.columns: getColumns.append(f'macdh_wma_45_rsi_2h_color')
        if f'macdh_wma_45_rsi_2h_p1_color' in positions.columns: getColumns.append(f'macdh_wma_45_rsi_2h_p1_color')


        positions = positions[getColumns]

        return positions



    
        
        
           
        # data = list(self.candleModels.setCollection(f"candle_{frame}").collection.find({
        #     Candle_Model.symbol: self.symbol,
        #     Candle_Model.is_close: 1,
        #     Candle_Model.close_time: {"$gte": startOfDay * 1000, "$lte": endOfDay * 1000}
        # }))
        # self.data[dataType] = pd.DataFrame.from_records(data)
    
    
        # frame = dataType.split('_')[1]
        # data = list(self.candleModels.setCollection(f"candle_{frame}").collection.find({
        #     Candle_Model.symbol: self.symbol,
        #     Candle_Model.timestamp: {"$gte": startOfDay, "$lte": endOfDay}
        # }))

    def addWma45(self, positions, frame, symbol, suffix = None):
        key = f'candle_{frame}_{symbol}'
        if(suffix is None): suffix = f'{frame}_{symbol}'
        if(not isset(self.data, key)):
            print(f"{symbol} get candle {frame} full of")
            data = list(self.candleModels.setCollection(f"candle_{frame}").collection.find({
                Candle_Model.symbol: symbol,
            }, {
                'timestamp': 1,
                'wma_45_rsi':1,
                'macdh_wma_45_rsi':1,
                'is_close':1
            }))
            
            kline2h = pd.DataFrame.from_records(data).add_suffix(f'_{suffix}')
            if(len(kline2h) > 0):
                c=kline2h[kline2h[f'is_close_{suffix}']==1][[f'timestamp_{suffix}', f'macdh_wma_45_rsi_{suffix}']].rename(columns={f'macdh_wma_45_rsi_{suffix}': f'macdh_wma_45_rsi_{suffix}_p1'})
                c[f'macdh_wma_45_rsi_{suffix}_p2'] = c[f'macdh_wma_45_rsi_{suffix}_p1'].shift()
                
                kline2h=kline2h.merge(c, how='left', on=f'timestamp_{suffix}')
                kline2h[f'macdh_wma_45_rsi_{suffix}_p1'] = kline2h[f'macdh_wma_45_rsi_{suffix}_p1'].pad()
                kline2h[f'macdh_wma_45_rsi_{suffix}_p2'] = kline2h[f'macdh_wma_45_rsi_{suffix}_p2'].pad()

                kline2h.loc[(kline2h[f'macdh_wma_45_rsi_{suffix}'] < 0) & (kline2h[f'macdh_wma_45_rsi_{suffix}_p1'] >= kline2h[f'macdh_wma_45_rsi_{suffix}']), f'macdh_wma_45_rsi_{suffix}_color'] = 2 #'Đỏ đậm'
                kline2h.loc[(kline2h[f'macdh_wma_45_rsi_{suffix}'] < 0) & (kline2h[f'macdh_wma_45_rsi_{suffix}_p1'] < kline2h[f'macdh_wma_45_rsi_{suffix}']), f'macdh_wma_45_rsi_{suffix}_color'] = 3 #'Đỏ nhạt'
                kline2h.loc[(kline2h[f'macdh_wma_45_rsi_{suffix}'] >= 0) & (kline2h[f'macdh_wma_45_rsi_{suffix}_p1'] <= kline2h[f'macdh_wma_45_rsi_{suffix}']), f'macdh_wma_45_rsi_{suffix}_color'] = 0 #'Xanh đậm'
                kline2h.loc[(kline2h[f'macdh_wma_45_rsi_{suffix}'] >= 0) & (kline2h[f'macdh_wma_45_rsi_{suffix}_p1'] > kline2h[f'macdh_wma_45_rsi_{suffix}']), f'macdh_wma_45_rsi_{suffix}_color'] = 1 #'Xanh nhạt'
                kline2h.loc[(kline2h[f'macdh_wma_45_rsi_{suffix}_p1'] < 0) & (kline2h[f'macdh_wma_45_rsi_{suffix}_p2'] >= kline2h[f'macdh_wma_45_rsi_{suffix}_p1']), f'macdh_wma_45_rsi_{suffix}_p1_color'] = 2 #'Đỏ đậm'
                kline2h.loc[(kline2h[f'macdh_wma_45_rsi_{suffix}_p1'] < 0) & (kline2h[f'macdh_wma_45_rsi_{suffix}_p2'] < kline2h[f'macdh_wma_45_rsi_{suffix}_p1']), f'macdh_wma_45_rsi_{suffix}_p1_color'] = 3 #'Đỏ nhạt'
                kline2h.loc[(kline2h[f'macdh_wma_45_rsi_{suffix}_p1'] >= 0) & (kline2h[f'macdh_wma_45_rsi_{suffix}_p2'] <= kline2h[f'macdh_wma_45_rsi_{suffix}_p1']), f'macdh_wma_45_rsi_{suffix}_p1_color'] = 0 #'Xanh đậm'
                kline2h.loc[(kline2h[f'macdh_wma_45_rsi_{suffix}_p1'] >= 0) & (kline2h[f'macdh_wma_45_rsi_{suffix}_p2'] > kline2h[f'macdh_wma_45_rsi_{suffix}_p1']), f'macdh_wma_45_rsi_{suffix}_p1_color'] = 1 #'Xanh nhạt'

            self.data[key] = kline2h

        if(len(self.data[key]) > 0):
            positions = positions.merge(self.data[key], how='left', left_on='timestamp', right_on=f'timestamp_{suffix}') 
        return positions

        


        
        
    

        





        

        

        







        

        


    