import subprocess
from threading import Thread
from dateutil import tz

from django.core.management.base import BaseCommand
from helper.Defaults import *
from helper.Data import *

from helper.Defaults import *




VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'Crawl kline 1m BTCUSDT, BTCUSDT_PERP, ETHUSDT'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        parser.add_argument("-d","--day", nargs='?', default=None, type=str)
        parser.add_argument("--reset", action='store_true', default=False)
        parser.add_argument("-e", "--except", nargs='*', dest='excepts', default=[])
        parser.add_argument("--exchange", nargs='?', default='future', type=str)

    def handle(self, *args, **options):
        self.day = options.get('day', None)
        self.reset = options.get('reset', False)
        self.exchange = options.get('exchange', "future")
        self.excepts = options.get('excepts', [])
        
        symbols = self.getAllSymbols()

        self.total = len(symbols)
        self.done = 0
        # symbols = ['RVNUSDT']   
        optionDay = f"-d{self.day}" if self.day is not None else ''
        optionReset = f"--reset" if self.reset else ''
        threads = list()
        for symbol in symbols:
            if(symbol in self.excepts): continue
            thread = Thread(target=self.openProc, args=(symbol, optionDay, optionReset))
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
            sleep(0.1)
            
        print(f"Process kline 1m {self.total} symbols were done.")    
        
    def openProc(self, symbol, optionDay, optionReset):
        print(f"Start process kline 1m {symbol}")
        pro = subprocess.Popen(f'python /home/ubuntu/linhvhv/coin_monitor/manage.py process_kline_1m_custom -s{symbol} -e {self.exchange} {optionDay} {optionReset} > /home/ubuntu/linhvhv/coin_monitor/logs/process_kline1m_{symbol}.log', shell=True)
        pro.wait()
        self.done += 1
        print(f"Process kline 1m {symbol} done {self.done}/{self.total}")

    def getAllSymbols(self):
        symbols = ['BTCUSDT','BTCUSDT_PERP', 'ETHUSDT']
        return symbols
        


        

    




        


    





        
        
        
        

    
        
        





        

        

        







        

        


    