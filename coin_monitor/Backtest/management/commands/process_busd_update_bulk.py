from datetime import datetime
import subprocess
import sys
from threading import Thread
from dateutil import tz

from django.core.management.base import BaseCommand
from helper.Defaults import *
from helper.Data import *

from helper.Defaults import *
from models.Mongo.BusdModel import BusdModel


VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'Generate testnet chart'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        parser.add_argument("-db","--database", nargs='?', required=False, default='backtest_data', type=str)
        parser.add_argument("-s", "--symbols", nargs='*', dest='symbols', default=[], type=str)
        parser.add_argument("-d","--day", nargs='?', default=None, type=str)
        parser.add_argument("-sd","--sday", nargs='?', default=None, type=str)

    def handle(self, *args, **options):
        
        self.db = options.get('database', 'backtest_data')
        self.day = options.get('day', None)
        self.sday = options.get('sday', None)
        self.symbols = options.get('symbols', [])

        self.busdModel = BusdModel()
        if(len(self.symbols) == 0):
            symbols = [ 
                'BTCUSDT',
                'ADAUSDT',
                'ALGOUSDT',
                'AVAXUSDT',
                'BNBUSDT',
                'DOGEUSDT',
                'DOTUSDT',
                'ENJUSDT',
                'ETCUSDT',
                'ETHUSDT',
                'FTMUSDT',
                'LRCUSDT',
                'MANAUSDT',
                'MATICUSDT',
                'NEARUSDT',
                'ONEUSDT',
                'SANDUSDT',
                'SOLUSDT',
                'THETAUSDT',
            ]
            symbols = list(self.busdModel.collection.distinct('symbol'))
        else:
            symbols = self.symbols
        
        processes = []
        optionDb = f"-db {self.db}" if self.db is not None else ''
        optionDay = f"-d {self.day}" if self.day is not None else ''
        optionSDay = f"-sd {self.sday}" if self.sday is not None else ''
        
        threads = list()
        for symbol in symbols:
            thread = Thread(target=self.openProc, args=(symbol, optionDb, optionDay, optionSDay,))
            threads.append(thread)
        max_threads = 20
        
        count = max_threads
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
            
        print("Process update busd all symbols were done.") 


    def openProc(self, symbol, optionDb, optionDay, optionSDay):
        print(f"Process update busd {symbol}")
        pro = subprocess.Popen(f'python /home/ubuntu/linhvhv/coin_monitor/manage.py process_busd_update -s {symbol} {optionDb} {optionDay} {optionSDay} > /home/ubuntu/linhvhv/coin_monitor/logs/update_busd_{symbol}.log', shell=True)
        pro.wait()        
        print(f"Process update busd {symbol} done")


        


    





        
        
        
        

    
        
        





        

        

        







        

        


    