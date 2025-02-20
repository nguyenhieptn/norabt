from hashlib import md5
def dict2Id(dic: dict):
    keysArray = []
    for key in dic:
        keysArray.append(f"{key}:{dic[key]}")
    keysArray.sort()
    return md5('.'.join(keysArray).encode()).hexdigest()

def findElement(strategy, filter):
    filterResult = []
    if(type(strategy) is list):
        for item in strategy:
            subResult = findElement(item, filter)
            filterResult += subResult
    if(type(strategy) is dict):
        
        if(filter(strategy)):
            filterResult.append(strategy)
        
        for key in strategy:
            subResult = findElement(strategy[key], filter)
            filterResult += subResult
            
    return filterResult

import re

def fillStrategy(strategy, params:dict={}):
    if(type(strategy) is dict):
        for key in strategy:
            if(type(strategy[key]) is dict or type(strategy[key])):
                fillStrategy(strategy[key], params)
            if(type(strategy[key]) is str):
                regex = r"\#([^\#]+)\#"
                match = re.search(regex, strategy[key])
                if(match is not None):
                    matchParams = match.groups()[0]
                    strategy[key] = params.get(matchParams, None)
    if(type(strategy) is list):
        for key,value in enumerate(strategy):
            if(type(strategy[key]) is dict or type(strategy[key])):
                fillStrategy(strategy[key], params)
            if(type(strategy[key]) is str):
                regex = r"\#([^\#]+)\#"
                match = re.search(regex, strategy[key])
                if(match is not None):
                    matchParams = match.groups()[0]
                    strategy[key] = params.get(matchParams, None)

"""
Update new data to check data
@param checkData dict {"BTCUSDT": {"1m":[],...}}
@param symbol Str
@param latest dict {"1m":{}, ....}
"""
def updateKlineData(checkData, lastest, dataLeng=30):
    for symbol in lastest:
        if(symbol not in checkData): checkData[symbol] = {}
        for frame in lastest[symbol]:
            closeTimeColName = 'close_time'
            candle = lastest[symbol][frame]
            if(frame not in checkData[symbol]):
                checkData[symbol][frame] = [candle]
            else:
                frameData:list = checkData[symbol][frame]
                if(int(frameData[-1][closeTimeColName]) < int(candle[closeTimeColName])):
                    frameData.append(candle)
                    if(len(frameData) > dataLeng):
                        frameData.pop(0)
                else:
                    frameData[-1] = candle
    return checkData
                
    

    
