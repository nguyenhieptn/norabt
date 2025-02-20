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
        filter={"name": {"$regex": r"(\d{4}_\d{2}_\d{2})_([^_]+)_kline_1m"}}))
        collections.sort()
        collectionBySymbol = {}
        for collection in collections:

            rg = r"(?P<date>\d{4}_\d{2}_\d{2})_(?P<symbol>[^_]+)_kline_1m"
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
        threads = list()
        max_threads = 10
        count = max_threads
        for symbol in collectionBySymbol:
            if(symbol in self.excepts): continue
            thread = Thread(target=self.openProc, args=(symbol, optionDay, optionReset))
            threads.append(thread)
        start = 0
        while count > 0:
            count = 0
            for index, _thread in enumerate(threads):
                _thread: Thread
                if _thread is not None and _thread.is_alive():  
                    count += 1
                else:
                    if index < start:
                        threads[index] = None
                        continue
                    if count < max_threads:
                        _thread.start()
                        start += 1
                        count += 1
            
        print("Process kline all symbols were done.")  

    def openProc(self, symbol, optionDay, optionReset):
        print(f"Run process kline {symbol}")
        pro = subprocess.Popen(f'python /home/ubuntu/linhvhv/coin_monitor/manage.py process_kline -s{symbol} {optionDay} {optionReset} > /home/ubuntu/linhvhv/coin_monitor/logs/process_kline_{symbol}.log', shell=True)
        pro.wait()
        print(f"Done process kline {symbol}")
    




        


    





        
        
        
        

    
        
        





        

        

        







        

        


    