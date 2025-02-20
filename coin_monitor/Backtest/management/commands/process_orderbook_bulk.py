from datetime import datetime
import subprocess
import sys
from dateutil import tz

from django.core.management.base import BaseCommand
from Backtest.Processors.klineProcessor import klineProcessor
from helper.Defaults import *
from helper.Data import *

from math import floor
from threading import Thread
from time import sleep, time
import orjson
from helper.Redis import Redis
from helper.Defaults import *
import pandas as pd


import pandas as pd

from models.Mongo.KlineModel import KlineModel


VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'Generate testnet chart'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        parser.add_argument("-d","--day", nargs='?', default=None, type=str)
        parser.add_argument("--reset", action='store_true', default=False)
        parser.add_argument("-e", "--except", nargs='*', dest='excepts', default=[])

    def handle(self, *args, **options):
        self.day = options.get('day', None)
        self.reset = options.get('reset', False)
        self.excepts = options.get('excepts', [])
        collections = list(KlineModel().database.list_collection_names(
        filter={"name": {"$regex": r"(\d{4}_\d{2}_\d{2})_([^_]+)_depth"}}))
        collections.sort()
        collectionBySymbol = {}
        for collection in collections:

            rg = r"(?P<date>\d{4}_\d{2}_\d{2})_(?P<symbol>[^_]+)_depth"
            match_object = re.match(rg, collection)
            symbol = match_object.group('symbol')
            date = match_object.group('date')
            if not symbol in collectionBySymbol:
                collectionBySymbol[symbol] = []
            collectionBySymbol[symbol].append({
                'date': date,
                'collection': collection
            })

        processes = []
        optionDay = f"-d{self.day}" if self.day is not None else ''
        optionReset = f"--reset" if self.reset else ''
        for symbol in collectionBySymbol:
            if(symbol in self.excepts): continue
            print(f"Run process orderbook {symbol}")
            pro = subprocess.Popen(f'python /home/ubuntu/linhvhv/coin_monitor/manage.py process_orderbook -s{symbol} {optionDay} {optionReset} > /home/ubuntu/linhvhv/coin_monitor/logs/process_orderbook_{symbol}.log', shell=True)
            processes.append(pro)
            if(len(processes) >= 5):
                for proc in processes:
                    proc.wait()
                processes = []

    




        


    





        
        
        
        

    
        
        





        

        

        







        

        


    