from datetime import datetime, timedelta, tzinfo
from heapq import merge
import math
from time import time
from dateutil import tz
from math import floor
import os

from django.core.management.base import BaseCommand
import numpy as np
import requests
from tqdm import tqdm
from helper.Defaults import *

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from plotly.subplots import make_subplots

from pymongo import MongoClient

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')
from dotenv import load_dotenv

load_dotenv()



class Command(BaseCommand):
    help = 'Generate testnet chart'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self.BUSD_TIMEFRAMES = [60, 240]
        self.BUSD_MA_WINDOW = [1200, 4800]
        self.MACD_TICKER = 5
        self.MACD_GREEN_BOLD = 0
        self.MACD_GREEN_LIGHT = 1
        self.MACD_RED_BOLD = 2
        self.MACD_RED_LIGHT = 3

        self.diff = [1,2,5]
        self.indexDiff=[5]
        self.ma = 2 * 600
        self.bol_ma = 3 * 3600
        self.maxLeng = 4 * 3600
        

    def add_arguments(self, parser):
        today = datetime.today()
        day = today.strftime("%Y_%m_%d")
        parser.add_argument("-s","--symbol", nargs='?', required=True, default=None, type=str)
        parser.add_argument("-d","--day", nargs='?', default=day, type=str)
        parser.add_argument("-a","--account", nargs='?', default=None, type=int)

    
    def handle(self, *args, **options):
        self.symbol = options.get('symbol').upper()
        self.day = options.get('day')
        self.account = options.get('account')
        self.fileName = f'raw_{self.account}_{self.symbol}_{self.day}.html'
        host = os.getenv("DB_HOST", '127.0.0.1')
        port = int(os.getenv("DB_PORT", 27023))
        username = os.getenv("DB_USERNAME", None)
        password = os.getenv("DB_PASSWORD", None)
        authsource = os.getenv("DB_AUTHSOURCE", None)
        port = int(os.getenv("DB_PORT", 27023))
        db_name = os.getenv("DB_NAME", 'coin')
        self.agg_trade_name = f'{self.day}_{self.symbol}_agg_trades'
        self.depth_name = f'{self.day}_{self.symbol}_depth'
        self.db = MongoClient(host=host, port=port, username=username, password=password, authSource=authsource)[db_name]
        self.aggTradeColl = self.db.get_collection(self.agg_trade_name)
        self.depthColl = self.db.get_collection(self.depth_name)
        print(f"Generate Chart for: {self.symbol} {self.day}")
        self.getDataRaw()
        # self.calc_BUSD()
        # self.calc_MACD_BUSD()
        self.calc_MACD_BA()
        # self.createChart()

    def getDataRaw(self):
        # self.aggTradeRaw = pd.DataFrame.from_records(self.aggTradeColl.find({},{'T':1,'m':1,'q':1,'_id':0}))
        self.depthRaw = pd.DataFrame.from_records(self.depthColl.find({},{'_id':0,'T':1, 'u':1,'pu':1,'b':1,'a':1}).limit(10000))
        # print(self.depthRaw['b'])

    def calc_MACD_BUSD(self):
        df_busd = self.df_busd
        for timeframe, ma_window in zip(self.BUSD_TIMEFRAMES, self.BUSD_MA_WINDOW):
            df_busd[f'BU_{timeframe}_{ma_window}'] = df_busd['BU'].rolling(timeframe * 60).sum().rolling(ma_window).mean()
            df_busd[f'SD_{timeframe}_{ma_window}'] = df_busd['SD'].rolling(timeframe * 60).sum().rolling(ma_window).mean()

        df_busd['timestamp_macd'] = df_busd.index.map(lambda x: x//(self.MACD_TICKER*60)*(self.MACD_TICKER*60))
        agg = {}
        for timeframe, ma_window in zip(self.BUSD_TIMEFRAMES, self.BUSD_MA_WINDOW):
            agg[f'BU_{timeframe}_{ma_window}'] = 'sum'
            agg[f'SD_{timeframe}_{ma_window}'] = 'sum'
        df_macd = df_busd.groupby('timestamp_macd').agg(agg).reset_index().set_index('timestamp_macd')
        df_macd.index.names = ['timestamp']
        for timeframe, ma_window in zip(self.BUSD_TIMEFRAMES, self.BUSD_MA_WINDOW):
            df_macd[f'BUSD_{timeframe}_{ma_window}'] = df_macd[f'BU_{timeframe}_{ma_window}'] - df_macd[f'SD_{timeframe}_{ma_window}']
            k = df_macd[f'BUSD_{timeframe}_{ma_window}'].ewm(span=12, adjust=False, min_periods=12).mean()
            d = df_macd[f'BUSD_{timeframe}_{ma_window}'].ewm(span=26, adjust=False, min_periods=26).mean()
            macd = k - d
            macd_s = macd.ewm(span=9, adjust=False, min_periods=9).mean()
            macd_h = macd - macd_s
            df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh'] = macd_h
            df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh_p1'] = df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh'].shift(1)
            df_macd[f'BUSD_{timeframe}_{ma_window}_colors'] = np.nan
            df_macd[f'BUSD_{timeframe}_{ma_window}_colors_type'] = np.nan
            df_macd.loc[(df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh'] < 0) & (df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh_p1'] >= df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh']), f'BUSD_{timeframe}_{ma_window}_colors'] = '#ff004c'
            df_macd.loc[(df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh'] < 0) & (df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh_p1'] < df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh']), f'BUSD_{timeframe}_{ma_window}_colors'] = '#ffc6d1'
            df_macd.loc[(df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh'] >= 0) & (df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh_p1'] <= df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh']), f'BUSD_{timeframe}_{ma_window}_colors'] = '#00af9b'
            df_macd.loc[(df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh'] >= 0) & (df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh_p1'] > df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh']), f'BUSD_{timeframe}_{ma_window}_colors'] = '#9fe4dc'
            
            df_macd.loc[(df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh'] < 0) & (df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh_p1'] >= df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh']), f'BUSD_{timeframe}_{ma_window}_colors_type'] = self.MACD_RED_BOLD
            df_macd.loc[(df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh'] < 0) & (df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh_p1'] < df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh']), f'BUSD_{timeframe}_{ma_window}_colors_type'] = self.MACD_RED_LIGHT
            df_macd.loc[(df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh'] >= 0) & (df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh_p1'] <= df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh']), f'BUSD_{timeframe}_{ma_window}_colors_type'] = self.MACD_GREEN_BOLD
            df_macd.loc[(df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh'] >= 0) & (df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh_p1'] > df_macd[f'BUSD_{timeframe}_{ma_window}_MACDh']), f'BUSD_{timeframe}_{ma_window}_colors_type'] = self.MACD_GREEN_LIGHT
            
            df_macd[f'BUSD_{timeframe}_{ma_window}_colors_p1'] = df_macd[f'BUSD_{timeframe}_{ma_window}_colors'].shift(1)
            df_macd[f'BUSD_{timeframe}_{ma_window}_colors_type_p1'] = df_macd[f'BUSD_{timeframe}_{ma_window}_colors_type'].shift(1)

        self.df_macd = df_macd

    def calc_BUSD(self):
        def sum_BUSD(dff: pd.DataFrame) -> pd.DataFrame:
            # print(dff)
            dff['T'] = dff['T'].map(lambda x: int(x / 1000))
            start_time, end_time = dff['T'].min(), dff['T'].max()
            dff = dff.groupby('T').agg({'q': sum}).reindex(range(start_time, end_time + 1)).fillna(0).reset_index()
            dff['q'] = dff['q'].map(float)
            return dff
        aggTradeRaw = self.aggTradeRaw
        # print(aggTradeRaw)
        df_bu_raw = sum_BUSD(aggTradeRaw[aggTradeRaw['m'] == True]).set_index('T')
        df_bu_raw['BU'] = df_bu_raw['q']
        df_sd_raw = sum_BUSD(aggTradeRaw[aggTradeRaw['m'] == False]).set_index('T')
        df_sd_raw['SD'] = df_sd_raw['q']
        df_busd = pd.merge(df_bu_raw[['BU']], df_sd_raw[['SD']], on='T', how='outer')
        start_time, end_time = df_busd.index.min(), df_busd.index.max()
        df_busd = df_busd.reindex(range(start_time, end_time + 1)).fillna(0).reset_index().set_index('T')
        self.df_busd = df_busd

    def calc_MACD_BA(self):

        df = self.depthRaw
        asks = (df['a']).map(lambda x: pd.DataFrame(x, columns=['p','v']))
        # ask_p = df['a'].map(lambda x: x[0][0] if len(x) > 0 else None)
        # ask_v = df['a'].map(lambda x: x[0][1] if len(x) > 0 else None)
        # print(df.columns)
        data = pd.DataFrame(columns = ['best_ask','best_bid'])
        data['best_ask'] = df['a'].map(lambda x: float(min(x, default=[0])[0]))
        data['best_bid'] = df['b'].map(lambda x: float(max(x, default=[0])[0]))
        data['mid_price'] = (data['best_ask'] + data['best_bid'])/2
        # # for i, diff in enumerate(self.diff):
        print(data)
        askDiff = map(lambda x: [x, data['best_ask'] * (100 + x)/100], self.diff)
        bidDiff = map(lambda x: [x, data['best_bid'] * (100 - x)/100], self.diff)
        def asksum(i, df: pd.DataFrame, diffPrice):
            df = df.astype(float)
            print(df)
            print(diffPrice)
            print(data['best_bid'][i])
            sum = df.loc[(df['p'] >= diffPrice) & (df['p'] <= data['best_bid'][i]), 'v'].sum()
            print(sum)
            return sum
        askV = {}
        for i, items in asks.iteritems():
            # print(i)
            for diffPrice in askDiff:
                # print(len(diffPrice[1]))
                if f'askV_{diffPrice[0]}' not in askV:
                    askV[f'askV_{diffPrice[0]}'] = list([asksum(i, items, diffPrice[1][i])])
                else:
                    askV[f'askV_{diffPrice[0]}'].append(asksum(i, items, diffPrice[1][i]))
        
        for diffPrice in askDiff:
            # print(askV[f'askV_{diffPrice[0]}'])
            data[f'askV_{diffPrice[0]}'] = askV[f'askV_{diffPrice[0]}']
            # data[f'askV_{diffPrice[0]}'] = self.bidInSecond.loc[(self.bidInSecond['p']>=diffPrice[1]) & (self.bidInSecond['p'] <= bestBid)]['v'].sum()
        print(data)
        # for diffPrice in bidDiff:
        #     data[f'bidV_{diffPrice[0]}'] = self.bidInSecond.loc[(self.bidInSecond['p']>=diffPrice[1]) & (self.bidInSecond['p'] <= bestBid)]['v'].sum()
        # def calc_volume(df, list_diff):
        #     for i, diff in enumerate(list_diff):
        #         df[f'bidV_{diff}'] = result[:, i, 1]
        #     return df
        # result = calc_best(df['bids_start_idx'].to_numpy(), df['bids_end_idx'].to_numpy(), df['u'].to_numpy(), df['pu'].to_numpy(), df['b'], 0, self.diff)
        # for i, diff in enumerate(self.diff):
        #     df[f'best_bid_{diff}'] = result[:, i, 0]
        #     df[f'bidV_{diff}'] = result[:, i, 1]
        # result = calc_best(df['asks_start_idx'].to_numpy(), df['asks_end_idx'].to_numpy(), df['u'].to_numpy(), df['pu'].to_numpy(), df['a'], 1, self.diff)
        # for i, diff in enumerate(self.diff):
        #     df[f'best_ask_{diff}'] = result[:, i, 0]
        #     df[f'askV_{diff}'] = result[:, i, 1]
        # for i, diff in enumerate(self.diff):
        #     df.loc[(df[f'best_bid_{diff}'] == -1), f'bidV_{diff}'] = np.nan
        #     df.loc[(df[f'best_bid_{diff}'] == -1), f'best_ask_{diff}'] = np.nan
        #     df.loc[(df[f'best_bid_{diff}'] == -1), f'askV_{diff}'] = np.nan
        #     df.loc[(df[f'best_bid_{diff}'] == -1), f'best_bid_{diff}'] = np.nan
        #     df.loc[(df[f'best_ask_{diff}'] == -1), f'best_bid_{diff}'] = np.nan
        #     df.loc[(df[f'best_ask_{diff}'] == -1), f'bidV_{diff}'] = np.nan
        #     df.loc[(df[f'best_ask_{diff}'] == -1), f'askV_{diff}'] = np.nan
        #     df.loc[(df[f'best_ask_{diff}'] == -1), f'best_ask_{diff}'] = np.nan
        #     df[f'mid_price_{diff}'] = (df[f'best_bid_{diff}'] + df[f'best_ask_{diff}']) / 2
        # df = df.tail(lens[0])
        # print(df)
        # bestAsk = asks['p'].min()
        # bestBid = bids['p'].max()
        # askDiff = map(lambda x: [x, bestAsk * (100 + x)/100], self.diff)
        # bidDiff = map(lambda x: [x, bestBid * (100 - x)/100], self.diff)


    def getData(self, dataType):

        date = datetime.strptime(self.day, '%Y_%m_%d').replace(tzinfo=VN_TZ)
        startOfDay = int(date.timestamp())
        endOfDay = startOfDay + 86400
        curentTime = int(datetime.now().timestamp())
        if(endOfDay > curentTime): endOfDay = curentTime
        print(f"Get data {dataType} from {startOfDay} to {endOfDay}")
        
    
    def createChart(self):

        # Create figure
        self.fig = make_subplots(
            rows=6, 
            cols=1, 
            shared_xaxes=True, 
            row_heights= [100/6] * 6, 
            vertical_spacing=0.01,
            specs=[
                [{"secondary_y": False}], 
                [{"secondary_y": False}], 
                [{"secondary_y": False}], 
                [{"secondary_y": False}],
                [{"secondary_y": False}], 
                [{"secondary_y": False}]
            ]
            )

        self.data = {}
        # self.getData('OrderBook')
        # self.getData('Position')
        # self.getData('Order')
        # self.drawPrice(1)
        # self.drawBidAsk(2, 5)

        # self.getData('BUSD')
        # self.drawBUSD(3, 60, 1200)
        # self.drawBusdHis(4, 60, 1200)

        # self.drawBUSD(5, 240, 4800)
        # self.drawBusdHis(6, 240, 4800)

        # Set title
        self.fig.update_layout(
            
            # legend = dict(orientation = "h",   # show entries horizontally
            #     xanchor = "center",  # use center of legend as anchor
            #     x = 0.5), # put legend in center of x-axis

            hovermode="x unified",
            hoverdistance=10,
            margin=dict(b=20, t=30, l=0, r=0)

        )
        self.fig.update_yaxes(showspikes=True, spikemode='across', spikesnap='cursor',  spikedash='dot')
        self.fig.update_xaxes(showspikes=True, spikemode='across', spikesnap='cursor',  spikedash='dot')
        self.fig.update_traces(xaxis='x1')
        self.fig.update_xaxes(type="date", row=1, col=1)
        
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
        if(len(self.data['OrderBook']) == 0): return
        timex = pd.to_datetime(self.data['OrderBook'].index.to_list(), unit='s', utc=True).tz_convert(VN_TZ)
        
        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=self.data['OrderBook'].loc[:,f'bidv_ma_{diff}'],
            line={'color': '#00bf55'},
            name=f'bidv_ma_{diff}'.upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=self.data['OrderBook'].loc[:,f'askv_ma_{diff}'],
            line={'color': '#ff002c'},
            name=f'askv_ma_{diff}'.upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=self.data['OrderBook'].loc[:,f'netba_{diff}'],
            line_color = '#636efa',
            name=f'NetBA_{diff}',
        ), row=row, col=1)

        self.fig.add_trace(go.Scatter(
            x=timex,
            y=self.data['OrderBook'].loc[:,f'netba_bolu_{diff}'],
            line_color = 'gray',
            line = {'dash': 'dash'},
            name='upper band'.capitalize(),
            opacity = 0.5
        ), row=row, col=1)

        self.fig.add_trace(go.Scatter(
            x=timex,
            y=self.data['OrderBook'].loc[:,f'netba_bold_{diff}'],
            line_color = 'gray',
            line = {'dash': 'dash'},
            fill = 'tonexty',
            name='lower band'.capitalize(),
            opacity = 0.5
        ), row=row, col=1)
        
    def drawBUSD(self, row, timeFrame, window):
        if(len(self.data['BUSD']) == 0): return
        timex = pd.to_datetime(self.data['BUSD']['timestamp'].to_list(), unit='s' , utc=True).tz_convert(VN_TZ)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=self.data['BUSD'][f"bu_{timeFrame}_{window}"],
            line_color = '#00bf55',
            name=f"bu_{timeFrame}_{window}".upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=self.data['BUSD'][f"sd_{timeFrame}_{window}"],
            line_color = '#ff002c',
            name=f"sd_{timeFrame}_{window}".upper(),
        ), row=row, col=1)

        self.fig.add_trace(go.Scattergl(
            x=timex,
            y= self.data['BUSD'][f"bu_{timeFrame}_{window}"] - self.data['BUSD'][f"sd_{timeFrame}_{window}"],
            line_color = '#636efa',
            name=f"NetBUSD {timeFrame}m"
        ), row=row, col=1)

    def drawBusdHis(self, row, timeFrame, window, merge=True):

        if(len(self.data['BUSD']) == 0): return

        hisCol = f"busd_{timeFrame}_{window}_macdh"
        macCol = f"busd_{timeFrame}_{window}_macd"
        fastCol = f"busd_{timeFrame}_{window}_fast"
        slowCol = f"busd_{timeFrame}_{window}_slow"
        smoothCol = f"busd_{timeFrame}_{window}_smooth"
        busdCol = f"busd_{timeFrame}_{window}"

        if(merge):
            self.data['BUSD']['timestamp_macd'] = self.data['BUSD'][BusdWrapper.timestamp].map(lambda x: x//(5*60)*(5*60))
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
        #     y=busdDataGroup[fastCol],
        #     name=fastCol.upper()
        # ), row=row, col=1)
        # self.fig.add_trace(go.Scattergl(
        #     x=timex,
        #     y=busdDataGroup[slowCol],
        #     name=slowCol.upper()
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
        
        





        

        

        







        

        


    