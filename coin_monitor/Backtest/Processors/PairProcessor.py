
from math import floor
from threading import Thread
from time import sleep, time
from datetime import datetime, timedelta
import requests
from helper.Indicator import rsi, ema, wma
from helper.Defaults import *
from helper.Data import *
from helper.Timer import *
from statistics import stdev, mean
from multiprocessing import Process

from pymongo import ASCENDING, DESCENDING

import pandas as pd

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')


class PairProcessor():

    
    def __init__(self, indicators = None, maxLength=None) -> None:
        
        
        
        if(indicators is None):
            lengths = [600, 1200, 2400, 3600]
            self.indicators = []
            for length in lengths:
                self.indicators += [
                    {"indicator":"sma", "source":"NET_F1B1_F2A1", "params": length},
                    {"indicator":"stdev", "source":"NET_F1B1_F2A1", "params": length},
                    {"indicator":"upper_band", "params": {'mid': f'sma_{length}_NET_F1B1_F2A1', 'stdev': f'stdev_{length}_NET_F1B1_F2A1'}, 'name':f't{length}_upper_band'},
                    {"indicator":"lower_band", "params": {'mid': f'sma_{length}_NET_F1B1_F2A1', 'stdev': f'stdev_{length}_NET_F1B1_F2A1'}, 'name':f't{length}_lower_band'},
                    {"indicator":"upper_band", "params": {'mid': f'sma_{length}_NET_F1B1_F2A1', 'stdev': f'stdev_{length}_NET_F1B1_F2A1', 'multi':1.5}, 'name':f't{length}_upper_band_1d5'},
                    {"indicator":"lower_band", "params": {'mid': f'sma_{length}_NET_F1B1_F2A1', 'stdev': f'stdev_{length}_NET_F1B1_F2A1', 'multi':1.5}, 'name':f't{length}_lower_band_1d5'},
                    
                    {"indicator":"sma", "source":"NET_F1A1_F2B1", "params": length},
                    {"indicator":"stdev", "source":"NET_F1A1_F2B1", "params": length},
                    {"indicator":"upper_band", "params": {'mid': f'sma_{length}_NET_F1A1_F2B1', 'stdev': f'stdev_{length}_NET_F1A1_F2B1'}, 'name':f'n{length}_upper_band'},
                    {"indicator":"lower_band", "params": {'mid': f'sma_{length}_NET_F1A1_F2B1', 'stdev': f'stdev_{length}_NET_F1A1_F2B1'}, 'name':f'n{length}_lower_band'},
                    {"indicator":"upper_band", "params": {'mid': f'sma_{length}_NET_F1A1_F2B1', 'stdev': f'stdev_{length}_NET_F1A1_F2B1', 'multi':1.5}, 'name':f'n{length}_upper_band_1d5'},
                    {"indicator":"lower_band", "params": {'mid': f'sma_{length}_NET_F1A1_F2B1', 'stdev': f'stdev_{length}_NET_F1A1_F2B1', 'multi':1.5}, 'name':f'n{length}_lower_band_1d5'},
                ]
            self.maxLeng = max(lengths)*2
        else:
            self.indicators = indicators
            self.maxLeng = maxLength
        
        # self.indicators = [
        #     {"indicator":"sma", "source":"NET_F1B1_F2A1", "params": 300},
        #     {"indicator":"stdev", "source":"NET_F1B1_F2A1", "params": 300},
        #     {"indicator":"upper_band", "params": {'mid': 'sma_300_NET_F1B1_F2A1', 'stdev': 'stdev_300_NET_F1B1_F2A1'}, 'name':'t_upper_band'},
        #     {"indicator":"lower_band", "params": {'mid': 'sma_300_NET_F1B1_F2A1', 'stdev': 'stdev_300_NET_F1B1_F2A1'}, 'name':'t_lower_band'},
            
        #     {"indicator":"sma", "source":"NET_F1A1_F2B1", "params": 300},
        #     {"indicator":"stdev", "source":"NET_F1A1_F2B1", "params": 300},
        #     {"indicator":"upper_band", "params": {'mid': 'sma_300_NET_F1A1_F2B1', 'stdev': 'stdev_300_NET_F1A1_F2B1'}, 'name':'n_upper_band'},
        #     {"indicator":"lower_band", "params": {'mid': 'sma_300_NET_F1A1_F2B1', 'stdev': 'stdev_300_NET_F1A1_F2B1'}, 'name':'n_lower_band'},
        # ]
        
        self.pairData = []
        


    def processData(self, data):
        self.pairData.append(data)
        if(len(self.pairData) > self.maxLeng): self.pairData.pop(0)
        self.updateIndicator(self.indicators)
        return self.pairData[-1]
    
    
    def processBlockData(self, datas):
        dataLeng = len(datas)
        if(dataLeng == 0): return []
        self.pairData = self.pairData[-self.maxLeng:] + datas
        pairDataDF = pd.DataFrame(self.pairData)
        fragment = 0
        for indicator in self.indicators:
            fragment += 1
            if(fragment > 10):
                pairDataDF = pairDataDF.copy()
                fragment = 0
                
            indicator:dict
            itype = indicator.get('indicator', None)
            obj = indicator.get('source', None)
            params = indicator.get('params', None)
            name = indicator.get('name', None)
            
            if(itype == 'sma'):
                N = params
                if(name is None): name = f'{itype}_{N}_{obj}'
                pairDataDF[name] = pairDataDF[obj].rolling(N).mean()
            
            elif(itype == 'stdev'):
                N = params
                if(name is None): name = f'{itype}_{N}_{obj}'
                pairDataDF[name] = pairDataDF[obj].rolling(N).std()
            
            elif(itype == 'upper_band'):
                midName = params['mid']     
                stdevName = params['stdev']
                multi = params.get('multi', 2)
                if(name is None): name = f'{itype}_{midName}_{str(multi).replace(".", "_")}std'
                pairDataDF[name] = pairDataDF[midName] + multi*pairDataDF[stdevName]

            elif(itype == 'lower_band'):
                midName = params['mid']     
                stdevName = params['stdev']
                multi = params.get('multi', 2)
                if(name is None): name = f'{itype}_{midName}_{str(multi).replace(".", "_")}std'
                pairDataDF[name] = pairDataDF[midName] - multi*pairDataDF[stdevName]
        
        pairDataDF = pairDataDF[-dataLeng:]
        return pairDataDF.to_dict(orient='records')
        
            
        
    
    
    def updateIndicator(self, indicators):
        
        if(len(self.pairData) < 2): return
        if(len(indicators) == 0): return

        for indicator in indicators:
            itype = indicator.get('indicator', None)
            obj = indicator.get('source', None)
            params = indicator.get('params', None)
            name = indicator.get('name', None)
            result = self.calIndicator(itype, obj, params, name)
            self.pairData[-1].update(result)
    
    
    def calIndicator(self, indicator, obj, params, name):
        
        if(indicator == 'sma'):
            N = params
            if(name is None): name = f'{indicator}_{N}_{obj}'
            historyValue = [get(candle,obj,None) for candle in self.pairData[-N:]]
            return {name: mean(historyValue)}
        
        elif(indicator == 'stdev'):
            N = params
            if(name is None): name = f'{indicator}_{N}_{obj}'
            historyValue = [get(candle,obj,None) for candle in self.pairData[-N:]]
            return {name: stdev(historyValue)}
        
        elif(indicator == 'upper_band'):
            lastData:dict = self.pairData[-1]
            midName = params['mid']     
            stdevName = params['stdev']
            multi = params.get('multi', 2)
            if(name is None): name = f'{indicator}_{midName}_{str(multi).replace(".", "_")}std'
            midVal = lastData.get(midName, None)
            stdevVal = lastData.get(stdevName, None)
            value = None
            if(midVal is not None and stdevVal is not None):
                value = midVal + multi*stdevVal
            return {name: value}

        elif(indicator == 'lower_band'):
            lastData:dict = self.pairData[-1]
            midName = params['mid']     
            stdevName = params['stdev']
            multi = params.get('multi', 2)
            if(name is None): name = f'{indicator}_{midName}_{str(multi).replace(".", "_")}std'
            midVal = lastData.get(midName, None)
            stdevVal = lastData.get(stdevName, None)
            value = None
            if(midVal is not None and stdevVal is not None):
                value = midVal - multi*stdevVal
            return {name: value}
            
        elif(indicator == 'ema'):
            N = params
            if(name is None): name = f'{indicator}_{N}_{obj}'
            p1Data = self.pairData[-2]
            lastData = self.pairData[-1]     
            periodValue = get(p1Data, name, None)
            objValue = get(lastData, obj, None)
            historyValue = None
            if(periodValue is None): historyValue = [get(candle,obj,None) for candle in self.pairData[-N:]]
            return {name: ema(periodValue, objValue, N, historyValue)}
        
        elif(indicator == 'rsi'):
            N = params
            if(name is None): name = f'{indicator}_{N}_{obj}'
            p1Data = self.pairData[-2]
            lastData = self.pairData[-1]     
            avgUName = f"avgU_{N}_{obj}"
            avgDName = f"avgD_{N}_{obj}"
            periodValue = get(p1Data, obj, None)
            periodAvgU = get(p1Data, avgUName, None)
            periodAvgD = get(p1Data, avgDName, None)
            objValue = get(lastData, obj, None)
            historyValue = None
            if(periodAvgU is None or periodAvgD is None): historyValue = [get(candle,obj,None) for candle in self.pairData[-N-1:]]
            result = rsi(periodValue, periodAvgU, periodAvgD, objValue, N, historyValue)
            return {
                name : result['rsi'],
                avgUName : result['avgU'],
                avgDName : result['avgD'],
            }
            
        elif(indicator == 'wma'):
            N = params
            if(name is None): name = f'{indicator}_{N}_{obj}'
            historyValue = [get(candle, obj, None) for candle in self.pairData[-N:]]
            return {name: wma(N, historyValue)}
        
        elif(indicator == 'macd'):
            fast = params['fast']
            slow = params['slow']
            if(name is None): name = f'{indicator}_{fast}_{slow}_{obj}'
            emaSlowName = f'ema_{slow}_{obj}'
            emaFastName = f'ema_{fast}_{obj}'
            slow = self.calIndicator('ema', obj, slow, emaSlowName)[emaSlowName]
            fast = self.calIndicator('ema', obj, fast, emaFastName)[emaFastName]
            if(slow is not None and fast is not None):
                macd = fast - slow
            else:
                macd = None
            return {
                name: macd,
                emaSlowName: slow,
                emaFastName: fast
            }
        elif(indicator == 'macdh'):
            
            lastData = self.pairData[-1]  
            fast = params['fast']
            slow = params['slow']
            signal = params['signal']
            if(name is None): name = f'{indicator}_{fast}_{slow}_{signal}_{obj}'
            macdName = f'macd_{fast}_{slow}_{obj}'
            signalName = f'ema_{signal}_{macdName}'

            macdResult = self.calIndicator('macd', obj, {"fast":fast, "slow":slow}, macdName)
            lastData[macdName] = macdResult[macdName]
            signal = self.calIndicator('ema', macdName, signal, signalName)[signalName]
            if(macdResult[macdName] is not None and signal is not None):
                macdh = macdResult[macdName] - signal
            else:
                macdh = None
            return {
                **macdResult,
                signalName: signal,
                name: macdh
            }
        
        
        
        




            










    


    


                
    


    
