from datetime import datetime
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
import pandas as pd
from pymongo import DESCENDING, ASCENDING
import json
from Backtest.BOT.Processor.Campaign import Campaign
from Backtest.BOT.Bot2_v1.Campaign import Campaign as Campaign_type2


VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'Generate testnet chart'
    
    #python manage.py bot_campaign -c pair_trading_band > ./Backtest/BOT/Logs/pair_trading_band.log

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        parser.add_argument("-c","--campaign", type=str)

    def handle(self, *args, **options):
        campaignArgs = options.get('campaign', None)
        
        campaignCfgId = campaignArgs
        campaignJson = f'./Backtest/BOT/Campaign/{campaignArgs}.json'
        campaignCfg:dict = json.load(open(campaignJson))
        
        strategyArgs = campaignCfg.get('strategy', campaignArgs)
        strategyJson = f'./Backtest/BOT/Strategy/{strategyArgs}.json'
        strategyCfg = json.load(open(strategyJson))
        
        campaignCfg['id'] = campaignCfgId
        campaignType = campaignCfg.get('type', 1)
        if(campaignType == 1):
            campaign = Campaign(campaignCfg, strategyCfg)
        else:
            campaign = Campaign_type2(campaignCfg, strategyCfg)
        
        campaign.initial()
        # campaign.runCustom()
        campaign.run()

        print(f"Save result to database")
        actions = campaign.getActions().values()
        # print(actions)
        resultModel = MongoModel('stock_backtest_result').setCollection(f"coin_{campaignCfg['id']}")
        resultModel.collection.delete_many({})
        
        
        actionsPandas = pd.DataFrame(actions).fillna(0)
        actionsPandas = actionsPandas.loc[actionsPandas["bot_act_commission"] > 0]
        
        resultModel.collection.insert_many(actionsPandas.to_dict(orient='records'))
        
        summary = f"========Summary {campaignCfg['id']} ============\n"
        summary +=f"Total Action = {len(actionsPandas.index)}\n"
        summary +=f"Total PNL = {actionsPandas['bot_act_pnl'].sum()}\n"
        summary +=f"Total Real PNL = {actionsPandas['bot_act_real_pnl'].sum()}\n"
        summary +=f"Total commission = {actionsPandas['bot_act_commission'].sum()}\n"
        summary +=f"Takeprofit = {len(actionsPandas.loc[actionsPandas['bot_act_real_pnl'] > 0].index)}\n"
        summary +=f"Stoploss = {len(actionsPandas.loc[actionsPandas['bot_act_real_pnl'] < 0].index)}\n"
        summary +=f"Count Edit Order = {campaign.countEditOrder}\n"
        print(summary)
        
        # actionsPandas.to_csv(f"./Backtest/BOT/Results/{campaignCfg['id']}_result.csv")
        
       

           
    
        





        
        
        
        

    
        
        





        

        

        







        

        


    