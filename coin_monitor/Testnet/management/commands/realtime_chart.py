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
from models.Mongo.CandleModel import Candle_1mModel

from models.Wrappers.nora_realtime_wrapper import BusdWrapper, OrderBookWrapper
from models.Wrappers.testnet_wrapper import TestnetOrderWrapper, TestnetResultsWrapper
from models.Mongo.BusdModel import BusdModel
from pymongo import ASCENDING, DESCENDING

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
        self.fileName = f'{self.account}_{self.symbol}_{self.day}.html'
        print(f"Generate Chart for account:{self.account} {self.symbol} {self.day}")

        self.busdModel = BusdModel('nora_realtime', 'busd')
        
        self.createChart()
        

    def getData(self, dataType):

        if(isset(self.data, dataType)): return self.data[dataType]

        date = datetime.strptime(self.day, '%Y_%m_%d').replace(tzinfo=VN_TZ)
        startOfDay = int(date.timestamp())
        endOfDay = startOfDay + 86400
        curentTime = int(datetime.now().timestamp())
        if(endOfDay > curentTime): endOfDay = curentTime
        print(f"Get data {dataType} from {startOfDay} to {endOfDay}")

        if(dataType == 'OrderBook'):
            #get orderbook data
            result = list(OrderBookWrapper().filter({
                OrderBookWrapper.symbol:self.symbol,
                OrderBookWrapper.timestamp + "__gte": startOfDay,
                OrderBookWrapper.timestamp + "__lte": endOfDay
            }).order_by(OrderBookWrapper.timestamp).values(
                OrderBookWrapper.timestamp, 
                OrderBookWrapper.mid_price, 
                OrderBookWrapper.best_ask, 
                OrderBookWrapper.best_bid,
                OrderBookWrapper.bidV_ma_5, 
                OrderBookWrapper.askV_ma_5,
                OrderBookWrapper.NetBA_5,
                OrderBookWrapper.NetBA_BOLD_5,
                OrderBookWrapper.NetBA_BOLU_5,
                OrderBookWrapper.askV_0_1,
                OrderBookWrapper.askV_1_2,
                OrderBookWrapper.askV_2_5,
                OrderBookWrapper.bidV_0_1,
                OrderBookWrapper.bidV_1_2,
                OrderBookWrapper.bidV_2_5,
                OrderBookWrapper.stable_time
            ))

            self.data['OrderBook'] = []
            if(len(result) > 0):
                self.data['OrderBook'] = pd.DataFrame.from_records(result).drop_duplicates(subset=['timestamp'], keep='last').set_index(OrderBookWrapper.timestamp).reindex(range(startOfDay, endOfDay))
        
        if(dataType == 'BUSD'):
            #get busd data
           
            result = list(self.busdModel.collection.find({
                BusdModel.symbol: self.symbol,
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
                
            self.data['BUSD'] = []
            if(len(result) > 0):
                self.data['BUSD'] = pd.DataFrame.from_records(result).drop_duplicates(subset=['timestamp'], keep='last')

        if(dataType == 'Order'):
            result = list(TestnetOrderWrapper().filter({
                TestnetOrderWrapper.testnet_order_account: self.account,
                TestnetOrderWrapper.testnet_order_symbol: self.symbol,
                TestnetOrderWrapper.testnet_order_time + "__gte": startOfDay * 1000,
                TestnetOrderWrapper.testnet_order_time + "__lte": endOfDay * 1000
            }).order_by(TestnetOrderWrapper.testnet_order_time).values())
            self.data['Order'] = pd.DataFrame.from_records(result)

        if(dataType == 'Position'):
            result = list(TestnetResultsWrapper().filter({
                TestnetResultsWrapper.testnet_result_account: self.account,
                TestnetResultsWrapper.testnet_result_symbol: self.symbol,
                TestnetResultsWrapper.testnet_result_chart + "__gte": startOfDay * 1000,
                TestnetResultsWrapper.testnet_result_chart + "__lte": endOfDay * 1000
            }).order_by(TestnetResultsWrapper.testnet_result_chart).values())
            self.data['Position'] = pd.DataFrame.from_records(result)
        
        if(dataType.startswith('candle')):
            frame = dataType.split('_')[1]
            data = getKline(self.symbol, frame, startOfDay * 1000, endOfDay * 1000)
            self.data[dataType] = pd.DataFrame.from_records(data)


        return self.data[dataType]
        
    
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

                {
                    "type": "BUSDOrigin",
                    "heigh": 100,
                    "params": [],
                    "title": "BUSD 1s"
                }, 

                {
                    "type": "BUSDMacd",
                    "heigh": 100,
                    "params": [60, 1200, 3],
                    "title": "BUSD_60_1200_3_MACD"
                }

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
            elif(ch['type'] == 'BidAskDis'):
                self.drawBidAskDis(row + 1, *ch['params']) 
            elif(ch['type'] == 'Candle'):
                self.drawKline(row + 1, *ch['params'])

        
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
        self.getData('OrderBook')
        self.getData('Position')
        self.getData('Order')
        
        if(len(self.data['OrderBook']) == 0): return
        timex = pd.to_datetime(self.data['OrderBook'].index.to_list(), unit='s', utc=True).tz_convert(VN_TZ)
        self.fig.add_trace(go.Scatter(x=timex, y=self.data['OrderBook'][OrderBookWrapper.mid_price].tolist(), name="Price"), row=row, col=1)
        # self.fig.add_trace(go.Scatter(x=timex, y=self.data['OrderBook'][OrderBookWrapper.best_ask].tolist(), name="Best Ask"), row=row, col=1)
        # self.fig.add_trace(go.Scatter(x=timex, y=self.data['OrderBook'][OrderBookWrapper.best_bid].tolist(), name="Best Bid"), row=row, col=1)
        # # self.fig.add_trace(go.Scatter(x=fundingTime, y=fundingDiff, name="Funding", marker=dict(color="crimson", size=8), mode="markers", visible='legendonly'), row=row, col=1)
        # self.fig.add_trace(go.Scatter(x=times, y=priceFuture, name="Future Price"), row=2, col=1)
        # self.fig.add_trace(go.Scatter(x=times, y=priceSpot, name="Spot Price"), row=2, col=1)
        if(len(self.data['Position']) > 0):
            positionx = pd.to_datetime(self.data['Position'][TestnetResultsWrapper.testnet_result_chart].to_list(), unit='ms', utc=True).tz_convert(VN_TZ)
            self.data['Position']['type'] = self.data['Position'][TestnetResultsWrapper.testnet_result_type].map(lambda x: "Long" if x==1 else "Short")
            self.data['Position']['state'] = self.data['Position'][TestnetResultsWrapper.testnet_result_status].map(lambda x: "TP" if x==2 else "ST" if x==3 else 'W' if x==6 else 'C' if x == 4 else '')
            self.data['Position']['text'] = "<b>" + self.data['Position']['type'] + ":" + self.data['Position']['state'] + "</b>"
            self.fig.add_trace(go.Scatter(
                x=positionx, 
                y=self.data['Position'][TestnetResultsWrapper.testnet_result_enter_price], 
                name="Position", 
                marker=dict(color="crimson", size=8), 
                mode="markers+text",
                text=self.data['Position']['text'],
                textposition="top center",
                textfont=dict(
                        color="crimson",
                    )
                ), row=row, col=1)
        
        if(len(self.data['Order']) > 0):
            positionx = pd.to_datetime(self.data['Order'][TestnetOrderWrapper.testnet_order_time].to_list(), unit='ms', utc=True).tz_convert(VN_TZ)
            self.data['Order']['type'] = self.data['Order'][TestnetOrderWrapper.testnet_order_type].map(lambda x: "<b>Buy</b>" if x==1 else "<b>Sell</b>")
            self.fig.add_trace(go.Scatter(
                x=positionx, 
                y=self.data['Order'][TestnetOrderWrapper.testnet_order_price], 
                name="Order", 
                marker=dict(color="green", size=8, symbol='square'), 
                mode="markers+text",
                text=self.data['Order']['type'],
                textposition="top center",
                textfont=dict(
                        color="green",
                    )
                ), row=row, col=1)

    def drawBidAsk(self, row, diff):
        self.getData('OrderBook')
        
        if(len(self.data['OrderBook']) == 0): return
        timex = pd.to_datetime(self.data['OrderBook'].index.to_list(), unit='s', utc=True).tz_convert(VN_TZ)
        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=self.data['OrderBook'].loc[:,f'bidV_ma_{diff}'],
            line={'color': '#00bf55'},
            name=f'bidv_ma_{diff}'.upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            
            x=timex,
            y=self.data['OrderBook'].loc[:,f'askV_ma_{diff}'],
            line={'color': '#ff002c'},
            name=f'askv_ma_{diff}'.upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=self.data['OrderBook'].loc[:,f'NetBA_{diff}'],
            line_color = '#636efa',
            name=f'NetBA_{diff}',
        ), row=row, col=1)

        self.fig.add_trace(go.Scatter(
            x=timex,
            y=self.data['OrderBook'].loc[:,f'NetBA_BOLU_{diff}'],
            line_color = 'gray',
            line = {'dash': 'dash'},
            name='upper band'.capitalize(),
            opacity = 0.5
        ), row=row, col=1)

        self.fig.add_trace(go.Scatter(
            x=timex,
            y=self.data['OrderBook'].loc[:,f'NetBA_BOLD_{diff}'],
            line_color = 'gray',
            line = {'dash': 'dash'},
            fill = 'tonexty',
            name='lower band'.capitalize(),
            opacity = 0.5
        ), row=row, col=1)
        
    def drawBidAskDis(self, row, side):
        self.getData('OrderBook')
       
        if(len(self.data['OrderBook']) == 0): return
        timex = pd.to_datetime(self.data['OrderBook'].index.to_list(), unit='s', utc=True).tz_convert(VN_TZ)
        self.fig.add_trace(go.Scatter(
            x=timex,
            y=self.data['OrderBook'].loc[:,f'{side}_0_1'],
            name=f'{side}_0_1'.upper(),
            stackgroup='one',
            mode='lines', 
            fill='tonexty'
        ), row=row, col=1)

        self.fig.add_trace(go.Scatter(
            x=timex,
            y=self.data['OrderBook'].loc[:,f'{side}_1_2'],
            name=f'{side}_1_2'.upper(),
            stackgroup='one',
            mode='lines', 
            fill='tonexty'
        ), row=row, col=1)

        self.fig.add_trace(go.Scatter(
            x=timex,
            y=self.data['OrderBook'].loc[:,f'{side}_2_5'],
            name=f'{side}_2_5'.upper(),
            stackgroup='one',
            mode='lines', 
            fill='tonexty'
        ), row=row, col=1)

        errors = self.data['OrderBook'].loc[self.data['OrderBook']['stable_time'] == 1]

        self.fig.add_trace(go.Scatter(
            x=pd.to_datetime(errors.index.to_list(), unit='s', utc=True).tz_convert(VN_TZ), 
            y=errors['stable_time'], 
            name="Unstable", 
            marker=dict(color="crimson", size=4), 
            mode="markers",
            ), row=row, col=1)

    def drawOriginBUSD(self, row):
        self.getData('BUSD')
        if(len(self.data['BUSD']) == 0): return
        timex = pd.to_datetime(self.data['BUSD']['timestamp'].to_list(), unit='s' , utc=True).tz_convert(VN_TZ)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=self.data['BUSD'][f"BU"],
            line_color = '#00bf55',
            name=f"bu".upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=self.data['BUSD'][f"SD"],
            line_color = '#ff002c',
            name=f"sd".upper(),
        ), row=row, col=1)

        # self.fig.add_trace(go.Scattergl(
        #     x=timex,
        #     y= self.data['BUSD'][f"BU"] - self.data['BUSD'][f"SD"],
        #     line_color = '#636efa',
        #     name=f"NetBUSD 1s"
        # ), row=row, col=1)

        errors = self.data['BUSD'].loc[self.data['BUSD']['stable_time'] == 1]

        self.fig.add_trace(go.Scatter(
            x=pd.to_datetime(errors['timestamp'].to_list(), unit='s', utc=True).tz_convert(VN_TZ), 
            y=errors['stable_time']-5, 
            name="Unstable", 
            marker=dict(color="crimson", size=4), 
            mode="markers",
            ), row=row, col=1)
   
    
    def drawBUSD(self, row, timeFrame, window):
        self.getData('BUSD')
        if(len(self.data['BUSD']) == 0): return
        timex = pd.to_datetime(self.data['BUSD']['timestamp'].to_list(), unit='s' , utc=True).tz_convert(VN_TZ)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=self.data['BUSD'][f"BU_{timeFrame}_{window}"],
            line_color = '#00bf55',
            name=f"bu_{timeFrame}_{window}".upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=self.data['BUSD'][f"SD_{timeFrame}_{window}"],
            line_color = '#ff002c',
            name=f"sd_{timeFrame}_{window}".upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y= self.data['BUSD'][f"BU_{timeFrame}_{window}"] - self.data['BUSD'][f"SD_{timeFrame}_{window}"],
            line_color = '#636efa',
            name=f"NetBUSD {timeFrame}m"
        ), row=row, col=1)

    def drawBusdMacd(self, row, timeFrame, window, ticker=5, col="BUSD", merge=True):
        self.getData('BUSD')
        if(len(self.data['BUSD']) == 0): return

        hisCol = f"{col}_{timeFrame}_{window}_{ticker}_MACDh"
        macCol = f"{col}_{timeFrame}_{window}_{ticker}_MACD"
        fastCol = f"{col}_{timeFrame}_{window}_{ticker}_FAST"
        slowCol = f"{col}_{timeFrame}_{window}_{ticker}_SLOW"
        smoothCol = f"{col}_{timeFrame}_{window}_{ticker}_SMOOTH"
        
        if(merge):
            self.data['BUSD']['timestamp_macd'] = self.data['BUSD'][BusdWrapper.timestamp].map(lambda x: x//(ticker*60)*(ticker*60))
            busdDataGroup = self.data['BUSD'].groupby('timestamp_macd').last()
            timex = pd.to_datetime(busdDataGroup.index, unit='s' , utc=True).tz_convert(VN_TZ)
        else:
            busdDataGroup = self.data['BUSD']
            timex = pd.to_datetime(self.data['BUSD']['timestamp'].to_list(), unit='s' , utc=True).tz_convert(VN_TZ)
        
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
        

        





        

        

        







        

        


    