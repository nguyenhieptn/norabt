import json
from time import time
import requests
from Console.Helper.Control import Ctrl
from Console.Helper.Defaults import *
from Console.Helper.Reply import Reply

def scanNeedData(strategy, defaultSymbol, result, defaultFrame={"1m":0}):
    if(not isset(result, defaultSymbol)):
        result[defaultSymbol] = defaultFrame
    if(type(strategy) is list):
        for item in strategy:
            scanNeedData(item, defaultSymbol, result, defaultFrame)
    if(type(strategy) is dict):
        if(isset(strategy, 'frame')):
            symbol = get(strategy, 'symbol', defaultSymbol)
            #get all index
            index = int(get(strategy, 'index', 0))
            startIndex = int(get(strategy, 'start_index', 0))
            if(index > startIndex): index = startIndex
            stopIndex = int(get(strategy, 'stop_index', 0))
            if(index > stopIndex): index = stopIndex

            frame = strategy['frame']
            if(not isset(result, symbol)):
                result[symbol] = {frame:index, **defaultFrame}
            else:
                if(not isset(result[symbol], frame)):
                    result[symbol][frame] = index
                else: 
                    if(result[symbol][frame] >= index):
                        result[symbol][frame] = index
        else:
            for key in strategy:
                scanNeedData(strategy[key], defaultSymbol, result, defaultFrame)

def scanDependSymbol(strategy, defaultSymbol, result):
    if(type(strategy) is list):
        for item in strategy:
            scanDependSymbol(item, defaultSymbol, result)
    if(type(strategy) is dict):
        if(isset(strategy, 'symbol')):
            result[strategy['symbol']] = True
        else:
            for key in strategy:
                scanDependSymbol(strategy[key], defaultSymbol, result)

def scanDataLeng(strategy):
    leng = 0
    if(type(strategy) is list):
        for item in strategy:
            scanLeng = scanDataLeng(item)
            if(leng < scanLeng): leng = scanLeng
    if(type(strategy) is dict):
        if(isset(strategy, 'frame')):
            scanLeng = -Number(get(strategy,'index', 0)) + 1
            if(leng < scanLeng): leng = scanLeng
            scanLeng = -Number(get(strategy,'stop_index', 0)) + 1
            if(leng < scanLeng): leng = scanLeng
            scanLeng = -Number(get(strategy,'start_index', 0)) + 1
            if(leng < scanLeng): leng = scanLeng
        else:
            for key in strategy:
                scanLeng = scanDataLeng(strategy[key])
                if(leng < scanLeng): leng = scanLeng
    return leng

def findStrategy(strategy, elementType):
    if(type(strategy) is list):
        for item in strategy:
            if (findStrategy(item, elementType)): return True
    if(type(strategy) is dict):
        if(isset(strategy, 'type')):
            if(strategy['type'] == elementType): return True
        
        for key in strategy:
            if (findStrategy(strategy[key], elementType)): return True

    return False

getPrecisionResult = None
def getPrecision(symbol):
    global getPrecisionResult
    if(getPrecisionResult is None):
        
        savePrecision = Ctrl.get('getPrecisionResult', None)
        if(not savePrecision is None ): savePrecision = json.loads(savePrecision)
        if(savePrecision is None or savePrecision['time'] < (time() - 86400)):
            getPrecisionResult = {}
            print("Get exchange info")
            result = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo')
            result = result.json()

            if(isset(result, 'symbols')):
                datas = result['symbols']
                for data in datas:
                    getPrecisionResult[data['symbol']] = {
                        'price' : int(data['pricePrecision']),
                        'quantity': int(data['quantityPrecision'])
                    }

                    if(isset(data, 'filters')):
                        filters = data['filters']
                        for f in filters:
                            if(isset(f, 'tickSize')):
                                getPrecisionResult[data['symbol']]['tickSize'] = float(f['tickSize'])
                                break

            Ctrl.set('getPrecisionResult', json.dumps({
                'time': int(time()),
                'data': getPrecisionResult
            }))
        else:
            getPrecisionResult = savePrecision['data']
    
    if(isset(getPrecisionResult, symbol)): return getPrecisionResult[symbol]
    return False



def compare(element, calculator, data):
    firstNumber = calculator(element[0], data)
    formula = element[1]
    secondsNumber = calculator(element[2], data)

    if(not firstNumber['result']):
        return firstNumber
    if(not secondsNumber['result']):
        return secondsNumber

    log = firstNumber['message'] + ' ' + formula + ' ' + secondsNumber['message']

    firstNumber = firstNumber['data']
    secondsNumber = secondsNumber['data']

    if(firstNumber is None or secondsNumber is None or firstNumber == '' or secondsNumber == ''):
        return Reply.make(True, log, None)
    if(formula == '='):
        return Reply.make(True, log, firstNumber == secondsNumber)
    elif(formula == '>'):
        return Reply.make(True, log, firstNumber > secondsNumber)
    elif(formula == '<'):
        return Reply.make(True, log, firstNumber < secondsNumber)
    elif(formula == '>='):
        return Reply.make(True, log, firstNumber >= secondsNumber)
    elif(formula == '<='):
        return Reply.make(True, log, firstNumber <= secondsNumber)
    elif(formula == '!='):
        return Reply.make(True, log, firstNumber != secondsNumber)
    else:
        return Reply.make(False, "Please define formula " + formula)

def compareAnd(conditions, calculator, data):
    logs = []
    for condition in conditions:
        if(type(condition) is list):
            if(len(condition) == 3 and condition[1] in ['<', '>', '=', '>=', '<=', '!=']):
                result = compare(condition, calculator, data)
                if(not result['result']):
                    return result
            else:
                result = compareOr(condition, calculator, data)
                if(not result['result']):
                    return result
            logs.append(result['message'])
            if(result['data'] is None):
                return Reply.make(True, ' AND '.join(logs), None)
            if(result['data'] is False):
                return Reply.make(True, ' AND '.join(logs), False)
        else:
            return Reply.make(False, 'And condition must be an array')

    return Reply.make(True, ' AND '.join(logs), True)

def compareOr(conditions, calculator, data):
    logs = []
    for condition in conditions:
        result = compareAnd(condition, calculator, data)
        if(not result['result']):
            return result
        logs.append(result['message'])
        if(result['data'] is None):
            return Reply.make(True, ' OR '.join(logs), None)
        if(result['data'] is True):
            return Reply.make(True, ' OR '.join(logs), True)
    return Reply.make(True, ' OR '.join(logs), False)

def scanColumn(strategy, result):
    if(type(strategy) is list):
        for item in strategy:
            scanColumn(item, result)
    if(type(strategy) is dict):
        if(isset(strategy, 'type') and isset(strategy, 'column')):
            if(not isset(result, strategy['type'])): result[strategy['type']] = {'timestamp': 1, 'symbol':1}
            result[strategy['type']][strategy['column']] = 1

        else:
            for key in strategy:
                scanColumn(strategy[key], result)



