from copy import deepcopy
import json
import re
from Console.Helper.Defaults import *
from Console.Models.Coin_lab import LabAccount, LabStrategies, LabStrategyContainer
from Console.Models.Wrappers.Lab.Coin_lab import LabCampaignsWrapper, LabResultsWrapper
from Console.Helper.Reply import Reply


def getAccount(id)->LabAccount:
    try:
        account = LabAccount.objects.get(lab_account_id=id)
        return account
    except Exception:
        return None

def getStrategy(id):
    try:
        strategy = LabStrategies.objects.filter(lab_strategy_id=id).values().first()
        return strategy
    except Exception as e:
        return None

def processLabChildStrategy(strategyid, optParams={}):
    strategy = getStrategy(strategyid)
    content = strategy['lab_strategy_content']
    if(content is None or content == ''):
        return {}
    
    for key in optParams:
        content = content.replace(key, str(optParams[key]))

    # Keltner processor columns encode decimal coefficients without a dot
    # (kup21_05, not kup21_0.5). Optimizer values remain real numbers such as
    # 0.5 so str2num can evaluate them safely; normalize only the column token
    # after all placeholders have been substituted.
    content = re.sub(r"(k(?:up|lo)\d+(?:\.\d+)?)_0\.(\d+)",
                     lambda m: f"{m.group(1)}_0{m.group(2)}", content)

    regex = r"\#[^\#]+\#"
    match = re.search(regex, content)
    if(not match is None):
        raise Exception("Can not find param in strategy: " + str(match[0]))

    content = json.loads(content)
   
    flows = {}

    for key in content:
        val = content[key]
        if(isset(val, 'type')):
            val['name'] = key
            flows[str(strategyid) + '--' + str(key)] = val

    for key in content:
        val = content[key]
        if(not isset(val, 'type')):
            for name in flows:
                flow = flows[name]
                if(not isset(flow, key)):
                    flow[key] = val

    for name in flows:
        flow = flows[name]
        flow['strategy'] = strategyid
        if(not isset(flow, 'takeprofit')):
            flow['takeprofit'] = strategy['lab_strategy_takeprofit']
        if(not isset(flow, 'stoploss')):
            flow['stoploss'] = strategy['lab_strategy_stoploss']
        if(not isset(flow, 'baseprofit')):
            flow['baseprofit'] = strategy['lab_strategy_baseprofit']
        if(not isset(flow, 'step_profit')):
            flow['step_profit'] = strategy['lab_strategy_stepprofit']
        if(not isset(flow, 'back_profit')):
            flow['back_profit'] = strategy['lab_strategy_backprofit']
        if(not isset(flow, 'baseprofit_baseon')):
            flow['baseprofit_baseon'] = strategy['lab_strategy_baseprofit_baseon']
        if(not isset(flow, 'timelife')):
            flow['timelife'] = strategy['lab_strategy_timelife']
        if(not isset(flow, 'interval')):
            flow['interval'] = strategy['lab_strategy_interval']
        if(not isset(flow, 'margin')):
            flow['margin'] = strategy['lab_strategy_margin']

    return flows


def processLabStrategy(strategyid, optParams={}):
    strategy = getStrategy(strategyid)
    
    if(strategy['lab_strategy_container']):
        flows = {}
        children = LabStrategyContainer.objects.filter(
            lab_stra_con_container=strategyid).order_by('lab_stra_con_weight')
        for child in children:
            childFlows = processLabChildStrategy(child.lab_stra_con_child, optParams)
            for name in childFlows:
                try:
                    blacklist = json.loads(child.lab_stra_con_blacklist)
                except Exception:
                    blacklist = []
                flow = childFlows[name]
                flow['container'] = strategyid
                flow['strategy_slot'] = child.lab_stra_con_slot
                flow['blacklist'] = blacklist
                flows[name] = flow

        for name in flows:
            flow = flows[name]
            if(not isset(flow, 'takeprofit')):
                flow['takeprofit'] = strategy['lab_strategy_takeprofit']
            if(not isset(flow, 'stoploss')):
                flow['stoploss'] = strategy['lab_strategy_stoploss']
            if(not isset(flow, 'baseprofit')):
                flow['baseprofit'] = strategy['lab_strategy_baseprofit']
            if(not isset(flow, 'step_profit')):
                flow['step_profit'] = strategy['lab_strategy_stepprofit']
            if(not isset(flow, 'back_profit')):
                flow['back_profit'] = strategy['lab_strategy_backprofit']
            if(not isset(flow, 'baseprofit_baseon')):
                flow['baseprofit_baseon'] = strategy['lab_strategy_baseprofit_baseon']
            if(not isset(flow, 'timelife')):
                flow['timelife'] = strategy['lab_strategy_timelife']
            if(not isset(flow, 'interval')):
                flow['interval'] = strategy['lab_strategy_interval']
            if(not isset(flow, 'margin')):
                flow['margin'] = strategy['lab_strategy_margin']

        return flows
    else:
        return processLabChildStrategy(strategyid, optParams)



"""
Update new data to check data
@param checkData dict {"BTCUSDT": {"1m":[],...}}
@param symbol Str
@param latest dict {"1m":{}, ....}
"""
def updateCheckData(checkData, symbol, lastest, dataLeng=30):
    if(not isset(checkData, symbol)):
        checkData[symbol] = {
            'kline': {},
            'busd': [],
            'orderbook': []
        }
    # print(json.dumps(lastest, default=str))

    if isset(lastest, 'kline'):
        for frame in lastest['kline']:

            closeTimeColName = 'close_time'
            candle = lastest['kline'][frame]
            if(not isset(checkData[symbol]['kline'], frame)):
                checkData[symbol]['kline'][frame] = [candle]
            else:
                frameData = checkData[symbol]['kline'][frame]
                if(not isset(frameData, 0)):
                    checkData[symbol]['kline'][frame].append(candle)
                elif(int(frameData[0][closeTimeColName]) < int(candle[closeTimeColName])):
                    checkData[symbol]['kline'][frame].insert(0, candle)
                    if(len(checkData[symbol]['kline'][frame]) > dataLeng):
                        checkData[symbol]['kline'][frame].pop()
                else:
                    checkData[symbol]['kline'][frame][0] = candle
                          
    if(isset(lastest, 'busd')):
        checkData[symbol]['busd'].insert(0, lastest['busd'])
        if(len(checkData[symbol]['busd']) > dataLeng):
            checkData[symbol]['busd'].pop()

    if(isset(lastest, 'orderbook')):
        checkData[symbol]['orderbook'].insert(0, lastest['orderbook'])
        if(len(checkData[symbol]['orderbook']) > dataLeng):
            checkData[symbol]['orderbook'].pop()


getPriorityIndexResult = None      
def getPriorityIndex(accountId):
    global getPriorityIndexResult
    if(not getPriorityIndexResult is None): return getPriorityIndexResult
    campaigns = LabCampaignsWrapper().filter({
        LabCampaignsWrapper.lab_campaign_account: accountId
    })
    priorityIndex = {}
    for campaign in campaigns:
        priorityIndex[campaign.lab_campaign_symbol] = float(campaign.lab_campaign_priority) if isNumeric(campaign.lab_campaign_priority) else 0
    getPriorityIndexResult = priorityIndex
    return getPriorityIndexResult


#compare leng of 2 leap string
def compareLeap(leap1, formula, leap2):
    leapLeng = {
        "15m": 15*60*1000,
        "1h": 60*60*1000,
        "4h": 4*60*60*1000,
        "1d": 24*60*60*1000
    }
    if(not isset(leapLeng, leap1) or not isset(leapLeng, leap2)):
        raise Exception("Not defined leap Leng " + str(leap1) + " " + str(leap2))
    if(formula == '='): return leapLeng[leap1] == leapLeng[leap2]
    if(formula == '>='): return leapLeng[leap1] >= leapLeng[leap2]
    if(formula == '<='): return leapLeng[leap1] <= leapLeng[leap2]
    if(formula == '>'): return leapLeng[leap1] > leapLeng[leap2]
    if(formula == '<'): return leapLeng[leap1] < leapLeng[leap2]
    raise Exception("Does not support leap formula")

#find out the shortest leap in the strategy
def getShortestLeap(strategy):
    shortest = None
    if(type(strategy) is dict):
        for key in strategy:
            item = strategy[key]
            if(type(item) is dict or type(item) is list): 
                leap = getShortestLeap(item)
                if(leap is None): continue
                if(shortest is None):
                    shortest = leap
                elif(compareLeap(shortest, ">=", leap)):
                    shortest = leap
            if(type(item) is str and key == "leap"):
                
                if(shortest is None):
                    shortest = item
                elif(compareLeap(shortest, ">=", item)):
                    shortest = item
        
    if(type(strategy) is list):
        for item in strategy:
            if(type(item) is dict or type(item) is list): 
                leap = getShortestLeap(item)
                if(leap is None): continue
                if(shortest is None):
                    shortest = leap
                elif(compareLeap(shortest, ">=", leap)):
                    shortest = leap
    return shortest

def simpleLeapCondition(condition):
    for key, cond in enumerate(condition):
        if(type(cond) is list and len(cond) == 3 and cond[1] in ['=', '>=', '<=', '>', '<', '!=']):
            if(isset(cond[0], 'leap')):
                if(isset(cond[0], 'symbol')): raise Exception("Leap only works on itself")
                if(isset(cond[0], 'type') and cond[0]['type'] != 'frame'): raise Exception("Leap only works on type frame")
                if(not isset(cond[0], 'column')): raise Exception("Not define colum in leap")
                if(cond[0]['column'] != 'low' and cond[0]['column'] != 'high'): raise Exception("Leap only works exactly on Low or High")
                if(cond[0]['column'] == 'low' and not cond[1] in ['<=', '<']): raise Exception("Leap only works exactly on Low <")
                if(cond[0]['column'] == 'high' and not cond[1] in ['>=', '>']): raise Exception("Leap only works exactly on High >")
                if(Number(cond[0]['index']) != 0): raise Exception("Leap only can apply for index = 0")
                if(type(cond[2]) is dict):
                    if(isset(cond[2], 'symbol')): raise Exception("Leap only works on itself")
                    if(isset(cond[2], 'type') and not cond[2]['type'] in ['frame', 'min', 'max']): raise Exception("Leap only works on type frame")
                    if(isset(cond[2], 'index') and Number(cond[2]['index']) >= 0): raise Exception("Leap only can compare with index < 0")
                    if(isset(cond[2], 'start_index') and Number(cond[2]['start_index']) >= 0): raise Exception("Leap only can compare with start_index < 0")
                    if(isset(cond[2], 'stop_index') and Number(cond[2]['stop_index']) >= 0): raise Exception("Leap only can compare with stop_index < 0")
                condition[key] = [1, '!=', 1]
            elif(isset(cond[2], 'leap')):
                if(isset(cond[2], 'symbol')): raise Exception("Leap only works on itself")
                if(isset(cond[2], 'type') and cond[2]['type'] != 'frame'): raise Exception("Leap only works on type frame")
                if(not isset(cond[2], 'column')): raise Exception("Not define colum in leap")
                if(cond[2]['column'] != 'low' and cond[2]['column'] != 'high'): raise Exception("Leap only works exactly on Low or High")
                if(cond[2]['column'] == 'low' and not cond[1] in ['>=', '>']): raise Exception("Leap only works exactly on > Low")
                if(cond[2]['column'] == 'high' and not cond[1] in ['<=', '<']): raise Exception("Leap only works exactly on < High")
                if(Number(cond[2]['index']) != 0): raise Exception("Leap only can apply for index = 0")
                if(type(cond[0]) is dict): 
                    if(isset(cond[0], 'symbol')): raise Exception("Leap only works on itself")
                    if(isset(cond[0], 'type') and not cond[0]['type'] in ['frame', 'min', 'max']): raise Exception("Leap only works on type frame")
                    if(isset(cond[0], 'index') and Number(cond[0]['index']) >= 0): raise Exception("Leap only can compare with index < 0")
                    if(isset(cond[0], 'start_index') and Number(cond[0]['start_index']) >= 0): raise Exception("Leap only can compare with start_index < 0")
                    if(isset(cond[0], 'stop_index') and Number(cond[0]['stop_index']) >= 0): raise Exception("Leap only can compare with stop_index < 0")
                condition[key] = [1, '!=', 1]
            else:
                condition[key] = [1, '=', 1]
        elif(type(cond) is list):
            simpleLeapCondition(cond)
        
def checkIsWorkingLeap(strategy, campaignImp):
    for flow in strategy:
        if(not isset(strategy[flow], 'type')): continue
        straType = strategy[flow]
        if (isset(straType, 'disable') and straType['disable']): continue
        if (not isset(straType, 'match')): continue
        if (not isset(straType['match'], 0)): continue
        condition = deepcopy(straType['match'][0]['condition'])
        simpleLeapCondition(condition)
        checkResult = campaignImp.compareOr(condition)
        if(not checkResult['result']): raise Exception(checkResult['message'])
        if(checkResult['data']):
            raise Exception("Leap can not overide condition. " + json.dumps(straType['match'][0]['condition']))


def replaceLeapCondition(condition, shortestLeap):
    for key, cond in enumerate(condition):
        if(type(cond) is list and len(cond) == 3 and cond[1] in ['=', '>=', '<=', '>', '<', '!=']):
            if(isset(cond[0], 'leap')):
                condition[key][0]['frame'] = shortestLeap
            elif(isset(cond[2], 'leap')):
                condition[key][2]['frame'] = shortestLeap
            else:
                condition[key] = [1, '=', 1]
        elif(type(cond) is list):
            replaceLeapCondition(cond, shortestLeap)
        

def genLeapCondition(strategy):
    leapCondition = []
    shortLeap = getShortestLeap(strategy)
    if(shortLeap is None): raise Exception("No Leap in the strategy")
    for flow in strategy:
        if(not isset(strategy[flow], 'type')): continue
        straType = strategy[flow]
        if (isset(straType, 'disable') and straType['disable']): continue
        if (not isset(straType, 'match')): continue
        if (not isset(straType['match'], 0)): continue
        condition = deepcopy(straType['match'][0]['condition'])
        replaceLeapCondition(condition, shortLeap)
        leapCondition.append([condition])
    return leapCondition


def checkMatchPrice(strategy):
    #Check match price setting is wrong or not
    print("Check match price")
    for flow in strategy:
        if(not isset(strategy[flow], 'type')): continue
        flowType = strategy[flow]['type']
        matches = strategy[flow]['match']
        phase = -1
        for match in matches:
            phase += 1    
            if(not isset(match, 'match_price')): continue
            matchPrice = match['match_price']

            #check if phase's match_price have problem
            if(isset(matchPrice, 'type') and matchPrice['type'] == 'event'):
                if(isset(matchPrice, 'column') and matchPrice['column'] == 'matched_price'):
                    if(isset(matchPrice, 'percent')):
                        percent = Number(matchPrice['percent'])
                        if(flowType == LabResultsWrapper.LAB_RESULT_TYPE_LONG and percent > 100):
                            return Reply.make(False, 'Match_price setting maybe wrong. In LONG match_price percent should be smaller than 100')
                        if(flowType == LabResultsWrapper.LAB_RESULT_TYPE_SHORT and percent < 100):
                            return Reply.make(False, 'Match_price setting maybe wrong. In SHORT match_price percent should be greater than 100')
            
            #check if phase 0 match_price have problem
            if(phase == 0):
                matchPriceConditions = []
                filterMatchPriceCodition(match['condition'], matchPriceConditions)
                print(matchPriceConditions)
                allowFrame = []
                allowColumn = []
                allowIndex = []
                allowStopIndex = []
                allowStartIndex = []
                for item in matchPriceConditions:
                    if(isset(item, 'frame')): allowFrame.append(item['frame'])
                    if(isset(item, 'column')): allowColumn.append(item['column'])
                    if(isset(item, 'index')): allowIndex.append(Number(item['index']))
                    if(isset(item, 'stop_index')): allowStopIndex.append(Number(item['stop_index']))
                    if(isset(item, 'start_index')): allowStartIndex.append(Number(item['start_index']))
                
                if(isset(matchPrice, 'frame')):
                    if(not matchPrice['frame'] in allowFrame):
                        return Reply.make(False, 'Match_price setting maybe wrong. frame should be in list: ' + json.dumps(allowFrame))
                if(isset(matchPrice, 'column')):
                    if(not matchPrice['column'] in allowColumn):
                        return Reply.make(False, 'Match_price setting maybe wrong. column should be in list: ' + json.dumps(allowColumn))
                if(isset(matchPrice, 'index')):
                    if(not Number(matchPrice['index']) in allowIndex):
                        return Reply.make(False, 'Match_price setting maybe wrong. index should be in list: ' + json.dumps(allowIndex))
                if(isset(matchPrice, 'stop_index')):
                    if(not Number(matchPrice['stop_index']) in allowStopIndex):
                        return Reply.make(False, 'Match_price setting maybe wrong. stop_index should be in list: ' + json.dumps(allowStopIndex))
                if(isset(matchPrice, 'start_index')):
                    if(not Number(matchPrice['start_index']) in allowStartIndex):
                        return Reply.make(False, 'Match_price setting maybe wrong. start_index should be in list: ' + json.dumps(allowStartIndex))
        
        

    return Reply.make(True, 'Maybe right')


def filterMatchPriceCodition(condition, result:list):
    if(type(condition) is list and len(condition) == 3 and condition[1] in ['=', '>=', '<=', '>', '<', '!=']):

        if(isset(condition[0], 'frame') 
        and isset(condition[0], 'column') 
        and condition[0]['column'] in ['low', 'high', 'close'] 
        and isset(condition[0], 'index') 
        and Number(condition[0]['index']) == 0
        and type(condition[2]) is dict
        ):
            result.append(condition[2])

        if(isset(condition[2], 'frame') 
        and isset(condition[2], 'column') 
        and condition[2]['column'] in ['low', 'high', 'close'] 
        and isset(condition[2], 'index')
        and Number(condition[2]['index']) == 0
        and type(condition[0]) is dict
        ):
            result.append(condition[0])
    elif(type(condition) is list):
        for con in condition:
            filterMatchPriceCodition(con, result)
        


            




    


    





    

    
    
