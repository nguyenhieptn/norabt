import json
from time import time
import requests
from Console.Helper.Control import Ctrl
from Console.Helper.Defaults import *
from Console.Helper.Reply import Reply

def scanNeedData(strategy, defaultSymbol, result, defaultFrame={"1m":0}):
    '''
    Find all symbol and requrire data from strategy
    ```
    result: {
        kline: {1m: 0, 3m:1},
        busd: 0
        orderbook: 0
    }
    ```
    '''
    if(not isset(result, defaultSymbol)):
        result[defaultSymbol] = {'kline': {**defaultFrame}}

    if(type(strategy) is list):
        for item in strategy:
            scanNeedData(item, defaultSymbol, result, defaultFrame)
    if(type(strategy) is dict):
        if(isset(strategy, 'frame') and not isset(strategy, 'type')):
            symbol = get(strategy, 'symbol', defaultSymbol)
            # symbol = calculateSymbol(symbol, defaultSymbol)
            #get all index
            index = int(get(strategy, 'index', 0))
            startIndex = int(get(strategy, 'start_index', 0))
            if(index > startIndex): index = startIndex
            stopIndex = int(get(strategy, 'stop_index', 0))
            if(index > stopIndex): index = stopIndex

            frame = strategy['frame']

            if(not isset(result, symbol)):
                result[symbol]={}
            
            if(not isset(result[symbol], 'kline')):
                result[symbol]['kline'] = {frame:index, **defaultFrame}

            if(not isset(result[symbol]['kline'], frame)):
                result[symbol]['kline'][frame] = index
            else: 
                if(result[symbol]['kline'][frame] >= index):
                    result[symbol]['kline'][frame] = index

        elif(isset(strategy, 'type') and strategy['type'] == 'BUSD'):
            symbol = get(strategy, 'symbol', defaultSymbol)
            # symbol = calculateSymbol(symbol, defaultSymbol)
            #get all index
            index = int(get(strategy, 'index', 0))

            if(not isset(result, symbol)):
                result[symbol]={}
            
            if(not isset(result[symbol], 'busd')):
                result[symbol]['busd'] = index
            
            if(result[symbol]['busd'] >= index):
                result[symbol]['busd'] = index

        elif(isset(strategy, 'type') and strategy['type'] == 'OrderBook'):
            symbol = get(strategy, 'symbol', defaultSymbol)
            # symbol = calculateSymbol(symbol, defaultSymbol)
            #get all index
            index = int(get(strategy, 'index', 0))
            if(not isset(result, symbol)):
                result[symbol]={}
            
            if(not isset(result[symbol], 'orderbook')):
                result[symbol]['orderbook'] = index
            
            if(result[symbol]['orderbook'] >= index):
                result[symbol]['orderbook'] = index

        elif(isset(strategy, 'type') and strategy['type'] == 'Pressure'):
            symbol = get(strategy, 'symbol', defaultSymbol)
            symbol = calculateSymbol(symbol, defaultSymbol)
            #get all index
            index = int(get(strategy, 'index', 0))
            if(not isset(result, symbol)):
                result[symbol]={}
            
            if(not isset(result[symbol], 'pressure')):
                result[symbol]['pressure'] = index
            
            if(result[symbol]['pressure'] >= index):
                result[symbol]['pressure'] = index

        else:
            for key in strategy:
                scanNeedData(strategy[key], defaultSymbol, result, defaultFrame)

def updateNeedData(totalNeed, childNeed):
    '''
    Mergle all require data of all Campaign and get the lowest index
    '''
    if(type(childNeed) is dict):
        for key in childNeed:
            if(not isset(totalNeed, key)):
                totalNeed[key] = childNeed[key]
            else:
                if(type(childNeed[key]) is dict):
                    updateNeedData(totalNeed[key], childNeed[key])
                elif(isNumeric(childNeed[key]) and totalNeed[key] > childNeed[key]):
                    totalNeed[key] = childNeed[key]

def scanDependSymbol(strategy, defaultSymbol, result):
    if(type(strategy) is list):
        for item in strategy:
            scanDependSymbol(item, defaultSymbol, result)
    if(type(strategy) is dict):
        if(isset(strategy, 'frame')):
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


ftxAndBinance = ['1INCH', 'AAVE', 'ADA', 'ALGO', 'ALICE', 'ALPHA', 'APE', 'AR', 'ATOM', 'AUDIO', 'AVAX', 'AXS', 'BAL', 'BAND', 'BAT', 'BCH', 'BNB', 'BTC', 'C98', 'CELO', 'CHR', 'CHZ', 'COMP', 'CRV', 'CVC', 'CVX', 'DASH', 'DEFI', 'DENT', 'DOGE', 'DOT', 'DYDX', 'EGLD', 'ENJ', 'ENS', 'EOS', 'ETC', 'ETH', 'FIL', 'FLM', 'FLOW', 'FTM', 'FTT', 'GAL', 'GALA', 'GMT', 'GRT', 'HBAR', 'HNT', 'HOT', 'ICP', 'ICX', 'IMX', 'IOST', 'IOTA', 'JASMY', 'KAVA', 'KNC', 'KSM', 'LDO', 'LINA', 'LINK', 'LRC', 'LTC', 'LUNA2', 'MANA', 'MATIC', 'MKR', 'MTL', 'NEAR', 'NEO', 'OMG', 'ONE', 'ONT', 'OP', 'PEOPLE', 'QTUM', 'RAY', 'REEF', 'REN', 'ROSE', 'RSR', 'RUNE', 'RVN', 'SAND', 'SC', 'SKL', 'SNX', 'SOL', 'SPELL', 'SRM', 'STG', 'STMX', 'STORJ', 'SUSHI', 'SXP', 'THETA', 'TLM', 'TOMO', 'TRX', 'UNI', 'VET', 'WAVES', 'XEM', 'XLM', 'XMR', 'XRP', 'XTZ', 'YFI', 'ZEC', 'ZIL', 'ZRX']
def ftx2binance(symbol:str):
    """Convert FTX symbol to Binance

    Args:
        symbol (str): FTX symbol. Ex BTC-PERP

    Raises:
        Exception: The symbol is not exists in Binance

    Returns:
        str: The symbol in Binance
    """
    _symbol = symbol[0:-5]
    if _symbol in ftxAndBinance:    
        return f"{_symbol}USDT"
    specialSymbolMapping = {
        "LUNC-PERP": "1000LUNCUSDT",
        "SHIB-PERP": "1000SHIBUSDT"        
    }
    if symbol in specialSymbolMapping:
        return specialSymbolMapping[symbol]

    raise Exception(f"Symbol {symbol} is not exits in Binance")

def binance2ftx(symbol:str):
    """Convert Binance symbol to FTX

    Args:
        symbol (str): The symbol in Binance

    Raises:
        Exception: The symbol is not exists in FTX

    Returns:
        str: The symbol in FTX
    """
    _symbol = symbol[0:-4]
    if _symbol in ftxAndBinance:
        return f"{_symbol}-PERP"    
    specialSymbolMapping = {
        "1000LUNCUSDT": "LUNC-PERP",
        "1000SHIBUSDT": "SHIB-PERP"
    }
    if symbol in specialSymbolMapping:
        return specialSymbolMapping[symbol]
    
    raise Exception(f"Symbol {symbol} is not exits in FTX")



def calculateSymbol(symbol:str, defaultSymbol:str):    
    """calculate symbol

    Args:
        symbol (str): symbol
        defaultSymbol (str): default symbol

    Returns:
        str: symbol
    """
    if(symbol == 'ftx2binance'): symbol = ftx2binance(defaultSymbol)
    if(symbol == 'binance2ftx'): symbol = binance2ftx(defaultSymbol)
    return symbol