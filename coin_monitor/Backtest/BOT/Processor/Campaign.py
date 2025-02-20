from datetime import datetime
import json
from math import floor
from helper.Reply import Reply
from helper.Defaults import *
from Backtest.BOT.Processor.Action import Action
from Backtest.BOT.Processor.Order import Order
from helper.Timer import is_maturity_date, timeInDate, is_maturity_after
from models.Mongo.MongoModel import MongoModel
from Backtest.BOT.Processor.functions import fillStrategy
import pandas as pd
import math
from helper.Telegram import Telegram
from time import sleep

class Campaign():

    def __init__(self, campaign:dict, strategy:dict, params:dict={}, showLog=True):
        super().__init__()
        
        self.action:Action = None
        self.actions:dict(str,Action) = {}
        self.showLog = showLog

        self.database = MongoModel('backtest_data')
        self.params = params
        self.strategy = strategy

        self.checkData = {}
        self.priceData = {}
        self.runtime = None

        self.id = campaign.get('id', None)
        self.log(f"Campain UUID = {self.id}")

        self.startDay = campaign.get('start_date',"2022_01_01")
        self.stopDay = campaign.get('stop_date', "2022_10_01")
        
        self.symbol = None
        self.orderEditQueue = []
        #======================
        self.symbols = ['ETHUSDT', 'ETHUSDTQ1']
        self.pairDatabase = 'pair_indicator_eth'
        self.countEditOrder = 0

    def initial(self):
        fillStrategy(self.strategy, self.params)

    def run(self):
        
        startTime = datetime.strptime(self.startDay, '%Y_%m_%d').timestamp()
        stopTime = datetime.strptime(self.stopDay, '%Y_%m_%d').timestamp()

        currentTime = startTime
        blockTime = 86400 * 1
        self.log("===== Start running ====")
        while(currentTime < stopTime):
            subStartTime = currentTime
            subStopTime = currentTime + blockTime
            currentTime += blockTime

            data = self.getData(subStartTime, subStopTime)
            timestamps = data['timestamps']
            
            total = len(timestamps)
            self.log(f"Total data {total}")
            processed = 0
            # self.updateDayFee()
            for timestamp in timestamps:
                
                #load pair data to self check data
                if(timestamp in data['pair']):
                    self.checkData['pair']:dict = data['pair'][timestamp]
                    
                # #load pair band data to self.check data   
                # if(timestamp in data['pair_band']):
                #     pairBandData:dict = data['pair_band'][timestamp]
                #     self.checkData['pair_band'] = { pairBandData['symbol']: [pairBandData]}
                    
                self.getPriceData()
                
                self.runtime = float(timestamp)
                self.process()
                processed += 1
                if(processed % 1000 == 0):
                    self.log(f"Process {processed}/{total}", end='\r')

    def getData(self, startTime, stopTime):
        startTime = startTime * 1000
        stopTime = stopTime * 1000
        self.log(f"Get data from {datetime.fromtimestamp(startTime/1000)}({startTime}) to {datetime.fromtimestamp(stopTime/1000)}({stopTime})")
        timestamps = []
        pairBandDict = []
        
        pairBandData = list(self.database.setCollection(self.pairDatabase).collection.find({'symbol': 'USDTPERP', 'timestamp': {'$gte': startTime, '$lte': stopTime}}, {'_id':0}).sort('timestamp', 1))
       
        if(len(pairBandData) > 0):
            pairBandData = pd.DataFrame(pairBandData).drop_duplicates(subset='timestamp', keep="last")
            pairBandData = pairBandData.set_index('timestamp', drop=False)
            pairBandData = pairBandData.sort_index()
            pairBandDict = pairBandData.to_dict(orient='index')
            timestamps = pairBandData.index.to_list()
        
        return {
            'pair': pairBandDict,
            'timestamps': timestamps
        }
        
    
    def getPriceData(self):
        self.priceData = {}
        for symbol in self.symbols:
            self.priceData[symbol] = {
                'last': float(self.checkData['pair'].get(f'{symbol}_lastPrice', 0)),
                'volLast': float(self.checkData['pair'].get(f'{symbol}_matchedVol', 0)),
                'bestBid': float(self.checkData['pair'].get(f'{symbol}_best1Bid', 0)),
                'volBid': float(self.checkData['pair'].get(f'{symbol}_best1BidVol', 0)),
                'bestAsk': float(self.checkData['pair'].get(f'{symbol}_best1Offer', 0)),
                'volAsk': float(self.checkData['pair'].get(f'{symbol}_best1OfferVol', 0)),
            }
        
        
    def calCommit(self, qty, price, isTaker=True):
        if(isTaker):
            return 0.04 * qty * price /100
        return 0.02 * qty * price /100

    def process(self):
        '''
        is call in other thread when call
        '''
        self.processDefined()
        #Check Có lệnh hay chưa
        isPending = self.checkAction()
    
        if(isPending):
            checkResult = self.monitorPosition()
        elif(not isPending):
            #Check ĐK đợi lệnh
            checkResult = self.checkNewAction()
            
            if(not checkResult['result']):
                self.checkResult = checkResult
            else:
                # print("Check Order")
                self.checkResult = Reply.make(True, 'Check Order', False)
    
    def checkAction(self):
        if(self.action is None): return False
        if(self.action.bot_act_pending == 0): return False
        self.defineSymbol(self.action.bot_act_flow)
        return True

    # == Block get and calculate data ==
    
    def compare(self, element):
        # make comparision with struct: OR(AND(FORMULAR, OR...), AND, ....)
        firstNumber = self.calculateElement(element[0])
        formula = element[1]
        secondsNumber = self.calculateElement(element[2])

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

    def compareAnd(self, conditions):
        logs = []
        for condition in conditions:
            if(type(condition) is list):
                if(len(condition) == 3 and condition[1] in ['<', '>', '=', '>=', '<=', '!=']):
                    result = self.compare(condition)
                    if(not result['result']):
                        return result
                else:
                    result = self.compareOr(condition)
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

    def compareOr(self, conditions):
        logs = []
        for condition in conditions:
            result = self.compareAnd(condition)
            if(not result['result']):
                return result
            logs.append(result['message'])
            if(result['data'] is None):
                return Reply.make(True, ' OR '.join(logs), None)
            if(result['data'] is True):
                return Reply.make(True, ' OR '.join(logs), True)
        return Reply.make(True, ' OR '.join(logs), False)

    def getPairData(self, struct:dict):
        
        symbol = struct.get('symbol', None)
        if(symbol is None): return Reply.make(False, 'Symbol not defined')
        symbol = self.calculateElement(symbol)['data']

        field = struct.get('field', None)
        if(field is None): return Reply.make(False, 'Field not defined')

        symbolField = field
        if(symbol != ""): symbolField = f"{symbol}_{field}"
        pairData = self.checkData.get('pair', {})

        if(symbolField not in pairData):
            return Reply.make(True, f'{field} not exist', None)
        
        value = pairData[symbolField]
        des = f"Pair {symbolField}"
        return self.calculateValue(struct, value, des)
        
        
        

    def updateAvgEnterGap(self):
        pairSymbol = self.action.bot_act_symbol_pair
        if(pairSymbol is None): return
        symbol = self.action.bot_act_symbol
        orderIds = list(self.action.orders.keys())
        
        side = None
        symbolQty = 0
        symbolMoney = 0
        pairSymbolQty = 0
        pairSymbolMoney = 0
        for orderId in orderIds:
            order:Order = self.action.orders[orderId]
            if(order.bot_order_status == Order.STATUS_ERROR): continue
            if(order.bot_order_matched_qty == 0): continue
            if(order.bot_order_act_type in [Order.ACT_TYPE_MAKE_ORDER]):
                if(order.bot_order_symbol == symbol):
                    side = order.bot_order_side
                    if(order.bot_order_side == Order.SIDE_BUY):
                        symbolQty += order.bot_order_matched_qty
                        symbolMoney += order.bot_order_matched_qty * order.bot_order_matched_price
                    else:
                        symbolQty -= order.bot_order_matched_qty
                        symbolMoney -= order.bot_order_matched_qty * order.bot_order_matched_price
            if(order.bot_order_act_type in [Order.ACT_TYPE_PAIR_ORDER]):
                if(order.bot_order_symbol == pairSymbol):
                    if(side is not None and order.bot_order_side != side):
                        if(order.bot_order_side == Order.SIDE_BUY):
                            pairSymbolQty += order.bot_order_matched_qty
                            pairSymbolMoney += order.bot_order_matched_qty * order.bot_order_matched_price
                        else:
                            pairSymbolQty -= order.bot_order_matched_qty
                            pairSymbolMoney -= order.bot_order_matched_qty * order.bot_order_matched_price
        
        pairSymbolAvg = None
        symbolAvg = None
        if(symbolQty + pairSymbolQty == 0):
            if(symbolQty != 0): symbolAvg = symbolMoney/symbolQty
            if(pairSymbolQty !=0): pairSymbolAvg = pairSymbolMoney/pairSymbolQty
        
        if(pairSymbolAvg is not None and symbolAvg is not None):
            self.action.bot_act_enter_gap = pairSymbolAvg - symbolAvg
            self.log(f"Avg Gap {self.action.bot_act_enter_gap}")
                    
                        
        
    #===============================================

    def calculateValue(self, struct:dict, value, des):
        try:
            if(isNumeric(value)): 
                percent = struct.get('percent', None)
                if(percent is not None):
                    percent = float(percent)
                    value = value * percent/100
                    des = f"{des}({percent}%)"
                    
                add = struct.get('add', None)
                if(add is not None):
                    addNumber = self.calculateElement(add)
                    if(not addNumber['result'] or addNumber['data'] is None): return addNumber
                    value = value + Number(addNumber['data'])
                    des = des + f" + {addNumber['message']}"
                    
                subtract = struct.get('subtract', None)
                if(subtract is not None):
                    subtractNumber = self.calculateElement(subtract)
                    if(not subtractNumber['result'] or subtractNumber['data'] is None): return subtractNumber
                    value = value - Number(subtractNumber['data'])
                    des = des + f" - {subtractNumber['message']}"
                    
                multiply = struct.get('multiply', None)
                if(multiply is not None):
                    multiplyNumber = self.calculateElement(multiply)
                    if(not multiplyNumber['result'] or multiplyNumber['data'] is None): return multiplyNumber
                    value = value * Number(multiplyNumber['data'])
                    des = des + f" * {multiplyNumber['message']}"
                    
                divide = struct.get('divide', None)
                if(divide is not None):
                    divideNumber = self.calculateElement(divide)
                    if(not divideNumber['result'] or divideNumber['data'] is None): return divideNumber
                    divideNum = Number(divideNumber['data'])
                    if(divideNum == 0): return Reply.make(False, f"Can not divide zero: {divideNumber['message']}")
                    value = value / divideNum
                    des = des + f" / {divideNumber['message']}"
        except Exception as e:
            return Reply.make(False, f"{des}. {e}")

        return Reply.make(True, f"{des}[{value}]", value)
        
    def calculateElement(self, struct, dynamicIndex = None) -> dict:
        if(type(struct) in [int, float, bool]): return Reply.make(True, str(struct), struct)
        if(struct is None): return Reply.make(True, str(struct), struct)
        if(type(struct) is str):

            if(struct == 'timestamp'):
                value = int(self.runtime)
                return Reply.make(True, f"{struct}[{value}]", value)

            if(struct == 'time_in_date'):
                value = timeInDate()
                return Reply.make(True, f"{struct}[{value}]", value)
            
            if(struct == 'is_maturity_date'):
                self.isMaturity = is_maturity_date(self.runtime/1000)
                return Reply.make(True, f"{struct}[{self.isMaturity}]", self.isMaturity)
            
            if(struct == 'is_maturity_after'):
                self.isAfterMaturity = is_maturity_after(self.runtime/1000)
                return Reply.make(True, f"{struct}[{self.isAfterMaturity}]", self.isAfterMaturity)
            
            
            #===========Fishing=============
            if(struct == 'enter_fishing_cancel'): 
                value = self.enterFishingCancel
                return Reply.make(True, f"{struct}({value})", value)
            if(struct == 'exit_fishing_cancel'): 
                value = self.exitFishingCancel
                return Reply.make(True, f"{struct}({value})", value)
            #===============================  
            
            if(struct in self.defined):
                return self.defined[struct]
            else:
                return Reply.make(True, struct, struct)
            
        if(type(struct) is dict):
            structType = struct.get('type', 'kline')
            if(structType is None): return Reply.make(False, 'No type Defined')

            if(structType == 'pair'):
                pairData = self.getPairData(struct)
                return pairData  
            
            elif(structType == 'event'):
                if(self.action is None): return Reply.make(False, 'No Event')
                column = struct.get('column', None)
                column = 'bot_act_' + str(column)
                if(column == 'bot_act_interval'):
                    value = (int(self.runtime) - int(self.action.bot_act_enter_time))
                else:
                    if(not hasattr(self.action, column)): return Reply.make(False, 'Can not find column ' + column)
                    value = getattr(self.action, column)
                des = f"Action {column}"
                
                return self.calculateValue(struct, value, des)
            
            elif(structType == 'campaign'):
                if(self.action is None): return Reply.make(False, 'No Event')
                column = struct.get('column', None)
                column = 'bot_camp_' + str(column)
                if(not hasattr(self.campaign, column)): return Reply.make(False, 'Can not find column ' + column)
                value = getattr(self.campaign, column)
                des = f"Campaign {column}"
                return self.calculateValue(struct, value, des)
            
            elif(structType == 'account'):
                if(self.account is None): return Reply.make(False, 'No account')
                column = struct.get('column', None)
                column = 'account_' + str(column)
                if(not hasattr(self.account, column)): return Reply.make(False, 'Can not find column ' + column)
                value = getattr(self.account, column)
                des = f"Account {column}"
                return self.calculateValue(struct, value, des)
            
            elif(structType == 'kline'):
                result = self.getData(struct)
                if(not result['result']): return result
                
                frame = get(struct, 'frame', None)
                indexCfg = get(struct, 'index', 0)
                
                column = struct.get('column', None)
                field = struct.get('field', column)
                if(field is None): return Reply.make(False, f'Field not defined : {struct}')
                
                symbol = struct.get('symbol', None)
                if(symbol is None): return Reply.make(False, f'Symbol not defined: {struct}')
                symbol = self.calculateElement(symbol)['data']
                
                if(indexCfg == 'dynamic'):
                    index = dynamicIndex
                else:
                    index = Number(indexCfg) - 1

                des = f"{symbol} Frame {frame} {field}({indexCfg})"
                
                if(frame is None or index is None or field is None):
                    return Reply.make(False, 'Please define symbol, frame, field and index ' + des + json.dumps(struct))
                
                try:
                    if('timestamp' in self.checkData['kline'][symbol][frame][-1]):
                        if(self.runtime - float(self.checkData['kline'][symbol][frame][-1]['timestamp']) > 60000): return Reply.make(True, f"Data {structType} too old", None)
                    value = self.checkData['kline'][symbol][frame][index][field]
                    return self.calculateValue(struct, value, des)                

                            
                except Exception:
                    return Reply.make(True, 'Can not get Kline ' + symbol + " " + frame + " " + str(indexCfg) + " " + str(field), None)
            
            elif(structType == 'calculate'):
                number1 = get(struct, 'number_1', None)
                number2 = get(struct, 'number_2', None)
                logic = get(struct, 'logic', None)
                if(number1 is None or number2 is None or logic is None):
                    return Reply.make(False, "Please define number_1, number_2 and logic " + json.dumps(struct))
                num1 = self.calculateElement(number1)
                if(not num1['result'] or num1['data'] is None): return num1
                num2 = self.calculateElement(number2)
                if(not num2['result'] or num2['data'] is None): return num2

                des1 = num1['message']
                des2 = num2['message']
                des = des1 + " " + str(logic) + " " + des2

                value = None
                num1 = Number(num1['data'])
                num2 = Number(num2['data'])
                if(logic == '+'): value = num1 + num2
                elif (logic == '-'): value = num1 - num2
                elif (logic == '*'): value = num1 * num2
                elif (logic == '/'): value = num1 / num2
                else: return Reply.make(False, 'Does not support logic ' + logic)
                return self.calculateValue(struct, value, des)
            
            elif(structType == 'if'):
                condition = get(struct, 'condition', None)
                trueValueCfg = get(struct, 'true', None)
                falseValueCfg = get(struct, 'false', None)
                if(condition is None or trueValueCfg is None or falseValueCfg is None):
                    return Reply.make(False, "Please define condition, true value and false value " + json.dumps(struct))
                condition = self.compareOr(condition)
                if(not condition['result'] or condition['data'] is None): return condition
                des = f"if({condition['message']})[{condition['data']}]"
                if(condition['data']):
                    trueValue = self.calculateElement(trueValueCfg)
                    if(not trueValue['result'] or trueValue['data'] is None): return trueValue
                    value = trueValue['data']
                else:
                    falseValue = self.calculateElement(falseValueCfg)
                    if(not falseValue['result'] or falseValue['data'] is None): return falseValue
                    value = falseValue['data']
                return Reply.make(True, f"{des}({value})", value)
            
            elif(structType == 'min'):
                numbers = struct.get('numbers', None)
                if(numbers is None): return Reply.make(False, 'Please define numbers in min')
                if(type(numbers) is not list): return Reply.make(False, "Numbers in min must be a list")
                if(len(numbers) == 0): return Reply.make(False, 'Numbers in min is empty')
                values = []
                dess = []
                for number in numbers:
                    value = self.calculateElement(number)
                    if(not value['result'] or value['data'] is None): return value
                    values.append(value['data'])
                    dess.append(value['message'])
                value = min(values)
                des = f"min({','.join(dess)})"
                return Reply.make(True, f"{des}[{value}]", value)
        
            elif(structType == 'max'):
                numbers = struct.get('numbers', None)
                if(numbers is None): return Reply.make(False, 'Please define numbers in max')
                if(type(numbers) is not list): return Reply.make(False, "Numbers in max must be a list")
                if(len(numbers) == 0): return Reply.make(False, 'Numbers in max is empty')
                values = []
                dess = []
                for number in numbers:
                    value = self.calculateElement(number)
                    if(not value['result'] or value['data'] is None): return value
                    values.append(value['data'])
                    dess.append(value['message'])
                value = max(values)
                des = f"max({','.join(dess)})"
                return Reply.make(True, f"{des}[{value}]", value)
            
            elif(structType == 'is_null'):
                value = struct.get('value', None)
                value = self.calculateElement(value)
                if(not value['result']): return value
                des = f"{value['message']} is Null"
                if(value['data'] is None or math.isnan(value['data'])):
                    vl = True
                else:
                    vl = False
                return Reply.make(True, f"{des}[{vl}]", vl)
            
            else:
                print(struct)
                result = self.getData(struct)
                
                if(not result['result']): return result
                
                indexCfg = get(struct, 'index', 0)
                source = struct.get('source', structType)
                field = struct.get('field', None)
                column = get(struct, 'column', field)
                
                symbol = struct.get('symbol', None)
                if(symbol is None): return Reply.make(False, 'Symbol not defined')
                symbol = self.calculateElement(symbol)['data']
                index = Number(indexCfg) - 1
                des = f"{symbol} {source} {column}({indexCfg})"
                
                if(index is None or column is None):
                    return Reply.make(False, 'Please define symbol, column and index ' + des + json.dumps(struct))
                try:
                    checkData = self.checkData[source][symbol]
                    if(not isset(checkData, index) or not isset(checkData[index], column)): return Reply.make(True, des, None)
                    if('timestamp' in checkData[-1]):
                        if(self.runtime - float(checkData[-1]['timestamp']) > 60000): return Reply.make(True, f"Data {structType} too old", None)
                    value = checkData[index][column]
                    return self.calculateValue(struct, value, des)
                    
                except Exception as e:
                    return Reply.make(True, f'Can not get Data {symbol} {indexCfg} {column}', None)
        return Reply.make(False, 'Can not calculate', struct)
    
    
    
    
    def processDefined(self):
        self.defined = {}
        if('defined' in self.strategy):
            for key in self.strategy['defined']:
                self.defined[key] = self.calculateElement(self.strategy['defined'][key])    
    
    def getFlowData(self, flowN, key):
        flowData:dict = self.strategy.get(flowN, None)
        if(flowData is None): return None
        return flowData.get(key, None)

    def defineSymbol(self, flowName):
        #calculate self symbol
        symbol = self.calculateElement(self.getFlowData(flowName, 'symbol'))
        if(not symbol['result']): raise Exception(symbol['message'])
        symbol = symbol['data']
        if(symbol is None): raise Exception('No Symbol')
        
        self.symbol = symbol
        pairSymbol = None
        pairConfig:dict = self.getFlowData(flowName, 'pair_trading')
        if(pairConfig is not None):
            pairSymbol = self.calculateElement(pairConfig.get('symbol', None))['data']

        return {
            "symbol": symbol,
            "symbol_pair": pairSymbol
        }

    # =====================================
    
    # == Block create position =============     
    def checkNewAction(self):
        '''
        - Lấy các flow của strategy
        - Lần lượt kiểm tra điều kiện vào lệnh
        '''
        logResults = {}
        for flowN in self.strategy:
            if(flowN == 'defined'): continue
            enterCondition = self.getFlowData(flowN, 'enter_condition')
            if(enterCondition is None): continue
            logResult = self.compareOr(enterCondition)
           
            # print(logResult)
            logResults[flowN] = logResult
            if(not logResult['result']): return logResult

            if(logResult['data'] is not None and logResult['data']):
                self.makeAction(flowN, logResult['message'])
                return Reply.make(True, 'Matched', logResults)

        return Reply.make(True, 'Unmatched', logResults)

    def makeAction(self, flowName, reason=''):

        symbols = self.defineSymbol(flowName)
        
        newAction = Action()
        newAction.bot_act_campaign = self.id
        newAction.bot_act_enter_time = int(self.runtime)
        newAction.bot_act_enter_data = json.dumps(self.checkData, default=str)
        newAction.bot_act_enter_reason = reason
        newAction.bot_act_status_enter = Action.STATUS_ENTER_PENDING
        newAction.bot_act_status_exit = None
        newAction.bot_act_flow = flowName
        newAction.bot_act_pending = 1
        newAction.bot_act_symbol = symbols['symbol']
        newAction.bot_act_symbol_pair = symbols['symbol_pair']

        self.action = newAction
        self.actions[newAction.bot_act_id] = newAction        

        self.sendTele('notice', '==== START ACTION ====', Telegram.TELE_ICON_TAKEPROFIT, {
            "Campaign": self.id,
            "Flow": flowName,
            "Reason": reason
        })

        action = self.getFlowData(flowName, 'enter_action')
        if(action is None ): raise Exception(f'Please define action for flow {flowName}')
        self.processMakeOrderAction(action, Order.ACT_TYPE_MAKE_ORDER, reason)

    def processMakeOrderAction(self, action:dict, orderType, reason=''):
        
        
        # Check order change for fishing strategy
        self.enterFishingCancel = False
        
        actionType = orderType
        symbol = self.action.bot_act_symbol

        orderType = self.calculateElement(action.get('order_type', None))['data']
        if(orderType is None): raise Exception('No Order Type')

        price = self.calculateElement(action.get('price', 0))['data']
        if(price is None):
            self.sendTele('warning','Can not make L0 order because Price=None')
            return Reply.make(False, 'Can not make order')

        if(price == 0 and orderType == Order.TYPE_LO): 
            self.sendTele('warning','Can not make L0 order because Price=0')
            return Reply.make(False, 'Can not make order')
        
        if(type(price) is float and price > 0): price = round(price, 9)

        #calculate number and side 
        
        orderMatched = 0
        orderSide = None

        symbolData = self.getEnterStatus()
        symbolData = symbolData.get(symbol, {})

        orderMatched = symbolData.get('matched', 0)
        enterWaiting = symbolData.get('enter_waiting', 0)

        cfgQty = self.calculateElement(action.get('quantity', None))
        if(not cfgQty['result']): raise Exception(cfgQty['message'])
        cfgQty = cfgQty['data']
        if(cfgQty is None or cfgQty == 0): 
            self.sendTele('warning','Can not make order because quantity = 0')
            return
        cfgQty = float(cfgQty)

        total = self.calculateElement(action.get('total', None))['data']
        if(total is None): total = cfgQty

        orderSide = self.calculateElement(action.get('order_side', None))['data']
        if(orderSide is None): return
        if(orderSide == Order.SIDE_BUY):
            orderQty = total - (orderMatched + enterWaiting)
        if(orderSide == Order.SIDE_SELL):
            orderQty = -total - (orderMatched + enterWaiting)
        
        if(orderQty > 0):
            orderSide = Order.SIDE_BUY
        if(orderQty < 0):
            orderQty = -orderQty
            orderSide = Order.SIDE_SELL

        orderQty = min(cfgQty, orderQty)

        if(orderSide is None): 
            return
        
        block = action.get('block', orderQty)
        if(type(block) is not list): block = [block]
        interval = action.get('interval', 0)
        delay = action.get('delay', 0)
        if(delay > 0): sleep(delay)
        
        icon = Telegram.TELE_ICON_LONG if orderSide == Order.SIDE_BUY else Telegram.TELE_ICON_SHORT
        self.sendTele('notice', f'Make ORDER', icon, {
            "Flow": self.action.bot_act_flow,
            "Symbol": symbol,
            "Side": orderSide,
            "Type": orderType,
            "Price": price,
            "Qty": orderQty,
            "Reason": reason
        })
        
        
        
        sent = 0
        orderIndex = 0
        blockLen = len(block)
        while sent < orderQty:
            blockIndex = orderIndex % blockLen
            orderIndex += 1
            blockQty = float(block[blockIndex])
            currentOrderQty = round(min(blockQty, orderQty-sent), 9)
            if(currentOrderQty == 0): break
            try:

                orderObj = Order()
                orderObj.bot_order_commission = 0
                orderObj.bot_order_task = None
                orderObj.bot_order_action = self.action.bot_act_id
                orderObj.bot_order_camp = self.id
                orderObj.bot_order_qty = currentOrderQty
                orderObj.bot_order_act_type = actionType
                orderObj.bot_order_symbol = symbol
                orderObj.bot_order_type = orderType
                orderObj.bot_order_price = price
                orderObj.bot_order_matched_qty = 0
                orderObj.bot_order_unmatched_qty = currentOrderQty
                orderObj.bot_order_side = orderSide
                orderObj.bot_order_status = Order.STATUS_SENT
                orderObj.bot_order_time = int(self.runtime)
                orderObj.bot_order_log = reason
                self.action.addOrder(orderObj)
                
            finally:
                sent += currentOrderQty
                if(interval > 0):
                    sleep(interval)
                
        
        return Reply.make(True, "Success")

    def processCloseOrderAction(self, action:dict, orderType, reason=''):
        
        # Check order change for fishing strategy
        self.exitFishingCancel = False
        
        actionType = orderType
        symbol = self.symbol
        orderType = action.get('order_type', None)
        if(orderType is None): raise Exception('No Order Type')

        price = self.calculateElement(action.get('price', 0))
        if(not price['result']): return price
        price = price['data']
        if(price == 0 and orderType == Order.TYPE_LO): 
            self.updateActionStatus()
            self.sendTele('warning','Can not make L0 order because Price=0')
            return Reply.make(False, 'Can not make order')
        

        #calculate number and side 

        order: Order
        orderMatched = 0
        orderwaiting = 0
        orderSide = None

        symbolData = self.getEnterStatus()
        symbol = self.symbol
        symbolData = symbolData.get(symbol, {})

        orderMatched = symbolData.get('matched', 0)
        closeWaiting = symbolData.get('close_waiting', 0)
                
        orderQty = orderMatched + closeWaiting
        
        if(orderQty > 0):
            orderSide = Order.SIDE_SELL
        if(orderQty < 0):
            orderQty = -orderQty
            orderSide = Order.SIDE_BUY

        if(orderSide is None): 
            return
        
        cfgQty = self.calculateElement(action.get('quantity', None))['data']
        if(cfgQty is None): cfgQty = orderQty
        
        orderQty = round(min(orderQty, cfgQty), 9)
        
        block = action.get('block', orderQty)
        if(type(block) is not list): block = [block]
        interval = action.get('interval', 0)
        delay = action.get('delay', 0)
        if(delay > 0): sleep(delay)
        
        icon = Telegram.TELE_ICON_LONG if orderSide == Order.SIDE_BUY else Telegram.TELE_ICON_SHORT
        self.sendTele('notice', f'Close order', icon, {
            "Flow": self.action.bot_act_flow,
            "Symbol": symbol,
            "Side": orderSide,
            "Type": orderType,
            "Price": price,
            "Qty": orderQty,
            "Reason": reason
        })
        
        sent = 0
        orderIndex = 0
        blockLen = len(block)
        while sent < orderQty:
            blockIndex = orderIndex % blockLen
            orderIndex += 1
            blockQty = float(block[blockIndex])
            currentOrderQty = round(min(blockQty, orderQty-sent), 9)
            if(currentOrderQty == 0): break
            try:
                print(f"Add close order {orderSide} {symbol} {currentOrderQty}")
                closeOrder = Order()
                closeOrder.bot_order_commission = 0
                closeOrder.bot_order_task = None
                closeOrder.bot_order_action = self.action.bot_act_id
                closeOrder.bot_order_camp = self.id
                closeOrder.bot_order_qty = currentOrderQty
                closeOrder.bot_order_act_type = actionType
                closeOrder.bot_order_symbol = symbol
                closeOrder.bot_order_type = orderType
                closeOrder.bot_order_price = price
                closeOrder.bot_order_matched_qty = 0
                closeOrder.bot_order_unmatched_qty = currentOrderQty
                closeOrder.bot_order_side = orderSide
                closeOrder.bot_order_status = Order.STATUS_SENT
                closeOrder.bot_order_time = int(self.runtime)
                closeOrder.bot_order_log = reason
                self.action.addOrder(closeOrder)
                
            finally:
                sent += currentOrderQty
                if(interval > 0):
                    sleep(interval)
        
        
        return Reply.make(True, "Success")

    def monitorOrder(self):
        '''
        Monitor opening order.
        '''
        pendingOrder = self.action.getPendingOrder()
        if(len(pendingOrder) <= 0):
            return
        
        orderIds = list(pendingOrder.keys())
        isChange = False


        for orderId in orderIds:
            order:Order = pendingOrder[orderId]
            
            symbol = order.bot_order_symbol
            
            currentPrice = self.priceData[symbol]['last']
            matchedVol = self.priceData[symbol]['volLast']
            bestBid = self.priceData[symbol]['bestBid']
            volBid = self.priceData[symbol]['volBid']

            bestAsk = self.priceData[symbol]['bestAsk']
            volAsk = self.priceData[symbol]['volAsk']

            matchQty = None
            isTaker = False
            isOrderChange = False
           
            if(order.bot_order_type == Order.TYPE_LO):
                # print(order.toDict())
                # print(f"{order.bot_order_id} {order.bot_order_matched_time} {self.runtime}")
                # delay 10second after matched
                if(order.bot_order_matched_time is not None and self.runtime - order.bot_order_matched_time < 1000):
                    continue
                orderPrice = float(order.bot_order_price)
                orderUnmatch = float(order.bot_order_unmatched_qty)
                
                # print(f"CurrentPrice: {currentPrice}, orderPrice {orderPrice}")
                
                if(order.bot_order_side == Order.SIDE_BUY):
                    if(self.runtime - order.bot_order_time <= 250):
                        if(bestAsk > 0 and bestAsk <= orderPrice):
                            matchPrice = bestAsk
                            matchQty = min(orderUnmatch, volAsk)
                            isTaker = True
                    else:
                        if(currentPrice <= orderPrice and matchedVol > 0):
                            matchPrice = orderPrice
                            matchQty = min(orderUnmatch, matchedVol)
                        if(bestAsk > 0 and bestAsk <= orderPrice):
                            matchPrice = bestAsk
                            matchQty = min(orderUnmatch, volAsk)

                elif(order.bot_order_side == Order.SIDE_SELL):
                    if(self.runtime - order.bot_order_time <= 250):
                        
                        if(bestBid > 0 and bestBid >= orderPrice):
                            matchPrice = bestBid
                            matchQty = min(orderUnmatch, volBid)
                            isTaker = True
                    else:
                        if(currentPrice >= orderPrice and matchedVol > 0):
                            matchPrice = orderPrice
                            matchQty = min(orderUnmatch, matchedVol)
                            
                        if(bestBid > 0 and bestBid >= orderPrice):
                            matchPrice = bestBid
                            matchQty = min(orderUnmatch, volBid)

                if(matchQty is not None):
                    self.action.bot_act_matched_time = int(self.runtime)
                    newUnmatch = orderUnmatch - matchQty
                    if(order.bot_order_matched_qty > 0):
                        newMatch = order.bot_order_matched_qty + matchQty
                        newPrice = (matchQty * matchPrice + order.bot_order_matched_qty * order.bot_order_matched_price)/newMatch
                    else:
                        newMatch = matchQty
                        newPrice = matchPrice
                

                    newCommission = self.calCommit(newMatch, newPrice, isTaker)
                    newStatus = Order.STATUS_MATCHED_PART if newUnmatch > 0 else Order.STATUS_MATCHED_FULL
                    
                    newPrice = round(newPrice, 9)
                    newMatch = round(newMatch, 9)
                    
                    self.action.updateOrder(order, {
                        'bot_order_matched_price': newPrice,
                        'bot_order_matched_qty': newMatch,
                        'bot_order_unmatched_qty': newUnmatch,
                        'bot_order_status': newStatus,
                        'bot_order_matched_time': int(self.runtime),
                        'bot_order_commission': newCommission
                    })
                    # print(order.toDict())
                    self.sendTele('notice', 'Matched', Telegram.TELE_ICON_MATCHED, {
                        "Flow": self.action.bot_act_flow,
                        "Symbol": order.bot_order_symbol,
                        "Side": order.bot_order_side,
                        "Price": order.bot_order_matched_price,
                        "Qty": order.bot_order_matched_qty,
                        "Commission": newCommission,
                        "log": order.bot_order_log
                    })
                    isChange = True
                    isOrderChange = True

            if(order.bot_order_type == Order.TYPE_MP):
                if(self.runtime - order.bot_order_time <= 250): continue
                if(order.bot_order_side == Order.SIDE_BUY):
                    matchPrice = bestAsk
                else:
                    matchPrice = bestBid
                if(matchPrice > 0):
                    commission = self.calCommit(order.bot_order_qty, matchPrice, True)
                    self.action.updateOrder(order, {
                        'bot_order_matched_price': matchPrice,
                        'bot_order_matched_qty': order.bot_order_qty,
                        'bot_order_unmatched_qty': 0,
                        'bot_order_status': Order.STATUS_MATCHED_FULL,
                        'bot_order_matched_time': int(self.runtime),
                        'bot_order_commission': commission
                    })
                    self.sendTele('notice', 'Matched', Telegram.TELE_ICON_MATCHED, {
                        "Flow": self.action.bot_act_flow,
                        "Symbol": order.bot_order_symbol,
                        "Side": order.bot_order_side,
                        "Price": order.bot_order_matched_price,
                        "Qty": order.bot_order_matched_qty,
                        "Commission": commission,
                        "log": order.bot_order_log
                    })
                    isChange = True
                    isOrderChange = True

            if(isOrderChange):
                # Check order change for fishing strategy
                if(order.bot_order_matched_qty > 0):
                    if(order.bot_order_act_type == Order.ACT_TYPE_MAKE_ORDER):
                        self.exitFishingCancel = True
                    elif(order.bot_order_act_type == Order.ACT_TYPE_CLOSE_ORDER):
                        self.enterFishingCancel = True       
        
        if(isChange):
            self.checkPairingTarget()
            self.updateActionStatus()
            self.updateAvgEnterGap()

    def cancelOrder(self, order:Order, reason=''):
        self.sendTele('notice', 'Cancel', Telegram.TELE_ICON_CANCEL, {
            "Flow": self.action.bot_act_flow,
            "Symbol": order.bot_order_symbol,
            "Side": order.bot_order_side,
            "Price": order.bot_order_matched_price,
            "Qty": order.bot_order_qty,
            "Reason": reason
        })
        self.action.updateOrder(order, {
            'bot_order_status' : Order.STATUS_CANCELED,
            'bot_order_log' : f"{self.runtime} {reason}"
        })
        self.checkPairingTarget()
        self.updateActionStatus()
        return Reply.make(True, 'success')
    
    def editOrder(self, order:Order, newQty, newPrice, reason = ''):
        # self.sendTele('notice', 'Edit order', Telegram.TELE_ICON_CANCEL, {
        #     "Flow": self.action.bot_act_flow,
        #     "Symbol": order.bot_order_symbol,
        #     "Old Price": order.bot_order_price,
        #     "New Price": newPrice,
        #     "Reason": reason
        # })
        self.countEditOrder += 1
        self.orderEditQueue.append({
            'order': order,
            'update': {
                'bot_order_price' : newPrice,
                'bot_order_qty': newQty,
                'bot_order_log' : f"{self.runtime} {reason}"
            },
            'time': self.runtime
        })
        return Reply.make(True, 'success')
    
    def monitorEditOrder(self):
        pendingOrder = []
        for dt in self.orderEditQueue:
            if(self.runtime - dt['time'] > 250):
                self.action.updateOrder(dt['order'], dt['update'])
            else:
                pendingOrder.append(dt)
        self.orderEditQueue = pendingOrder

    def getPositionSymbol(self):
        '''
        Return position of action by symbol
            {
                VN30F2210: {matched: 5, waiting: 5}
                VN30F2211: {matched: 5, waiting: 5}
            }
        '''
        returnData = {}
        order:Order
        orderIds = list(self.action.orders.keys())
        for orderId in orderIds:
            order:Order = self.action.orders[orderId]
            if(order.bot_order_status in [Order.STATUS_ERROR]): continue

            symbol = order.bot_order_symbol
            if(symbol not in returnData):
                returnData[symbol] = {
                    'matched': 0,
                    'waiting': 0,
                }

            if(order.bot_order_side == Order.SIDE_BUY):
                returnData[symbol]['matched'] += order.bot_order_matched_qty
            else:
                returnData[symbol]['matched'] -= order.bot_order_matched_qty

            if(order.bot_order_status not in [Order.STATUS_CANCELED, Order.STATUS_MATCHED_FULL]):
                if(order.bot_order_side == Order.SIDE_BUY):
                    returnData[symbol]['waiting'] += order.bot_order_unmatched_qty
                else:
                    returnData[symbol]['waiting'] -= order.bot_order_unmatched_qty
        return returnData

    def getEnterStatus(self):
        '''
         Return position of action by symbol without Pair
            {
                VN30F2210: {matched: 5, enter_waiting: 5, close_waiting:5}
            }
        '''
        returnData = {}
        order:Order
        orderIds = list(self.action.orders.keys())
        for orderId in orderIds:
            order:Order = self.action.orders[orderId]

            if(order.bot_order_act_type in [Order.ACT_TYPE_PAIR_ORDER]): continue
            if(order.bot_order_status in [Order.STATUS_ERROR]): continue
            
            symbol = order.bot_order_symbol
            if(symbol not in returnData):
                returnData[symbol] = {
                    'matched': 0,
                    'enter_waiting': 0,
                    'close_waiting': 0,
                }

            if(order.bot_order_side == Order.SIDE_BUY):
                returnData[symbol]['matched'] += order.bot_order_matched_qty
            else:
                returnData[symbol]['matched'] -= order.bot_order_matched_qty

            if(order.bot_order_status not in [Order.STATUS_CANCELED, Order.STATUS_MATCHED_FULL]):
                if(order.bot_order_act_type == Order.ACT_TYPE_MAKE_ORDER):
                    if(order.bot_order_side == Order.SIDE_BUY):
                        returnData[symbol]['enter_waiting'] += order.bot_order_unmatched_qty
                    else:
                        returnData[symbol]['enter_waiting'] -= order.bot_order_unmatched_qty
                elif(order.bot_order_act_type == Order.ACT_TYPE_CLOSE_ORDER):

                    if(order.bot_order_side == Order.SIDE_BUY):
                        returnData[symbol]['close_waiting'] += order.bot_order_unmatched_qty
                    else:
                        returnData[symbol]['close_waiting'] -= order.bot_order_unmatched_qty
                
                # if(order.bot_order_side == Order.SIDE_BUY):
                #     returnData[symbol]['waiting'] += order.bot_order_unmatched_qty
                # else:
                #     returnData[symbol]['waiting'] -= order.bot_order_unmatched_qty
        return returnData
        
    def summaryAction(self):
        if(self.action.bot_act_pending == 0): return
        self.log('Summary Action')
        pnl = 0
        matchedQty = 0
        totalBuyVol = 0
        totalSellVol = 0
        commission = 0
        order:Order
        orderIds = list(self.action.orders.keys())
        for orderId in orderIds:
            order:Order = self.action.orders[orderId]
            if(order.bot_order_status in [Order.STATUS_ERROR]): continue
            
            if order.bot_order_matched_qty > 0:
                commission += order.bot_order_commission
                if order.bot_order_side == Order.SIDE_BUY:    
                    totalBuyVol += order.bot_order_matched_qty * order.bot_order_matched_price
                    matchedQty += order.bot_order_matched_qty
                else:
                    totalSellVol += order.bot_order_matched_qty * order.bot_order_matched_price
    
        
        pnl  = totalSellVol - totalBuyVol 
        realPnl = pnl - commission
        # dayFee = 0
        # if(self.action.bot_act_dayfee is not None): 
        #     dayFee = self.action.bot_act_dayfee
        # realPnl -= dayFee
        
        self.action.bot_act_pending = 0
        self.action.bot_act_pnl = pnl
        self.action.bot_act_exit_time = int(self.runtime)
        self.action.bot_act_real_pnl = realPnl
        self.action.bot_act_commission = commission
        self.action.bot_act_qty = matchedQty

        if(matchedQty > 0):
            icon = Telegram.TELE_ICON_TAKEPROFIT if realPnl > 0 else Telegram.TELE_ICON_STOPLOSS
            self.sendTele("notice","==== SUMMARY ====", icon, {
                "Flow": self.action.bot_act_flow,
                "Total qty": matchedQty,
                "Total buy": f"{totalBuyVol:,}",
                "Total sell": f"{totalSellVol:,}",
                "PNL": f"{pnl:,}",
                "Fee": f"{commission:,}",
                # "Day Fee": f"{dayFee:,}",
                "Real PNL": f"{realPnl:,}"
            })
         
   
    # =====================================
    
    # === Block Monitor position Status ===

    def monitorPosition(self):
        # startTime = self.runtime * 1000
        self.monitorEditOrder()
        self.monitorOrder()

        if(self.action.bot_act_status_close is None):

            if(self.action.bot_act_status_enter == Action.STATUS_ENTER_SENDING):
                self.monitorEnterSending()
            if(self.action.bot_act_status_enter == Action.STATUS_ENTER_PENDING):
                self.monitorEnterCancel()
            if(self.action.bot_act_status_enter == Action.STATUS_ENTER_PENDING):
                self.monitorEnterPending()
            if(self.action.bot_act_status_enter == Action.STATUS_ENTER_PART):
                self.monitorEnterPart()
                
            if(self.action.bot_act_status_exit == Action.STATUS_EXIT_PART):
                self.monitorExitPart()
            if(self.action.bot_act_status_exit == Action.STATUS_EXIT_SENDING):
                self.monitorExitSending()
            if(self.action.bot_act_status_exit == Action.STATUS_EXIT_PENDING):
                self.monitorExitCancel()
            if(self.action.bot_act_status_exit == Action.STATUS_EXIT_PENDING):
                self.monitorExitPending()

            if(self.action.bot_act_status_enter in [Action.STATUS_ENTER_PART, Action.STATUS_ENTER_FULL]):
                self.monitorClosePosition()

        # print(f"Monitor time = {startTime - self.runtime*1000}ms")

    def monitorEnterSending(self):
        # print('monitorEnterSending')
        isSent = True
        order:Order
        orderIds = list(self.action.orders.keys())
        for orderId in orderIds:
            order:Order = self.action.orders[orderId]
            if(order.bot_order_act_type != Order.ACT_TYPE_MAKE_ORDER): continue
            if(order.bot_order_status == Order.STATUS_SENDING):
                isSent = False
                break

        if(isSent):
            self.updateEvent({
                'bot_act_status_enter': Action.STATUS_ENTER_PENDING
            })

    def monitorEnterCancel(self):
        # print("monitorEnterCancel")
        cancelCondition = self.getFlowData(self.action.bot_act_flow, 'enter_cancel')
        if(cancelCondition is None): return
        cancelResult = self.compareOr(cancelCondition)
        if(not cancelResult['result']): raise Exception(cancelResult['message'])
        if(cancelResult['data'] is not None and cancelResult['data']):
        
            # self.updateEvent({
            #     'bot_act_status_enter': Action.STATUS_ENTER_CANCEL
            # })
            self.sendTele('notice', f'Cancel Enter order', Telegram.TELE_ICON_CANCEL, {
                "Flow": self.action.bot_act_flow,
                "Reason": cancelResult['message']
            })
            #cancel all make_order order
            order: Order
            canceled = 0
            orderIds = list(self.action.orders.keys())
            for orderId in orderIds:
                order:Order = self.action.orders[orderId]
                if(order.bot_order_status in [Order.STATUS_ERROR]): continue
                if(order.bot_order_act_type == Order.ACT_TYPE_MAKE_ORDER):
                    if(order.bot_order_status not in [Order.STATUS_CANCELED , Order.STATUS_MATCHED_FULL]):
                        result = self.cancelOrder(order, cancelResult['message'])
                        if(not result['result']):
                            self.sendTele('warning', f'Can not cancel order {order.bot_order_id}', Telegram.TELE_ICON_WARNING, {
                                "Log": result['message']
                            })
                        else:
                            canceled += 1
            if(canceled == 0):
                self.updateActionStatus()

    def monitorEnterPending(self):
        # print("monitorEnterPending")
        enterAction:dict = self.getFlowData(self.action.bot_act_flow, 'enter_action')
        orderType = enterAction.get('order_type', None)
        if(orderType is None): raise Exception('No Order Type')

        if(orderType == Order.TYPE_LO):
            isKeep = enterAction.get('keep', False)
            if(not isKeep):
                price = self.calculateElement(enterAction.get('price', 0))
                if(not price['result']): return price
                log = price['message']
                price = price['data']

                if(price == 0): return
                if(price > 0): price = round(price, 1)

                orders = self.action.orders
                slip = self.calculateElement(enterAction.get('slip', 0))['data']
                for orderId in orders:
                    order:Order = self.action.orders[orderId]
                    if(order.bot_order_act_type != Order.ACT_TYPE_MAKE_ORDER): continue
                    if(order.bot_order_status not in [Order.STATUS_ERROR, Order.STATUS_MATCHED_FULL, Order.STATUS_CANCELED]):
                        # print(f"Order price {order.bot_order_price} {price}")
                        if(abs(order.bot_order_price - price) > slip and order.bot_order_type == Order.TYPE_LO):
                            self.editOrder(order, order.bot_order_qty, price , log)

    def monitorEnterPart(self):
        enterCondition = self.getFlowData(self.action.bot_act_flow, 'enter_condition')
        if(enterCondition is None): return
        logResult = self.compareOr(enterCondition)
        # print(logResult)
        if(not logResult['result']): return logResult
        if(logResult['data'] is not None and logResult['data']):
            enterAction = self.getFlowData(self.action.bot_act_flow, 'enter_action')
            self.updateEvent({
                'bot_act_status_enter': Action.STATUS_ENTER_PENDING
            })
            self.processMakeOrderAction(enterAction, Order.ACT_TYPE_MAKE_ORDER, logResult['message'])

    def monitorExitPart(self):

        # print("monitorMatchedPosition")
        exitCondition = self.getFlowData(self.action.bot_act_flow, 'exit_condition')
        if(exitCondition is None):
            return
        exitResult = self.compareOr(exitCondition)
        if(not exitResult['result']): raise Exception(exitResult['message'])
        if(exitResult['data'] is not None and exitResult['data']):
            exitAction = self.getFlowData(self.action.bot_act_flow, 'exit_action')
            if(exitAction is None or len(exitAction) == 0): raise Exception('No exit actions')
            self.updateEvent({
                'bot_act_exit_data': json.dumps(self.checkData, default=str),
                'bot_act_exit_reason': exitResult['message'],
                'bot_act_status_exit' : Action.STATUS_EXIT_SENDING
            })

            self.processCloseOrderAction(exitAction, Order.ACT_TYPE_CLOSE_ORDER, exitResult['message'])

                
    def monitorExitSending(self):
        # print('monitorExitSending')
        
        isSent = True
        order:Order
        orderIds = list(self.action.orders.keys())
        for orderId in orderIds:
            order:Order = self.action.orders[orderId]
            if(order.bot_order_act_type != Order.ACT_TYPE_CLOSE_ORDER): continue
            if(order.bot_order_status == Order.STATUS_SENDING):
                isSent = False
                break

        if(isSent):
            self.updateEvent({
                'bot_act_status_exit': Action.STATUS_EXIT_PENDING
            })    

    def monitorExitCancel(self):
        # print("monitorExitCancel")
        cancelCondition = self.getFlowData(self.action.bot_act_flow, 'exit_cancel')
        if(cancelCondition is None): return
        cancelResult = self.compareOr(cancelCondition)
        if(not cancelResult['result']): raise Exception(cancelResult['message'])
        if(cancelResult['data'] is not None and cancelResult['data']):
            #cancel all make_order order
            self.updateEvent({
                'bot_act_status_exit': Action.STATUS_EXIT_CANCEL
            })
            self.sendTele('notice', f'Cancel Exit order', Telegram.TELE_ICON_CANCEL, {
                "Flow": self.action.bot_act_flow,
                "Reason": cancelResult['message']
            })

            order: Order
            canceled = 0
            orderIds = list(self.action.orders.keys())
            for orderId in orderIds:
                order:Order = self.action.orders[orderId]
                if(order.bot_order_status in [Order.STATUS_ERROR]): continue
                if(order.bot_order_act_type == Order.ACT_TYPE_CLOSE_ORDER):
                    if(order.bot_order_status not in [Order.STATUS_CANCELED , Order.STATUS_MATCHED_FULL, Order.STATUS_SENDING]):
                        result = self.cancelOrder(order, cancelResult['message'])
                        if(not result['result']):
                            self.sendTele('warning', f'Can not cancel order {order.bot_order_id}', Telegram.TELE_ICON_WARNING, {
                                "Log": result['message']
                            })
                        else:
                            canceled += 1
            if(canceled == 0):
                self.updateActionStatus()

    def monitorClosePosition(self):

        if(self.action.bot_act_status_close == Action.STATUS_CLOSE_PENDING): return
        if(self.action.bot_act_status_close == Action.STATUS_CLOSE_FORCE):
            closeResult = Reply.make(True, 'Force to Close', True)
        else:
            closeCondition = self.getFlowData(self.action.bot_act_flow, 'close_condition')
            if(closeCondition is None):
                return
            closeResult = self.compareOr(closeCondition)
            

        if(not closeResult['result']): raise Exception(closeResult['message'])
        if(closeResult['data'] is not None and closeResult['data']):
            closeAction = self.getFlowData(self.action.bot_act_flow, 'close_action')
            if(closeAction is None or len(closeAction) == 0): raise Exception('No close actions')
            self.updateEvent({
                'bot_act_exit_data': json.dumps(self.checkData, default=str),
                'bot_act_exit_reason': closeResult['message'],
                'bot_act_status_close' : Action.STATUS_CLOSE_PENDING
            })
            #Cancel all order
            orderIds = list(self.action.orders.keys())
            for orderId in orderIds:
                order:Order = self.action.orders[orderId]
                if(order.bot_order_status in [Order.STATUS_ERROR]): continue
                if(order.bot_order_status not in [Order.STATUS_CANCELED , Order.STATUS_MATCHED_FULL, Order.STATUS_SENDING]):
                    result = self.cancelOrder(order, closeResult['message'])
                    if(not result['result']):
                        self.sendTele('warning', f'Can not cancel order {order.bot_order_id}', Telegram.TELE_ICON_WARNING, {
                            "Log": result['message'],
                            "Reason": closeResult['message']
                        })

            self.sendTele('notice', f'Close matched order', Telegram.TELE_ICON_CANCEL, {
                "Flow": self.action.bot_act_flow,
                "Reason": closeResult['message']
            })
            self.processCloseOrderAction(closeAction, Order.ACT_TYPE_CLOSE_ORDER, closeResult['message'])

    def monitorExitPending(self):
        exitAction:dict = self.getFlowData(self.action.bot_act_flow, 'exit_action')
        orderType = exitAction.get('order_type', None)
        if(orderType is None): raise Exception('No Order Type')

        if(orderType == Order.TYPE_LO):
            isKeep = exitAction.get('keep', False)
            if(not isKeep):
                price = self.calculateElement(exitAction.get('price', 0))
                if(not price['result']): return price
                log = price['message']
                price = price['data']
                

                if(price == 0): return
                if(price > 0): price = round(price, 1)

                orders = self.action.orders
                slip = self.calculateElement(exitAction.get('slip', 0))['data']
                for orderId in orders:
                    order:Order = self.action.orders[orderId]
                    if(order.bot_order_act_type != Order.ACT_TYPE_CLOSE_ORDER): continue
                    if(order.bot_order_status not in [Order.STATUS_ERROR, Order.STATUS_MATCHED_FULL, Order.STATUS_CANCELED]):
                        if(abs(order.bot_order_price - price) > slip and order.bot_order_type == Order.TYPE_LO):
                            self.editOrder(order, order.bot_order_qty, price, log)
                    

    # =====================================
    
    # === Block process Pair trading ===

    def checkPairingTarget(self):
        
        pairConfig:dict = self.getFlowData(self.action.bot_act_flow, 'pair_trading')
        if(pairConfig is None): return

        # print("Start thread monitor Pairing")
        
        symbol = self.symbol
        pairSymbol = self.calculateElement(pairConfig.get('symbol', None))['data']
        pairInvert = pairConfig.get('invert', True)

        if(pairSymbol is None or symbol is None): return
       
        if(self.action is None or self.action.bot_act_pending == 0): 
            self.updateEvent({
                'bot_act_status_pair': Action.PAIR_STATUS_OK
            })
            return

        pairSymbolWaitingQty = 0
        pairSymbolMatchedQty = 0
        symbolMatchedQty = 0
        order: Order
        orderIds = list(self.action.orders.keys())
        for orderId in orderIds:
            order:Order = self.action.orders[orderId]
            if(order.bot_order_status in [Order.STATUS_ERROR]): continue

            if(order.bot_order_symbol == symbol):
                if(order.bot_order_side == Order.SIDE_BUY):
                    symbolMatchedQty += order.bot_order_matched_qty
                else:
                    symbolMatchedQty -= order.bot_order_matched_qty
            
            if(order.bot_order_act_type == Order.ACT_TYPE_PAIR_ORDER):
                if(order.bot_order_symbol == pairSymbol):
                    if(order.bot_order_side == Order.SIDE_BUY):
                        pairSymbolMatchedQty += order.bot_order_matched_qty
                        if(order.bot_order_status not in [Order.STATUS_CANCELED, Order.STATUS_MATCHED_FULL]):
                            pairSymbolWaitingQty += order.bot_order_unmatched_qty
                    else:
                        pairSymbolMatchedQty -= order.bot_order_matched_qty
                        if(order.bot_order_status not in [Order.STATUS_CANCELED, Order.STATUS_MATCHED_FULL]):
                            pairSymbolWaitingQty -= order.bot_order_unmatched_qty

        # print(f"Pair result {symbolMatchedQty} {pairSymbolWaitingQty} + {pairSymbolMatchedQty}")
        need2Pair = False
        pairSymbolExpectQty = round(pairSymbolMatchedQty + pairSymbolWaitingQty, 9)
        symbolMatchedQty = round(symbolMatchedQty, 9)
        if(pairInvert):
            if(symbolMatchedQty == -pairSymbolExpectQty):
                #pair order is send and work ok
                return
            else:
                need2Pair = True
                pairSide = Order.SIDE_SELL
                pairQty = symbolMatchedQty + pairSymbolExpectQty
                if(pairQty < 0):
                    pairSide = Order.SIDE_BUY
                    pairQty = -pairQty

        else:
            if(symbolMatchedQty == pairSymbolExpectQty):
                #pair order is send and work ok
                return
            else:
                #need to send pair order
                need2Pair = True
                pairSide = Order.SIDE_BUY
                pairQty = symbolMatchedQty - pairSymbolExpectQty
                if(pairQty < 0):
                    pairSide = Order.SIDE_SELL
                    pairQty = -pairQty

        pairQty = round(pairQty, 9)
        if(need2Pair):

            self.updateEvent({
                'bot_act_status_pair': Action.PAIR_STATUS_PENDING
            })

            pairOrder = Order()
            pairOrder.bot_order_action = self.action.bot_act_id
            pairOrder.bot_order_camp = self.id
            pairOrder.bot_order_qty = pairQty
            pairOrder.bot_order_act_type = Order.ACT_TYPE_PAIR_ORDER
            pairOrder.bot_order_symbol = pairSymbol
            pairOrder.bot_order_type = Order.TYPE_MP
            pairOrder.bot_order_price = 0
            pairOrder.bot_order_matched_qty = 0
            pairOrder.bot_order_unmatched_qty = pairQty
            pairOrder.bot_order_side = pairSide
            pairOrder.bot_order_status = Order.STATUS_SENT
            pairOrder.bot_order_time = int(self.runtime)
            pairOrder.bot_order_commission = 0
            self.action.addOrder(pairOrder)

            icon = Telegram.TELE_ICON_LONG if order.bot_order_side == Order.SIDE_BUY else Telegram.TELE_ICON_SHORT
            self.sendTele('notice', f'Make PAIR ORDER', icon, {
                "Flow": self.action.bot_act_flow,
                "Symbol": pairOrder.bot_order_symbol,
                "Side": pairOrder.bot_order_side,
                "Price": pairOrder.bot_order_price,
                "Qty": pairQty
            })

    def updateActionStatus(self):
        symbolData = self.getEnterStatus()
        self.log(symbolData)
        self.log(self.symbol)
        symbol = self.symbol
        symbolData = symbolData.get(symbol, {})
        
        flowName = self.action.bot_act_flow
        matched = round(symbolData.get('matched', 0), 9)
        enterWaiting = round(symbolData.get('enter_waiting', 0), 9)
        closeWaiting = round(symbolData.get('close_waiting', 0), 9)
        enterAction:dict = self.getFlowData(flowName, 'enter_action')
        if(enterAction is None): return
        
        #update enter status
        quantity = self.calculateElement(enterAction.get('quantity', None))['data']
        if(quantity is not None): quantity = float(quantity)
        
        totalQty = self.calculateElement(enterAction.get('total', None))['data']
        if(totalQty is None): totalQty=quantity
        if(totalQty is None): raise Exception("Can not define total quantity")
        totalQty = round(float(totalQty),9)

        updateData = {}

        #Update enter status
        if(enterWaiting == 0):
            if(matched != 0 and abs(matched) < totalQty): 
                updateData['bot_act_status_enter'] = Action.STATUS_ENTER_PART
            if(matched != 0 and abs(matched) >= totalQty):
                updateData['bot_act_status_enter'] = Action.STATUS_ENTER_FULL
        #update exit status
        if(closeWaiting == 0):
            if(matched + enterWaiting + closeWaiting != 0):
                updateData['bot_act_status_exit'] = Action.STATUS_EXIT_PART
                if(self.action.bot_act_status_close == Action.STATUS_CLOSE_PENDING): 
                    updateData['bot_act_status_close'] = None
                
            if(matched == 0 and closeWaiting == 0 and enterWaiting == 0):
                updateData['bot_act_status_exit'] = Action.STATUS_EXIT_FULL
                if(self.action.bot_act_status_close == Action.STATUS_CLOSE_PENDING): 
                    updateData['bot_act_status_close'] = Action.STATUS_CLOSE_DONE
        
                
        if(len(updateData) > 0):
            self.updateEvent(updateData, False)
        
        self.log(f"{self.action.bot_act_status_enter} {self.action.bot_act_status_exit} {self.action.bot_act_status_pair} {self.action.bot_act_status_close}")
        self.checkFinish()

    def checkFinish(self):
        symbolData = self.getPositionSymbol()
        self.log(symbolData)
        isFinished = True
        for symbol in symbolData:
            symDt = symbolData[symbol]
            if(round(symDt['matched'], 9) != 0 or round(symDt['waiting'], 9) != 0):
                isFinished = False
                break
        if(isFinished):

            if(self.action.bot_act_status_close is not None):
                self.updateEvent({
                    'bot_act_status_exit': Action.STATUS_CLOSE_DONE
                })

            self.summaryAction()

    def updateDayFee(self):
        if(self.action is None or self.action.bot_act_pending == 0): return
        currentDayFee = self.action.bot_act_dayfee
        if(currentDayFee is None): currentDayFee = 0
        currentPosition = self.getPositionSymbol()
        for sym in currentPosition:
            currentDayFee += abs(currentPosition[sym].get('matched', 0)) * 2500
        self.updateEvent({
            'bot_act_dayfee': currentDayFee
        })
    # =====================================     

    def log(self, mess, end='\n'):
        if(not self.showLog): return
        ms = f"Campaign [{self.id}] {mess}"
        print(ms, end=end)
    
    def sendTele(self, level, title, icon=None, datas={}):
        if(not self.showLog): return
        '''
        :param level : notice warning error
        '''
        dateTime = datetime.fromtimestamp(floor(self.runtime/1000))
        if icon is None:
            icon = Telegram.TELE_ICON_WARNING
        ms = f"{icon} Campaign [{self.id}] {title}"
        ms += "\n- Time: " + str(dateTime)
        for key in datas:
            ms += f"\n- {key}: {str(datas[key])}"
        print(ms)

    def updateEvent(self, editData, force = True):
        '''
        Update position to memory
        - if force update to redis and database
        - Update to redis and database each 10s
        '''
        if(not self.action is None):
            for key in editData:
                setattr(self.action, key, editData[key])        
        return Reply.make(True, 'success', self.action)

    def getActions(self):
        actions = {}
        for act in self.actions:
            actions[act] = self.actions[act].toDict()
        return actions
        

