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

from models.backtest import LabAccount

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')



class Command(BaseCommand):
    help = 'Generate testnet chart'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        

    def add_arguments(self, parser):
        today = datetime.today()
        day = today.strftime("%Y_%m_%d")
        parser.add_argument("-s","--symbol", nargs='?', required=True, default=None, type=str)
        parser.add_argument("-d","--day", nargs='?', default=day, type=str)
        parser.add_argument("-a","--account", nargs='?', default=None, type=int)
        parser.add_argument("-t", "--type", nargs='?', default=1, type=int)

    
    def handle(self, *args, **options):
        self.symbol = options.get('symbol').upper()
        self.day = options.get('day')
        self.account = options.get('account')
        self.type = options.get('type')

        accountObj = list(LabAccountWrapper().filter({LabAccountWrapper.lab_account_id: self.account}))
        if(len(accountObj) == 0):
            raise Exception('No account')
        self.accountObj = accountObj[0] #type: LabAccount

        self.fileName = f'backtest_{self.account}_{self.symbol}_{self.day}.html'
        print(f"Generate Chart for account:{self.account} {self.symbol} {self.day}")
        
        databaseName = self.accountObj.lab_account_db
        if(databaseName is None or databaseName == ''): databaseName = 'backtest_data'

        self.busdModel = BusdModel(databaseName, 'busd')
        self.busdModel1m = BusdModel('backtest_data_1m', 'busd')
        self.orderbookModel = Order_bookModel(databaseName, 'order_book')
        self.candleModels = Candle_Model(databaseName)
        
        self.createChart()
        

    def getData(self, dataType, symbol=None):

        if(symbol is None): symbol = self.symbol
        key = f"{dataType}_{symbol}"
        if(isset(self.data, key)): return self.data[key]

        date = datetime.strptime(self.day, '%Y_%m_%d').replace(tzinfo=VN_TZ)
        startOfDay = int(date.timestamp())
        endOfDay = startOfDay + 86400
        if(self.accountObj.lab_account_db == 'backtest_data_1m'):
            startOfDay -= 2 * 86400
            endOfDay += 2 * 86400
        curentTime = int(datetime.now().timestamp())
        if(endOfDay > curentTime): endOfDay = curentTime
        print(f"Get data {dataType} from {startOfDay} to {endOfDay}")

        if(dataType == 'OrderBook'):
            #get orderbook data
            result = list(self.orderbookModel.collection.find({
                Order_bookModel.symbol: symbol,
                Order_bookModel.timestamp : {"$gte":startOfDay, "$lte":endOfDay}
            }, {
                Order_bookModel.timestamp : 1,
                Order_bookModel.mid_price: 1,
                Order_bookModel.best_ask : 1,
                Order_bookModel.best_bid: 1,
                Order_bookModel.bidV_ma_5 : 1,
                Order_bookModel.askV_ma_5: 1,
                Order_bookModel.NetBA_5: 1,
                Order_bookModel.NetBA_BOLD_5: 1,
                Order_bookModel.NetBA_BOLU_5: 1,
                Order_bookModel.askV_0_1: 1,
                Order_bookModel.askV_1_2: 1,
                Order_bookModel.askV_2_5: 1,
                Order_bookModel.bidV_0_1: 1,
                Order_bookModel.bidV_1_2: 1,
                Order_bookModel.bidV_2_5: 1,
                Order_bookModel.stable_time: 1,
            }
            ).sort('timestamp', ASCENDING))

            self.data[key] = []
            if(len(result) > 0):
                self.data[key] = pd.DataFrame.from_records(result).drop_duplicates(subset=['timestamp'], keep='last').set_index(Order_bookModel.timestamp).reindex(range(startOfDay, endOfDay))
        
        if(dataType == 'BUSD'):
            #get busd data
           
            result = list(self.busdModel.collection.find({
                BusdModel.symbol: symbol,
                BusdModel.timestamp : {"$gte":startOfDay, "$lte":endOfDay}
            }, {
                BusdModel.timestamp: 1,
                BusdModel.stable_time: 1,
                BusdModel.BU: 1,
                BusdModel.SD: 1,
                BusdModel.BU_60_1200: 1,
                BusdModel.SD_60_1200: 1,
                BusdModel.BU_240_4800: 1,
                BusdModel.SD_240_4800: 1,
                BusdModel.BU_60: 1,
                BusdModel.BU_240: 1,
                BusdModel.SD_60: 1,
                BusdModel.SD_240: 1,
                BusdModel.BUSD_240_4800_5_MACDh: 1,
                BusdModel.BUSD_240_4800_5_MACD: 1,
                # BusdModel.BU_240_4800_5_MACDh: 1,
                # BusdModel.BU_240_4800_5_MACD: 1,
                # BusdModel.SD_240_4800_5_MACDh: 1,
                # BusdModel.SD_240_4800_5_MACD: 1,
                # BusdModel.BUSD_240_4800_5_fast: 1,
                # BusdModel.BUSD_240_4800_5_slow: 1,
                # BusdModel.BUSD_240_4800_5_smooth: 1,
                # BusdModel.BUSD_240_4800: 1,
                BusdModel.BUSD_60_1200_5_MACDh: 1,
                BusdModel.BUSD_60_1200_5_MACD: 1,
                # BusdModel.BU_60_1200_5_MACDh: 1,
                # BusdModel.BU_60_1200_5_MACD: 1,
                # BusdModel.SD_60_1200_5_MACDh: 1,
                # BusdModel.SD_60_1200_5_MACD: 1,
                # BusdModel.BUSD_60_1200_5_fast: 1,
                # BusdModel.BUSD_60_1200_5_slow: 1,
                # BusdModel.BUSD_60_1200_5_smooth: 1,
                # BusdModel.BUSD_60_1200: 1,
                BusdModel.BUSD_240_4800_60_MACDh: 1,
                BusdModel.BUSD_240_4800_60_MACD: 1,
                BusdModel.BUSD_60_1200_60_MACDh: 1,
                BusdModel.BUSD_60_1200_60_MACD: 1,
                BusdModel.BUSD_1440_28800_60_MACDh: 1,
                BusdModel.BUSD_1440_28800_60_MACD: 1,
                BusdModel.BUSD_15_300_3_MACD: 1,
                BusdModel.BUSD_15_300_3_MACDh: 1,
                BusdModel.BUSD_60_1200_3_MACD: 1,
                BusdModel.BUSD_60_1200_3_MACDh: 1,
            }).sort('timestamp', ASCENDING))
                
            self.data[key] = []
            if(len(result) > 0):
                self.data[key] = pd.DataFrame.from_records(result).drop_duplicates(subset=['timestamp'], keep='last')

        if(dataType == 'BUSD_1m'):
            #get busd data
           
            result = list(self.busdModel1m.collection.find({
                BusdModel.symbol: symbol,
                BusdModel.timestamp : {"$gte":startOfDay, "$lte":endOfDay}
            }, {
                BusdModel.timestamp: 1,
                BusdModel.stable_time: 1,
                BusdModel.BU: 1,
                BusdModel.SD: 1,
                BusdModel.BU_60_1200: 1,
                BusdModel.SD_60_1200: 1,
                BusdModel.BU_240_4800: 1,
                BusdModel.SD_240_4800: 1,
                BusdModel.BU_60: 1,
                BusdModel.BU_240: 1,
                BusdModel.SD_60: 1,
                BusdModel.SD_240: 1,
                BusdModel.BUSD_240_4800_5_MACDh: 1,
                BusdModel.BUSD_240_4800_5_MACD: 1,
                # BusdModel.BU_240_4800_5_MACDh: 1,
                # BusdModel.BU_240_4800_5_MACD: 1,
                # BusdModel.SD_240_4800_5_MACDh: 1,
                # BusdModel.SD_240_4800_5_MACD: 1,
                # BusdModel.BUSD_240_4800_5_fast: 1,
                # BusdModel.BUSD_240_4800_5_slow: 1,
                # BusdModel.BUSD_240_4800_5_smooth: 1,
                # BusdModel.BUSD_240_4800: 1,
                BusdModel.BUSD_60_1200_5_MACDh: 1,
                BusdModel.BUSD_60_1200_5_MACD: 1,
                # BusdModel.BU_60_1200_5_MACDh: 1,
                # BusdModel.BU_60_1200_5_MACD: 1,
                # BusdModel.SD_60_1200_5_MACDh: 1,
                # BusdModel.SD_60_1200_5_MACD: 1,
                # BusdModel.BUSD_60_1200_5_fast: 1,
                # BusdModel.BUSD_60_1200_5_slow: 1,
                # BusdModel.BUSD_60_1200_5_smooth: 1,
                # BusdModel.BUSD_60_1200: 1,
                BusdModel.BUSD_240_4800_60_MACDh: 1,
                BusdModel.BUSD_240_4800_60_MACD: 1,
                BusdModel.BUSD_60_1200_60_MACDh: 1,
                BusdModel.BUSD_60_1200_60_MACD: 1,
                BusdModel.BUSD_1440_28800_60_MACDh: 1,
                BusdModel.BUSD_1440_28800_60_MACD: 1,
                BusdModel.BUSD_15_300_3_MACD: 1,
                BusdModel.BUSD_15_300_3_MACDh: 1,
                BusdModel.BUSD_60_1200_3_MACD: 1,
                BusdModel.BUSD_60_1200_3_MACDh: 1,
            }).sort('timestamp', ASCENDING))
                
            self.data[key] = []
            if(len(result) > 0):
                self.data[key] = pd.DataFrame.from_records(result).drop_duplicates(subset=['timestamp'], keep='last')

        if(dataType == 'Order'):
            result = list(LabOrderWrapper().filter({
                LabOrderWrapper.lab_order_account: self.account,
                LabOrderWrapper.lab_order_symbol: symbol,
                LabOrderWrapper.lab_order_time + "__gte": startOfDay * 1000,
                LabOrderWrapper.lab_order_time + "__lte": endOfDay * 1000
            }).order_by(LabOrderWrapper.lab_order_time).values())
            self.data[key] = pd.DataFrame.from_records(result)

        if(dataType == 'Position'):
            result = list(LabResultsWrapper().filter({
                LabResultsWrapper.lab_result_account: self.account,
                LabResultsWrapper.lab_result_symbol: symbol,
                LabResultsWrapper.lab_result_chart + "__gte": startOfDay * 1000,
                LabResultsWrapper.lab_result_chart + "__lte": endOfDay * 1000
            }).order_by(LabResultsWrapper.lab_result_chart).values())
            self.data[key] = pd.DataFrame.from_records(result)
        
        if(dataType.startswith('candle')):
            frame = dataType.split('_')[1]
            data = list(self.candleModels.setCollection(f"candle_{frame}").collection.find({
                Candle_Model.symbol: symbol,
                Candle_Model.is_close: 1,
                Candle_Model.close_time: {"$gte": startOfDay * 1000, "$lte": endOfDay * 1000}
            }))
            self.data[key] = pd.DataFrame.from_records(data)
        
        if(dataType.startswith('detailcandle')):
            frame = dataType.split('_')[1]
            data = list(self.candleModels.setCollection(f"candle_{frame}").collection.find({
                Candle_Model.symbol: symbol,
                Candle_Model.timestamp: {"$gte": startOfDay, "$lte": endOfDay}
            }))
            self.data[key] = pd.DataFrame.from_records(data)


        return self.data[key]
        
    
    def createChart(self):

        if(self.type == 1):
            charts = [
                {
                    "type": "Price",
                    "heigh": 200,
                    "title": "Price"
                },

                {
                    "type": "BidAsk",
                    "heigh": 200,
                    "params": [5],
                    "title": "OrderBook"
                },

                {
                    "type": "BidAskDis",
                    "heigh": 200,
                    "params": ['bidV'],
                    "title": "BID Distribution"
                },

                {
                    "type": "BidAskDis",
                    "heigh": 200,
                    "params": ['askV'],
                    "title": "ASK Distribution"
                },

                {
                    "type": "BUSD",
                    "heigh": 200,
                    "params": [60, 1200],
                    "title": "BUSD_60_1200"
                },

                {
                    "type": "BUSDMacd",
                    "heigh": 100,
                    "params": [60, 1200],
                    "title": "BUSD_60_1200_MACD"
                },

                {
                    "type": "BUSD",
                    "heigh": 200,
                    "params": [240, 4800],
                    "title": "BUSD_240_4800"
                },

                {
                    "type": "BUSDMacd",
                    "heigh": 100,
                    "params": [240, 4800],
                    "title": "BUSD_240_4800_MACD"
                },
            ]

        if(self.type == 2):
            charts = [
                {
                    "type": "Price",
                    "heigh": 200,
                    "title": "Price"
                },

                {
                    "type": "BUSDOrigin",
                    "heigh": 100,
                    "params": [],
                    "title": "BUSD 1s"
                }, 

                {
                    "type": "BUSDMacd",
                    "heigh": 100,
                    "params": [15, 300, 3],
                    "title": "BUSD_15_300_3_MACD"
                }, 

                {
                    "type": "BUSDMacd",
                    "heigh": 100,
                    "params": [240, 4800, 60],
                    "title": "BUSD_240_4800_60_MACD"
                }, 

                {
                    "type": "BUSDMacd",
                    "heigh": 100,
                    "params": [60, 1200, 60],
                    "title": "BUSD_60_1200_60_MACD"
                }, 


                {
                    "type": "BUSDMacd",
                    "heigh": 100,
                    "params": [1440, 28800, 60],
                    "title": "BUSD_1440_28800_60_MACD"
                }, 

            
            ]

        if(self.type == 3):
            charts = [
                {
                    "type": "Price",
                    "heigh": 200,
                    "title": "Price"
                },

                # {
                #     "type": "BUSDOrigin",
                #     "heigh": 100,
                #     "params": [],
                #     "title": "BUSD 1s"
                # }, 

                {
                    "type": "BUSDMacd",
                    "heigh": 100,
                    "params": [60, 1200, 3],
                    "title": "BUSD_60_1200_3_MACD"
                }, 
                {
                    "type": "Wma45",
                    "heigh": 100,
                    "params": ['2h', self.symbol],
                    "title": "WMA45 2H"
                }, 
                {
                    "type": "MacdhWma45",
                    "heigh": 100,
                    "params": ['2h', self.symbol],
                    "title": "MACDH WMA45 2H"
                }, 
                {
                    "type": "Wma45",
                    "heigh": 100,
                    "params": ['2h', 'BTCUSDT'],
                    "title": "BTCUSDT WMA45 2H"
                }, 
                {
                    "type": "MacdhWma45",
                    "heigh": 100,
                    "params": ['2h', 'BTCUSDT'],
                    "title": "BTCUSDT MACDH WMA45 2H"
                }, 
                {
                    "type": "Wma45",
                    "heigh": 100,
                    "params": ['4h', 'BTCUSDT'],
                    "title": "BTCUSDT WMA45 4H"
                }, 
                {
                    "type": "MacdhWma45",
                    "heigh": 100,
                    "params": ['4h', 'BTCUSDT'],
                    "title": "BTCUSDT MACDH WMA45 4H"
                }, 
                
                # {
                #     "type": "BUSDMacd1m",
                #     "heigh": 100,
                #     "params": [60, 1200, 3],
                #     "title": "BUSD_60_1200_3_MACD 1m"
                # }, 

                # {
                #     "type": "CandlePrice",
                #     "heigh": 100,
                #     "params": ['4h'],
                #     "title": "Kline 4H"
                # },
                # {
                #     "type": "CandlePrice",
                #     "heigh": 100,
                #     "params": ['1d'],
                #     "title": "Kline 1D"
                # }

            ]

        chartsPd = pd.DataFrame(charts)

        # Create figure
        self.fig = make_subplots(
            rows= len(chartsPd), 
            cols=1, 
            shared_xaxes=True, 
            row_heights= chartsPd['heigh'].to_list(),
            vertical_spacing=0.02,
            subplot_titles= chartsPd['title'].to_list(),
            # specs=[
            #     [{"secondary_y": False}], 
            #     [{"secondary_y": False}], 
            #     [{"secondary_y": False}], 
            #     [{"secondary_y": False}],
            #     [{"secondary_y": False}], 
            #     [{"secondary_y": False}]
            # ]
            )

        self.data = {}
       
        for row, ch in enumerate(charts):
            if(ch['type'] == 'Price'):
                self.drawPrice(row + 1)
            elif(ch['type'] == 'BidAsk'):
                self.drawBidAsk(row + 1, *ch['params'])
            elif(ch['type'] == 'BUSD'):
                self.drawBUSD(row + 1, *ch['params'])
            elif(ch['type'] == 'BUSDOrigin'):
                self.drawOriginBUSD(row + 1, *ch['params'])
            elif(ch['type'] == 'BUSDMacd'):
                self.drawBusdMacd(row + 1, *ch['params']) 
            elif(ch['type'] == 'BUSDMacd1m'):
                self.drawBusdMacd1m(row + 1, *ch['params']) 
            elif(ch['type'] == 'BidAskDis'):
                self.drawBidAskDis(row + 1, *ch['params']) 
            elif(ch['type'] == 'Candle'):
                self.drawKline(row + 1, *ch['params'])
            elif(ch['type'] == 'CandlePrice'):
                self.drawCandlePrice(row + 1, *ch['params'])
            elif(ch['type'] == 'MacdhWma45'):
                self.drawMacdhWma45(row + 1, *ch['params'])
            elif(ch['type'] == 'Wma45'):
                self.drawWma45(row + 1, *ch['params'])

        
        # Set title
        self.fig.update_layout(
            
            # legend = dict(orientation = "h",   # show entries horizontally
            #     xanchor = "center",  # use center of legend as anchor
            #     x = 0.5), # put legend in center of x-axis

            hovermode="x unified",
            hoverdistance=10,
            margin=dict(b=20, t=40, l=0, r=0)

        )
        self.fig.update_yaxes(showspikes=True, spikemode='across', spikesnap='cursor',  spikedash='dot')
        self.fig.update_xaxes(showspikes=True, spikemode='across', spikesnap='cursor',  spikedash='dot')
        self.fig.update_traces(xaxis='x1')
        self.fig.update_xaxes(type="date", row=1, col=1)
        self.fig.update_annotations(font_size=8)
        
        print("Export to html")
        
        config = {}
        config.setdefault("showLink", False)
        config.setdefault("responsive", True)
        self.fig.write_html(
            f"frontend/build/plot/{self.fileName}",
            config=config,
            auto_play=True,
            include_plotlyjs=True,
            include_mathjax=False,
            post_script=None,
            full_html=True,
            validate=True,
            animation_opts=None,
            auto_open=False,
            default_width='100%',
            default_height='100%',
        )
        


    def drawPrice(self, row):
        candle1MData = self.getData('candle_1m')
        positionData = self.getData('Position')
        orderData = self.getData('Order')
        
        if(len(candle1MData) == 0): return
        timex = pd.to_datetime(candle1MData['close_time'].to_list(), unit='ms', utc=True).tz_convert(VN_TZ)
        self.fig.add_trace(go.Scatter(x=timex, y=candle1MData['close'].tolist(), name="Price"), row=row, col=1)
        # self.fig.add_trace(go.Scatter(x=timex, y=candle1MData[Order_bookModel.best_ask].tolist(), name="Best Ask"), row=row, col=1)
        # self.fig.add_trace(go.Scatter(x=timex, y=candle1MData[Order_bookModel.best_bid].tolist(), name="Best Bid"), row=row, col=1)
        # # self.fig.add_trace(go.Scatter(x=fundingTime, y=fundingDiff, name="Funding", marker=dict(color="crimson", size=8), mode="markers", visible='legendonly'), row=row, col=1)
        # self.fig.add_trace(go.Scatter(x=times, y=priceFuture, name="Future Price"), row=2, col=1)
        # self.fig.add_trace(go.Scatter(x=times, y=priceSpot, name="Spot Price"), row=2, col=1)
        if(len(positionData) > 0):
            positionx = pd.to_datetime(positionData[LabResultsWrapper.lab_result_chart].to_list(), unit='ms', utc=True).tz_convert(VN_TZ)
            positionData['type'] = positionData[LabResultsWrapper.lab_result_type].map(lambda x: "Long" if x==1 else "Short")
            positionData['state'] = positionData[LabResultsWrapper.lab_result_status].map(lambda x: "TP" if x==2 else "ST" if x==3 else 'W' if x==6 else 'C' if x == 4 else '')
            positionData['text'] = "<b>" + positionData['type'] + ":" + positionData['state'] + "</b>"
            self.fig.add_trace(go.Scatter(
                x=positionx, 
                y=positionData[LabResultsWrapper.lab_result_chart_price], 
                name="Position", 
                marker=dict(color="crimson", size=8), 
                mode="markers+text",
                text=positionData['text'],
                textposition="top center",
                textfont=dict(
                        color="crimson",
                    )
                ), row=row, col=1)
        
        if(len(orderData) > 0):
            positionx = pd.to_datetime(orderData[LabOrderWrapper.lab_order_time].to_list(), unit='ms', utc=True).tz_convert(VN_TZ)
            orderData['type'] = orderData[LabOrderWrapper.lab_order_type].map(lambda x: "<b>Buy</b>" if x==1 else "<b>Sell</b>")
            self.fig.add_trace(go.Scatter(
                x=positionx, 
                y=orderData[LabOrderWrapper.lab_order_price], 
                name="Order", 
                marker=dict(color="green", size=8, symbol='square'), 
                mode="markers+text",
                text=orderData['type'],
                textposition="top center",
                textfont=dict(
                        color="green",
                    )
                ), row=row, col=1)

    def drawBidAsk(self, row, diff):
        orderBookData = self.getData('OrderBook')
        
        if(len(orderBookData) == 0): return
        timex = pd.to_datetime(orderBookData.index.to_list(), unit='s', utc=True).tz_convert(VN_TZ)
        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=orderBookData.loc[:,f'bidV_ma_{diff}'],
            line={'color': '#00bf55'},
            name=f'bidv_ma_{diff}'.upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            
            x=timex,
            y=orderBookData.loc[:,f'askV_ma_{diff}'],
            line={'color': '#ff002c'},
            name=f'askv_ma_{diff}'.upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=orderBookData.loc[:,f'NetBA_{diff}'],
            line_color = '#636efa',
            name=f'NetBA_{diff}',
        ), row=row, col=1)

        self.fig.add_trace(go.Scatter(
            x=timex,
            y=orderBookData.loc[:,f'NetBA_BOLU_{diff}'],
            line_color = 'gray',
            line = {'dash': 'dash'},
            name='upper band'.capitalize(),
            opacity = 0.5
        ), row=row, col=1)

        self.fig.add_trace(go.Scatter(
            x=timex,
            y=orderBookData.loc[:,f'NetBA_BOLD_{diff}'],
            line_color = 'gray',
            line = {'dash': 'dash'},
            fill = 'tonexty',
            name='lower band'.capitalize(),
            opacity = 0.5
        ), row=row, col=1)
        
    def drawBidAskDis(self, row, side):
        orderBookData = self.getData('OrderBook')
       
        if(len(orderBookData) == 0): return
        timex = pd.to_datetime(orderBookData.index.to_list(), unit='s', utc=True).tz_convert(VN_TZ)
        self.fig.add_trace(go.Scatter(
            x=timex,
            y=orderBookData.loc[:,f'{side}_0_1'],
            name=f'{side}_0_1'.upper(),
            stackgroup='one',
            mode='lines', 
            fill='tonexty'
        ), row=row, col=1)

        self.fig.add_trace(go.Scatter(
            x=timex,
            y=orderBookData.loc[:,f'{side}_1_2'],
            name=f'{side}_1_2'.upper(),
            stackgroup='one',
            mode='lines', 
            fill='tonexty'
        ), row=row, col=1)

        self.fig.add_trace(go.Scatter(
            x=timex,
            y=orderBookData.loc[:,f'{side}_2_5'],
            name=f'{side}_2_5'.upper(),
            stackgroup='one',
            mode='lines', 
            fill='tonexty'
        ), row=row, col=1)

        errors = orderBookData.loc[orderBookData['stable_time'] == 1]

        self.fig.add_trace(go.Scatter(
            x=pd.to_datetime(errors.index.to_list(), unit='s', utc=True).tz_convert(VN_TZ), 
            y=errors['stable_time'], 
            name="Unstable", 
            marker=dict(color="crimson", size=4), 
            mode="markers",
            ), row=row, col=1)

    def drawOriginBUSD(self, row):
        busdData = self.getData('BUSD')
        if(len(busdData) == 0): return
        timex = pd.to_datetime(busdData['timestamp'].to_list(), unit='s' , utc=True).tz_convert(VN_TZ)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=busdData[f"BU"],
            line_color = '#00bf55',
            name=f"bu".upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=busdData[f"SD"],
            line_color = '#ff002c',
            name=f"sd".upper(),
        ), row=row, col=1)

        # self.fig.add_trace(go.Scattergl(
        #     x=timex,
        #     y= busdData[f"BU"] - busdData[f"SD"],
        #     line_color = '#636efa',
        #     name=f"NetBUSD 1s"
        # ), row=row, col=1)

        errors = busdData.loc[busdData['stable_time'] == 1]

        self.fig.add_trace(go.Scatter(
            x=pd.to_datetime(errors['timestamp'].to_list(), unit='s', utc=True).tz_convert(VN_TZ), 
            y=errors['stable_time']-5, 
            name="Unstable", 
            marker=dict(color="crimson", size=4), 
            mode="markers",
            ), row=row, col=1)
   
    
    def drawBUSD(self, row, timeFrame, window):
        busdData=self.getData('BUSD')
        if(len(busdData) == 0): return
        timex = pd.to_datetime(busdData['timestamp'].to_list(), unit='s' , utc=True).tz_convert(VN_TZ)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=busdData[f"BU_{timeFrame}_{window}"],
            line_color = '#00bf55',
            name=f"bu_{timeFrame}_{window}".upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=busdData[f"SD_{timeFrame}_{window}"],
            line_color = '#ff002c',
            name=f"sd_{timeFrame}_{window}".upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y= busdData[f"BU_{timeFrame}_{window}"] - busdData[f"SD_{timeFrame}_{window}"],
            line_color = '#636efa',
            name=f"NetBUSD {timeFrame}m"
        ), row=row, col=1)

    def drawBusdMacd(self, row, timeFrame, window, ticker=5, col="BUSD", merge=True):
        busdData=self.getData('BUSD')
        if(len(busdData) == 0): return

        hisCol = f"{col}_{timeFrame}_{window}_{ticker}_MACDh"
        macCol = f"{col}_{timeFrame}_{window}_{ticker}_MACD"
        fastCol = f"{col}_{timeFrame}_{window}_{ticker}_FAST"
        slowCol = f"{col}_{timeFrame}_{window}_{ticker}_SLOW"
        smoothCol = f"{col}_{timeFrame}_{window}_{ticker}_SMOOTH"
        
        if(merge):
            busdData['timestamp_macd'] = busdData[BusdModel.timestamp].map(lambda x: x//(ticker*60)*(ticker*60))
            busdDataGroup = busdData.groupby('timestamp_macd').last()
            timex = pd.to_datetime(busdDataGroup.index, unit='s' , utc=True).tz_convert(VN_TZ)
        else:
            busdDataGroup = busdData
            timex = pd.to_datetime(busdData['timestamp'].to_list(), unit='s' , utc=True).tz_convert(VN_TZ)
        
        busdDataGroup['p1'] = busdDataGroup[hisCol].shift(1)
        busdDataGroup.loc[(busdDataGroup[hisCol] < 0) & (busdDataGroup['p1'] >= busdDataGroup[hisCol]), f'color'] = '#ff004c'
        busdDataGroup.loc[(busdDataGroup[hisCol] < 0) & (busdDataGroup['p1'] < busdDataGroup[hisCol]), f'color'] = '#ffc6d1'
        busdDataGroup.loc[(busdDataGroup[hisCol] >= 0) & (busdDataGroup['p1'] <= busdDataGroup[hisCol]), f'color'] = '#00af9b'
        busdDataGroup.loc[(busdDataGroup[hisCol] >= 0) & (busdDataGroup['p1'] > busdDataGroup[hisCol]), f'color'] = '#9fe4dc'

        self.fig.add_trace(go.Bar(
            x=timex,
            y=busdDataGroup[hisCol],
            marker_color=busdDataGroup['color'],
            name=hisCol.upper()
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=busdDataGroup[macCol],
            name=macCol.upper()
        ), row=row, col=1)

        # self.fig.add_trace(go.Scattergl(
        #     x=timex,
        #     y=busdDataGroup[sdCol],
        #     name=sdCol.upper()
        # ), row=row, col=1)
        # self.fig.add_trace(go.Scattergl( 
        #     x=timex,
        #     y=busdDataGroup[buCol],
        #     name=buCol.upper()
        # ), row=row, col=1)

        # self.fig.add_trace(go.Scattergl(
        #     x=timex,
        #     y=busdDataGroup[smoothCol],
        #     name=smoothCol.upper()
        # ), row=row, col=1)

        # self.fig.add_trace(go.Scattergl(
        #     x=timex,
        #     y=busdDataGroup[busdCol],
        #     name=busdCol.upper()
        # ), row=row, col=1)


    def drawBusdMacd1m(self, row, timeFrame, window, ticker=5, col="BUSD", merge=True):
        data = self.getData('BUSD_1m')
        if(len(data) == 0): return

        hisCol = f"{col}_{timeFrame}_{window}_{ticker}_MACDh"
        macCol = f"{col}_{timeFrame}_{window}_{ticker}_MACD"
        fastCol = f"{col}_{timeFrame}_{window}_{ticker}_FAST"
        slowCol = f"{col}_{timeFrame}_{window}_{ticker}_SLOW"
        smoothCol = f"{col}_{timeFrame}_{window}_{ticker}_SMOOTH"
        
        if(merge):
            data['timestamp_macd'] = data[BusdModel.timestamp].map(lambda x: x//(ticker*60)*(ticker*60))
            busdDataGroup = data.groupby('timestamp_macd').last()
            timex = pd.to_datetime(busdDataGroup.index, unit='s' , utc=True).tz_convert(VN_TZ)
        else:
            busdDataGroup = data
            timex = pd.to_datetime(data['timestamp'].to_list(), unit='s' , utc=True).tz_convert(VN_TZ)
        
        busdDataGroup['p1'] = busdDataGroup[hisCol].shift(1)
        busdDataGroup.loc[(busdDataGroup[hisCol] < 0) & (busdDataGroup['p1'] >= busdDataGroup[hisCol]), f'color'] = '#ff004c'
        busdDataGroup.loc[(busdDataGroup[hisCol] < 0) & (busdDataGroup['p1'] < busdDataGroup[hisCol]), f'color'] = '#ffc6d1'
        busdDataGroup.loc[(busdDataGroup[hisCol] >= 0) & (busdDataGroup['p1'] <= busdDataGroup[hisCol]), f'color'] = '#00af9b'
        busdDataGroup.loc[(busdDataGroup[hisCol] >= 0) & (busdDataGroup['p1'] > busdDataGroup[hisCol]), f'color'] = '#9fe4dc'

        self.fig.add_trace(go.Bar(
            x=timex,
            y=busdDataGroup[hisCol],
            marker_color=busdDataGroup['color'],
            name=hisCol.upper()
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=busdDataGroup[macCol],
            name=macCol.upper()
        ), row=row, col=1)

        # self.fig.add_trace(go.Scattergl(
        #     x=timex,
        #     y=busdDataGroup[sdCol],
        #     name=sdCol.upper()
        # ), row=row, col=1)
        # self.fig.add_trace(go.Scattergl( 
        #     x=timex,
        #     y=busdDataGroup[buCol],
        #     name=buCol.upper()
        # ), row=row, col=1)

        # self.fig.add_trace(go.Scattergl(
        #     x=timex,
        #     y=busdDataGroup[smoothCol],
        #     name=smoothCol.upper()
        # ), row=row, col=1)

        # self.fig.add_trace(go.Scattergl(
        #     x=timex,
        #     y=busdDataGroup[busdCol],
        #     name=busdCol.upper()
        # ), row=row, col=1)
    
    def drawKline(self, row, frame):
        name = f'candle_{frame}'
        data = self.getData(name)
        if(len(data) == 0): return
        timex = pd.to_datetime(data['open_time'].to_list(), unit='ms', utc=True).tz_convert(VN_TZ)
        self.fig.add_trace(go.Candlestick(
            x = timex,
            open = data['open'],
            high = data['high'],
            low = data['low'],
            close = data['close'],
            
            name = name.upper(),
            
        ), row=row, col=1)

    def drawCandlePrice(self, row, frame):
        name = f'detailcandle_{frame}'
        data = self.getData(name)
        if(len(data) == 0): return
        timex = pd.to_datetime(data['timestamp'].to_list(), unit='s', utc=True).tz_convert(VN_TZ)
        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=data['close'],
            line_color = '#00bf55',
            name=f"Close",
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=data['open'],
            line_color = '#ff002c',
            name=f"Open".upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=data['low'],
            line_color = '#636efa',
            name=f"Low".upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=data['high'],
            line_color = '#630efa',
            name=f"High".upper(),
        ), row=row, col=1)


    def drawMacdhWma45(self, row, frame, symbol):
        data = self.getData(f'candle_{frame}', symbol)
        if(len(data) == 0): return

        timex = pd.to_datetime(data['open_time'].to_list(), unit='ms', utc=True).tz_convert(VN_TZ)
        
        data['p1'] = data['macdh_wma_45_rsi'].shift(1)
        data.loc[(data['macdh_wma_45_rsi'] < 0) & (data['p1'] >= data['macdh_wma_45_rsi']), f'color'] = '#ff004c'
        data.loc[(data['macdh_wma_45_rsi'] < 0) & (data['p1'] < data['macdh_wma_45_rsi']), f'color'] = '#ffc6d1'
        data.loc[(data['macdh_wma_45_rsi'] >= 0) & (data['p1'] <= data['macdh_wma_45_rsi']), f'color'] = '#00af9b'
        data.loc[(data['macdh_wma_45_rsi'] >= 0) & (data['p1'] > data['macdh_wma_45_rsi']), f'color'] = '#9fe4dc'

        self.fig.add_trace(go.Bar(
            x=timex,
            y=data['macdh_wma_45_rsi'],
            marker_color=data['color'],
            name='macdh_wma_45_rsi'.upper()
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=data['macd_12_26_wma_45_rsi'],
            name='macd_wma_45_rsi'.upper()
        ), row=row, col=1)

    def drawWma45(self, row, frame, symbol):
        data = self.getData(f'candle_{frame}', symbol)
        if(len(data) == 0): return

        timex = pd.to_datetime(data['open_time'].to_list(), unit='ms', utc=True).tz_convert(VN_TZ)
        
        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=data['wma_45_rsi'],
            name='wma_45_rsi'.upper()
        ), row=row, col=1)
        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=data['rsi'],
            name='rsi'.upper()
        ), row=row, col=1)

        
        

        





        

        

        







        

        


    