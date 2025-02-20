import subprocess
from threading import Thread
from dateutil import tz

from django.core.management.base import BaseCommand
from helper.Defaults import *
from helper.Data import *

from helper.Defaults import *




VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'Crawl kline 1m'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        parser.add_argument("-d","--day", nargs='?', default=None, type=str)
        parser.add_argument("-s", "--symbols", nargs='*', dest='symbols', default=[], type=str)

    def handle(self, *args, **options):
        self.day = options.get('day', None)
        self.symbols = options.get('symbols', [])
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
            symbols=self.getAllSymbols()
        else:
            symbols = self.symbols
                
        optionDay = f"-d{self.day}" if self.day is not None else ''
        threads = list()
        for symbol in symbols:
            thread = Thread(target=self.openProc, args=(symbol, optionDay,))
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
            
        print("Process update busd 1m all symbols were done.")  


    def openProc(self, symbol, optionDay):
        print(f"Process update busd 1m {symbol}")
        pro = subprocess.Popen(f'python /home/ubuntu/linhvhv/coin_monitor/manage.py process_busd_1m_update -s{symbol} {optionDay}> /home/ubuntu/linhvhv/coin_monitor/logs/update_busd_1m_{symbol}.log', shell=True)
        pro.wait()        
        print(f"Process update busd 1m {symbol} done")


    def getAllSymbols(self):
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        request = requests.get(url)
        data = request.json()  
        # print(data)      
        symbolData = data['symbols']
        symbols = list()
        for symbolItem in symbolData:
            if symbolItem["quoteAsset"] == 'USDT':
                symbols.append(symbolItem['symbol'])
        return symbols
        


        

    




        


    





        
        
        
        

    
        
        





        

        

        







        

        


    