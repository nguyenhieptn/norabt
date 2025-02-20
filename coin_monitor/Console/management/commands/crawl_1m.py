from datetime import datetime
from math import floor
import os

from django.core.management.base import BaseCommand
import requests
import json
from threading import Thread
import psutil
from helper.Defaults import *



class Command(BaseCommand):
    help = 'Crawl Kline data 1m'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self.using = 'data_binance'
        self.spot = Spot()
        self.future = Future()

    def add_arguments(self, parser):
        parser.add_argument("--symbols", nargs="*", default=None)

    
    def handle(self, *args, **options):

        symbols = options['symbols']
        
        spot_symbols = self.spot_symbols()
        if(symbols is None):
            future_symbols = self.future_symbols()
        else:
            future_symbols = symbols #type: list
        

        print("Crawl data of:"+ str(len(future_symbols)))
        print(future_symbols)
        
        specialPair = {
            '1000SHIBUSDT': 'SHIBUSDT',
            '1000XECUSDT': 'XECUSDT'
        }

        for futureSymbol in future_symbols:
            futureSymbol = futureSymbol.upper()
            print(f"Crawl data {futureSymbol}")
            
            try:
                result = FutureCandle1M.objects.using(self.using).raw(f"ALTER TABLE future_candle_1m ADD PARTITION (PARTITION p{futureSymbol} VALUES IN ('{futureSymbol}'))")
                list(result)
            except:
                pass
            
            futureThread = Thread(target=self.future_crawl, args=[futureSymbol])
            futureThread.start()
            spotSymbol = None
            if(isset(specialPair, futureSymbol)): 
                spotSymbol = specialPair[futureSymbol]
            else:
                if(futureSymbol in spot_symbols):
                    spotSymbol = futureSymbol
            if(spotSymbol is not None):
                try:
                    result = SpotCandle1M.objects.using(self.using).raw(f"ALTER TABLE spot_candle_1m ADD PARTITION (PARTITION p{spotSymbol} VALUES IN ('{spotSymbol}'))")
                    list(result)
                except:
                    pass
               
                spotThread = Thread(target=self.spot_crawl, args=[spotSymbol])
                spotThread.start()
                spotThread.join()
            futureThread.join()


    def spot_crawl(self, symbol, startTime=None):

        if startTime is None:
            last_candle = SpotCandle1M.objects.using(self.using).filter(spot_1m_symbol=symbol).order_by('-spot_1m_close_time').first()  # type:SpotCandle1M
            if last_candle is not None:
                startTime = last_candle.spot_1m_close_time
            else:
                # first time
                startTime = 958113480000
        while True:
            data = self.spot.kline(symbol, startTime=startTime)
            if not data["status"]:
                print(f"Spot {symbol} is wrong format")
                break
            candles = data["data"]
            items = []
            for candle in candles:
                try:
                    items.append(SpotCandle1M(
                        spot_1m_symbol=symbol,
                        spot_1m_open_time=candle[0],
                        spot_1m_close_time=candle[6],
                        spot_1m_open=candle[1],
                        spot_1m_low=candle[3],
                        spot_1m_high=candle[2],
                        spot_1m_close=candle[4],
                        spot_1m_volume=candle[5],
                    ))
                except Exception as ex:
                    print(ex)
                startTime = candle[6]
            if len(items) > 0:
                SpotCandle1M.objects.using(
                    self.using).bulk_create(items, 1000)
                print(f"{symbol} spot {str(datetime.fromtimestamp(floor(startTime/1000)))}", end='\r')
            else:
                break

    def future_crawl(self, symbol, startTime=None):
        if startTime is None:
            last_candle = FutureCandle1M.objects.using(self.using).filter(future_1m_symbol=symbol).order_by('-future_1m_close_time').first()  # type: FutureCandle1M
            if last_candle is not None:
                startTime = last_candle.future_1m_close_time
            else:
                # first time
                startTime = 958113480000
        while True:
            data = self.future.kline(symbol, startTime=startTime)
            if not data["status"]:
                print(f"Future {symbol} is wrong format")
                break
            candles = data["data"]
            items = []
            for candle in candles:

                items.append(FutureCandle1M(
                    future_1m_symbol=symbol,
                    future_1m_open_time=candle[0],
                    future_1m_close_time=candle[6],
                    future_1m_open=candle[1],
                    future_1m_low=candle[3],
                    future_1m_high=candle[2],
                    future_1m_close=candle[4],
                    future_1m_volume=candle[5],
                ))
                startTime = candle[6]
            if len(items) > 0:
                FutureCandle1M.objects.using(
                    self.using).bulk_create(items, 1000)
                print(f"{symbol} future {str(datetime.fromtimestamp(floor(startTime/1000)))}", end='\r')
            else:
                break

    def spot_symbols(self):
        data = self.spot.exchangeInfo()
        symbols = []
        if data["status"]:
            data = data['data']
            # print(data)
            print('symbols' in data)
            if 'symbols' in data:
                for symbol in data['symbols']:
                    if 'symbol' in symbol:
                        symbols.append(symbol['symbol'])
        symbols = list(filter(lambda x: 'USDT' in x, symbols))
        return symbols

    def future_symbols(self):
        data = self.future.exchangeInfo()
        symbols = []
        if data["status"]:
            data = data['data']
            if 'symbols' in data:
                for symbol in data['symbols']:
                    if 'symbol' in symbol:
                        symbols.append(symbol['symbol'])
        symbols = list(filter(lambda x: 'USDT' in x, symbols))
        return symbols

    def chunks(self, arr, amount):
        if amount < 1:
            raise ValueError('amount must be positive integer')
        chunk_len = len(arr) // amount
        leap_parts = len(arr) % amount
        remainder = amount // 2  # make it symmetrical
        i = 0
        while i < len(arr):
            remainder += leap_parts
            end_index = i + chunk_len
            if remainder >= amount:
                remainder -= amount
                end_index += 1
            yield arr[i:end_index]
            i = end_index


class Spot:
       # time frame 1m, 3m, 5m, 15m, 30m, 1h, 2h,4h,6h,8h,12h,1d,3d,1w,1M
    def __init__(self):
        self.base_uri = 'https://api.binance.com'

    def get(self, path, params=None, headers=None):
        if headers is None:
            headers = dict()
        if params is None:
            params = dict()

        request = requests.get('{}{}'.format(
            self.base_uri, path), params=params, headers=headers)
        response = json.loads(request.content)
        if 'code' in response and 'msg' in response:
            return {
                'status': False,
                    'msg': response['msg']
            }
        return {
            'status': True,
                'data': response
        }

    def kline(self, symbol='BTCUSDT', interval='1m', startTime=None, endTime=None, limit=1000):
        path = '/api/v3/klines'
        params = dict(symbol=symbol.upper(), interval=interval,
                      startTime=startTime, endTime=endTime, limit=limit)
        response = self.get(path, params)
        return response

    def exchangeInfo(self):
        path = '/api/v3/exchangeInfo'
        response = self.get(path)
        return response


class Future:
    def __init__(self):
        self.base_uri = 'https://fapi.binance.com'

    def get(self, path, params=None, headers=None):
        if headers is None:
            headers = dict()
        if params is None:
            params = dict()

        request = requests.get('{}{}'.format(
            self.base_uri, path), params=params, headers=headers)
        response = json.loads(request.content)
        if 'code' in response and 'msg' in response:
            return {
                'status': False,
                    'msg': response['msg']
            }
        return {
            'status': True,
                'data': response
        }

    def kline(self, symbol='BTCUSDT', interval='1m', startTime=None, endTime=None, limit=1000):
        path = '/fapi/v1/klines'
        params = dict(symbol=symbol.upper(), interval=interval,
                      startTime=startTime, endTime=endTime, limit=limit)
        response = self.get(path, params)
        return response

    def exchangeInfo(self):
        path = '/fapi/v1/exchangeInfo'
        response = self.get(path)
        return response
