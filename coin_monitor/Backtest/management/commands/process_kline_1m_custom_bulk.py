import subprocess
import sys
from threading import Thread
from pathlib import Path
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
        parser.add_argument("--stop", nargs='?', default=None, type=str)
        parser.add_argument("--reset", action='store_true', default=False)
        parser.add_argument("-e", "--except", nargs='*', dest='excepts', default=[])
        parser.add_argument("--exchange", nargs='?', default='future', type=str)
        parser.add_argument("-s", "--symbols", nargs='*', default=None)
        parser.add_argument("--max-threads", nargs='?', default=3, type=int)
        parser.add_argument("--db", nargs='?', default='backtest_data_1m_custom', type=str)
        parser.add_argument("--frames", nargs='*', default=None)

    def handle(self, *args, **options):
        self.day = options.get('day', None)
        self.reset = options.get('reset', False)
        self.stop_day = options.get('stop', None)
        self.exchange = options.get('exchange', "future")
        self.excepts = options.get('excepts', [])
        self.max_threads = max(1, options.get('max_threads', 3))
        self.db = options.get('db', 'backtest_data_1m_custom')
        self.frames = options.get('frames')
        
        symbols = options.get('symbols') or self.getAllSymbols()
        symbols = [symbol.upper() for symbol in symbols]

        self.total = len(symbols)
        self.done = 0
        # symbols = ['RVNUSDT']   
        optionDay = f"-d{self.day}" if self.day is not None else ''
        optionReset = f"--reset" if self.reset else ''
        optionStop = f"--stop={self.stop_day}" if self.stop_day is not None else ''
        threads = list()
        for symbol in symbols:
            if(symbol in self.excepts): continue
            thread = Thread(target=self.openProc, args=(symbol, optionDay, optionReset, optionStop))
            threads.append(thread)

        max_threads = self.max_threads
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
        
    def openProc(self, symbol, optionDay, optionReset, optionStop):
        print(f"Start process kline 1m {symbol}")
        base_dir = Path(__file__).resolve().parents[3]
        log_file = base_dir / "logs" / f"process_kline1m_{symbol}.log"
        cmd = [
            sys.executable,
            str(base_dir / "manage.py"),
            "process_kline_1m_custom",
            f"-s{symbol}",
            "-e",
            self.exchange,
        ]
        if optionDay:
            cmd.append(optionDay)
        if optionReset:
            cmd.append(optionReset)
        if optionStop:
            cmd.append(optionStop)
        cmd.extend(["--db", self.db])
        if self.frames:
            cmd.append("--frames")
            cmd.extend([frame.lower() for frame in self.frames])
        with open(log_file, "w") as log:
            pro = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        pro.wait()
        self.done += 1
        print(f"Process kline 1m {symbol} done {self.done}/{self.total}")

    def getAllSymbols(self):
        symbols = ['BTCUSDT','BTCUSDT_PERP', 'ETHUSDT']
        return symbols
        


        

    




        


    





        
        
        
        

    
        
        





        

        

        







        

        


    
