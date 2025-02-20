from datetime import datetime, timedelta, tzinfo
from heapq import merge
from dateutil import tz
from math import floor
import os

from django.core.management.base import BaseCommand
import requests
from helper.Defaults import *

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from plotly.subplots import make_subplots

from models.Mongo.MongoModel import MongoModel

import pprint
pp = pprint.PrettyPrinter(depth=4)


VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')



class Command(BaseCommand):
    help = 'Generate testnet chart'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        

    def add_arguments(self, parser):
        parser.add_argument("-c","--campaign", type=str)

    
    def handle(self, *args, **options):
        campaignCfg = options.get('campaign', None)

        # accountObj = list(LabAccountWrapper().filter({LabAccountWrapper.lab_account_id: self.account}))
        # if(len(accountObj) == 0):
        #     raise Exception('No account')
        # self.accountObj = accountObj[0] #type: LabAccount

        self.fileName = f'./Backtest/BOT/Plots/pnl_{campaignCfg}.html'
       
        self.resultModel = MongoModel('stock_backtest_result').setCollection(f"coin_{campaignCfg}")
        self.results = list(self.resultModel.collection.find({}, {"_id":0, "orders":0, "bot_act_enter_data":0, "bot_act_exit_data":0}))
        if(len(self.results) == 0):
            print("No result")
            return
        
        self.results = pd.DataFrame(self.results)
        
        self.createPNLChart(self.fileName)
        
        self.results['interval'] = self.results['bot_act_exit_time'] - self.results['bot_act_enter_time']
        
        meanInterval = self.results.loc[self.results['bot_act_commission'] > 0]['interval'].mean()//60000
        
        totalAction = len(self.results.loc[self.results['bot_act_commission'] > 0])
        totalTakeprofit = len(self.results.loc[self.results['bot_act_real_pnl'] > 0])
        totalStoploss = len(self.results.loc[self.results['bot_act_real_pnl'] < 0])
        totalQty = self.results['bot_act_qty'].sum()
        totalPNL = f"{round(self.results['bot_act_real_pnl'].sum()):,}"
        totalCommission = f"{round(self.results['bot_act_commission'].sum()):,}"
        maxTakeprofit = f"{round(self.results['bot_act_real_pnl'].max()):,}"
        maxStoploss = f"{round(self.results['bot_act_real_pnl'].min()):,}"
        winrate = round(totalTakeprofit * 100 / totalAction, 2)
        
        
        summary = {
            'Total Action' :totalAction,
            'Total Takeprofit' :totalTakeprofit,
            'Total Stoploss' :totalStoploss,
            'Total Qty' :totalQty,
            'Total PNL' :totalPNL,
            'Total Commission' :totalCommission,
            'Max Takeprofit' :maxTakeprofit,
            'Max Stoploss' :maxStoploss,
            'Winrate': f"{winrate}%",
            "Interval": meanInterval,
            
        }
        
        column = 'Campaign'
        values = campaignCfg
        for key in summary:
            value = summary[key]
            column = column + "\t " + str(key)
            values = values + "\t " + str(value)
            
        print(column)
        print(values)
            
        
        
        
    def createPNLChart(self, fileName):
        
        # Create figure
        self.fig = make_subplots(
            rows= 1, 
            cols=1, 
            shared_xaxes=True, 
            row_heights=[600],
            vertical_spacing=0.02,
            subplot_titles=['PNL Cummsum']
        )
        
        # Set title
        self.fig.update_layout(
            
            # legend = dict(orientation = "h",   # show entries horizontally
            #     xanchor = "center",  # use center of legend as anchor
            #     x = 0.5), # put legend in center of x-axis

            hovermode="x unified",
            hoverdistance=10,
            margin=dict(b=20, t=40, l=0, r=0),
            

        )
        self.fig.update_yaxes(showspikes=True, spikemode='across', spikesnap='cursor',  spikedash='dot')
        self.fig.update_xaxes(showspikes=True, spikemode='across', spikesnap='cursor',  spikedash='dot')
        self.fig.update_traces(xaxis='x1')
        self.fig.update_xaxes(dict(
            type='category',
            categoryorder = 'category ascending',
            rangeslider = {'visible': False}
            # tickvals=list(df.index)[::NSKIP],
            # ticktext=list(df['day'])[::NSKIP],
        ))
        self.fig.update_annotations(font_size=8)
        
        timex = pd.to_datetime(self.results["bot_act_exit_time"].to_list(), unit='ms', utc=True).tz_convert(VN_TZ)
        self.fig.add_trace(go.Scattergl(
            x=timex,
            y=self.results["bot_act_real_pnl"].cumsum(),
            line={'color': '#00bf55'},
            name=f'PNL',
        ), row=1, col=1)
        
        print("Export to html")
        
        config = {}
        config.setdefault("showLink", False)
        config.setdefault("responsive", True)
        self.fig.write_html(
            fileName,
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
        


    