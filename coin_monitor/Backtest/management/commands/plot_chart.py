import subprocess
from threading import Thread
from dateutil import tz

from django.core.management.base import BaseCommand
from helper.Defaults import *
from helper.Data import *

from helper.Defaults import *
from models.Mongo.KlineModel import KlineModel
import pandas as pd
from datetime import datetime
import plotly.express as px




VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        # parser.add_argument("-s", "--symbol", nargs='*', dest='symbol', default=[], type=str)
        pass

    def handle(self, *args, **options):
        symbol = "ETHUSDT"
        pair_symbol = f"{symbol}_230331"
        klineModel = KlineModel('raw_kline1m_future', f'{symbol}_kline_1m')
        pairKlineModel = KlineModel('raw_kline1m_future', f'{pair_symbol}_kline_1m')
        pair_data = pairKlineModel.collection.find({},{'_id':0}).sort('close_time', 1)
        pair_data = pd.DataFrame.from_records(pair_data)
        pair_data = pair_data.set_index('close_time')
        start_time = int(pair_data.index[0])
        end_time = int(pair_data.index[-1])
        data = klineModel.collection.find({'close_time':{'$gte':start_time, '$lte': end_time}},{'_id':0}).sort('close_time', 1)
        data = pd.DataFrame.from_records(data)
        data = data.set_index('close_time')
        df_net:pd.Series = data['close'] - pair_data['close']
        df_net = df_net.dropna()
        # print(data)
        # print(pair_data)
        # print(df_net)
        # fig = df_net.plot.line()
        df = pd.DataFrame()
        df[symbol] = data['close']
        df[pair_symbol] = pair_data['close']
        df['net'] = df_net
        df.index = pd.to_datetime(df.index, unit='ms')
        fig = px.line(df, x=df.index, y=df['net'])
        fig.write_html(f"/home/ubuntu/linhvhv/coin_monitor/{symbol}_net.html")

