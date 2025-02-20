import uuid
from helper.Reply import Reply
from helper.Defaults import *
from .Model.BotAction import BotAction
from helper.Timer import *
from models.Mongo.MongoModel import MongoModel
from .function import *
from .Model.Constant import *
from .Model.BotBill import BotBill
from .Model.BotOrder import BotOrder
import pandas as pd
from math import floor

from helper.Telegram import Telegram
from datetime import datetime


class Campaign():

    def __init__(self, campaign:dict, strategy:dict, params:dict={}, showLog=True):
        super().__init__()
        
        self.action:BotAction = None
        self.periodAction:BotAction = None
        self.actions:dict(str,BotAction) = {}
        self.showLog = showLog

        self.database = MongoModel('backtest_data').setCollection('pair_indicator')
        self.params = params
        self.strategy = strategy

        self.checkData = {}
        self.priceData = {}
        self.runtime = None

        self.id = campaign.get('id', None)
        self.log(f"Campain UUID = {self.id}")

        self.startDay = campaign.get('start_date',"2022_01_01")
        self.stopDay = campaign.get('stop_date', "2022_10_01")

        self.commissRate = 0.04
        self.symbol = None
        #======================
        self.symbols = ['MATICUSDT', 'THETAUSDT']
        
        

    def initial(self):
        fillStrategy(self.strategy, self.params)
        #reset tairling param
        self.advBase = None
        self.profitBase = None

    def run(self):
        
        startTime = datetime.strptime(self.startDay, '%Y_%m_%d').replace(tzinfo=VN_TZ).timestamp()
        stopTime = datetime.strptime(self.stopDay, '%Y_%m_%d').replace(tzinfo=VN_TZ).timestamp()

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
                    for symbol in self.symbols:
                        self.priceData[symbol] = {
                            'last': float(self.checkData['pair'].get(f'{symbol}_lastPrice', 0)),
                            'bestBid': float(self.checkData['pair'].get(f'{symbol}_best1Bid', 0)),
                            'volBid': float(self.checkData['pair'].get(f'{symbol}_best1BidVol', 0)),
                            'bestAsk': float(self.checkData['pair'].get(f'{symbol}_best1Offer', 0)),
                            'volAsk': float(self.checkData['pair'].get(f'{symbol}_best1OfferVol', 0)),
                        }
                
                self.runtime = float(timestamp)
                self.process()
                if(not self.checkResult['result']):
                    print(self.checkResult)
                    break
                processed += 1
                if(processed % 1000 == 0):
                    self.log(f"Process {processed}/{total}", end='\r')

    def getData(self, startTime, stopTime):
        
        self.log(f"Get data from {datetime.fromtimestamp(startTime, tz=VN_TZ)}({startTime}) to {datetime.fromtimestamp(stopTime, tz=VN_TZ)}({stopTime})")
        
        # get pair bollinger band
        timestamps = []
        pairBandDict = {}
        
        pairBandData = list(self.database.collection.find({'symbol': 'USDTPERP', 'timestamp': {'$gte': startTime, '$lte': stopTime}}, {'_id':0}))
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
            # print(checkResult)
            if(not checkResult['result']):
                self.checkResult = checkResult
            else:
                # print("Check Order")
                self.checkResult = Reply.make(True, 'Check Order', False)    

    
    # == Block Check event and get event ==

    def checkAction(self):
        if(self.action is None): return False
        if(self.action.bot_act_pending == 0): return False
        return True


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
                result = Reply.make(True, ' OR '.join(logs), None)
                return result
            if(result['data'] is True):
                result = Reply.make(True, ' OR '.join(logs), True)
                return result
        result = Reply.make(True, ' OR '.join(logs), False)
        return result

    def getPairData(self, struct:dict):
        
        symbol = struct.get('symbol', None)
        if(symbol is None): return Reply.make(False, 'Symbol not defined')
        symbol = self.calculateElement(symbol)['data']

        field = struct.get('field', None)
        if(field is None): return Reply.make(False, 'Field not defined')

        symbolField = f"{field}"
        pairData = self.checkData.get('pair', {})

        if(symbolField not in pairData):
            return Reply.make(True, f'{field} not exist', None)
        
        value = pairData[symbolField]
        des = f"Pair {symbol} {field}({value})"

        if(isNumeric(value)):
            value = Number(value)
            
            percent = struct.get('percent', None)
            if(percent is not None):
                percent = float(percent)
                value = value * percent/100
                des = f"{percent}% {des}"
                
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
        
        return Reply.make(True, f"{des}({value})", value)

    def getSession(self):
        pairData = self.checkData.get('pair', {})
        session = pairData.get('F2.session', pairData.get('F1.session', None))
        return session
    
    def getBaseAdvantage(self):
        if(self.advBase is None): return 0
        return self.advBase
    
    def getBaseProfit(self):
        if(self.profitBase is None): return 0
        return self.profitBase
    
    def isAfterStoploss(self, flowName):
        if(self.periodAction is None): return False
        if(self.periodAction.bot_act_flow != flowName): return False
        if(self.periodAction.bot_act_real_pnl < 0): return True
        return False
        
    def calculateElement(self, struct) -> dict:
        if(type(struct) in [int, float, bool]): return Reply.make(True, str(struct), struct)
        if(struct is None): return Reply.make(True, str(struct), struct)
        if(type(struct) is str):

            if(struct == 'session'):
                value = self.getSession()
                return Reply.make(True, f"{struct}({value})", value)

            if(struct == 'time_in_date'):
                value = timeInDate(self.runtime)
                return Reply.make(True, f"{struct}({value})", value)
            
            if(struct == 'in_order_time'):
                value = inOrderTime(self.runtime)
                return Reply.make(True, f"{struct}({value})", value)
            
            if(struct == 'is_maturity_date'):
                value = is_maturity_date(self.runtime)
                return Reply.make(True, f"{struct}({value})", value)
            
            if(struct == 'is_maturity_after'):
                value = is_maturity_after(self.runtime)
                return Reply.make(True, f"{struct}({value})", value)

            if(struct == 'timestamp'):
                value = int(self.runtime)
                return Reply.make(True, f"{struct}({value})", value)
            
            if(struct in self.defined):
                return self.defined[struct]
            else:
                return Reply.make(True, struct, struct)
            
        if(type(struct) is dict):
            structType = struct.get('type', None)
            if(structType is None): return Reply.make(False, 'No type Defined')

            if(structType == 'pair'):
                return self.getPairData(struct)  
            
            if(structType == 'event'):
                if(self.action is None): return Reply.make(False, 'No Event')
                column = struct.get('column', None)
                column = 'bot_act_' + str(column)
                
                if(column == 'bot_act_interval'):
                    value = (int(self.runtime*1000) - int(self.action.bot_act_enter_time))/60000
                else:
                    if(not hasattr(self.action, column)): return Reply.make(False, 'Can not find column ' + column)
                    value = getattr(self.action, column)
                des = f"Event {column}({value})"
                if(isNumeric(value)):
                    value = Number(value)
                    
                    percent = struct.get('percent', None)
                    if(percent is not None):
                        percent = float(percent)
                        value = value * percent/100
                        des = f"Event {percent}% {column}({value})"
                        
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
                        
                return Reply.make(True, f"{des}({value})", value)

            elif(structType == 'calculate'):
                number1 = get(struct, 'number_1', None)
                number2 = get(struct, 'number_2', None)
                logic = get(struct, 'logic', None)
                if(number1 is None or number2 is None or logic is None):
                    Reply.make(False, "Please define number_1, number_2 and logic " + json.dumps(struct))
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
                return Reply.make(True, f"{des}({value})", value)

            elif(structType == 'if'):
                condition = get(struct, 'condition', None)
                trueValueCfg = get(struct, 'true', None)
                falseValueCfg = get(struct, 'false', None)
                if(condition is None or trueValueCfg is None or falseValueCfg is None):
                    Reply.make(False, "Please define condition, true value and false value " + json.dumps(struct))
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
            
            elif(structType == 'after_stoploss'):
                
                flowName = get(struct, 'flow', None)
                if(flowName is None):
                    Reply.make(False, f"Please define {flowName}")
                value = self.isAfterStoploss(flowName)
                des = 'After stoploss'
                return Reply.make(True, f"{des}({value})", value)
            
            elif(structType == 'kline'):
                frame = get(struct, 'frame', None)
                index = get(struct, 'index', 0)
                column = get(struct, 'column', None)
                symbol = get(struct, 'symbol', self.symbol)
                index = int(index) - 1
                des = f"Kline {symbol} {frame}({index}) {column}"
                if(frame is None or index is None or column is None):
                    return Reply.make(False, 'Please define symbol, frame, column and index ' + des + json.dumps(struct))
    
                try:
                    
                    value = self.checkData['kline'][symbol][frame][index][column]
                    if(isNumeric(value)): 
                        
                        percent = struct.get('percent', None)
                        if(percent is not None):
                            percent = float(percent)
                            value = value * percent/100
                            des = f"{percent}% {des}"
                            
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
                            
                    return Reply.make(True, f"{des}[{value}]", value)
                except Exception:
                    return Reply.make(False, f'Can not get {des}')
            
            else:
                
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
                    value = checkData[index][column]
                    
                    if(isNumeric(value)): 
                        
                        percent = struct.get('percent', None)
                        if(percent is not None):
                            percent = float(percent)
                            value = value * percent/100
                            des = f"{percent}% {des}"
                            
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
                            
                    return Reply.make(True, f"{des}[{value}]", value)
                
                except Exception as e:
                    return Reply.make(False, f'Can not get Data {symbol} {indexCfg} {column}')
    
    
    
        
    def processDefined(self):
        self.defined = {}
        if('defined' in self.strategy):
            for key in self.strategy['defined']:
                self.defined[key] = self.calculateElement(self.strategy['defined'][key])    
    
    def getFlowData(self, flowN, key) -> dict:
        flowData:dict = self.strategy.get(flowN, None)
        if(flowData is None): return None
        return flowData.get(key, None)
    
    def getEnterPhase(self, flowName, phase) -> dict:
        phases = self.getFlowData(flowName, "enter")
        if(len(phases) > phase):
            return phases[phase]
        return None

        
    # ======================================
    
    # == Block create position =============     
    def checkNewAction(self):
        '''
        - Lấy các flow của strategy
        - Lần lượt kiểm tra điều kiện vào lệnh
        '''
        
        logResults = {}
        
        interval = self.calculateElement('interval')['data']
        if(interval == 'interval'): 
            interval = 1000
        else:
            interval = interval * 60 * 1000
        
        for flowN in self.strategy:
            if(flowN == 'defined'): continue
            
            # Check campaign side and flow side
            flowSide:dict = self.getFlowData(flowN, 'side')
            if(flowSide is None): raise Exception(f"Please define side for flow {flowN}")
           
            phase0:dict = self.getEnterPhase(flowN, 0)
            if(phase0 is None): continue
            enterCondition = phase0.get('condition')
            if(enterCondition is None): continue
            logResult = self.compareOr(enterCondition)
            logResults[flowN] = logResult
            if(not logResult['result']): return logResult
            # print(logResult)
            if(logResult['data'] is not None and logResult['data']):
                
                if(interval > 0):
                    if(self.periodAction is not None and self.periodAction != False):
                        exitTime = self.periodAction.bot_act_exit_time
                        if(exitTime is not None):
                            if(self.runtime*1000 - exitTime < interval):
                                return Reply.make(True, 'Deny because interval time', logResults)
                            
                self.makeAction(flowN, 0, logResult['message'])
                return Reply.make(True, 'Matched', logResults)

        return Reply.make(True, 'Unmatched', logResults)

    def makeAction(self, flowName, phase, reason=''):
        BotAction.bot_act_status_matched
        
        actionObj = BotAction(
            bot_act_enter_time = int(self.runtime*1000),
            bot_act_enter_data = json.dumps(self.checkData),
            bot_act_enter_reason = reason,
            bot_act_status_enter = ActionEnterStatus.STATUS_ENTER_WAITTING,
            bot_act_enter_phase = phase,
            bot_act_status_matched = ActionMatchedStatus.STATUS_EMPTY,
            bot_act_matched_qty = 0,
            bot_act_status_exit = None,
            bot_act_flow = flowName,
            bot_act_pending = 1,
            bot_act_bot_type = 2,
            bot_act_dayfee = 0,
            bot_act_dayfee_time = int(self.runtime)                   
        )
        
        self.actions[actionObj.bot_act_id] = actionObj
        self.action = actionObj
        self.orderThreads = {}

        self.sendTele('notice', '==== START ACTION ====', Telegram.TELE_ICON_WAITTING, {
            "Status": ActionEnterStatus.STATUS_ENTER_WAITTING,
            "Flow": flowName,
            "Reason": reason
        })
        
        self.monitorEnterWaitting()
   
    def makeEnterBill(self, billCfg, reason=None)->BotBill:
        billPos = {}
        for pos in billCfg:
            pos:dict
            symbol = self.calculateElement(pos.get('symbol'))['data']
            if(symbol is None): raise Exception("No symbol")
            quantity = self.calculateElement(pos.get('quantity'))['data']
            if(quantity is None): raise Exception("No quantity")
            
            qty = int(quantity)
            side = pos.get('order_side')
            if(symbol not in billPos): billPos[symbol] = 0
            if(side == OrderSide.SIDE_BUY):
                billPos[symbol] += qty
            else:
                billPos[symbol] -= qty
        
        billObj = BotBill(
            bot_bill_action = self.action.bot_act_id,
            bot_bill_act_type = BillActType.ACT_TYPE_MAKE_ORDER,
            bot_bill_phase = self.action.bot_act_enter_phase,
            bot_bill_status = BillStatus.STATUS_UNCOMPLETED,
            bot_bill_ignore = 0,
            bot_bill_reason = reason
        )
        billObj.setExpectPosition(billPos)
        self.action.addBill(billObj)
        return billObj
    
    def makeExitBill(self, reason=None)->BotBill:
        billObj = BotBill(
            bot_bill_action = self.action.bot_act_id,
            bot_bill_act_type = BillActType.ACT_TYPE_EXIT_ORDER,
            bot_bill_phase = self.action.bot_act_enter_phase,
            bot_bill_status = BillStatus.STATUS_UNCOMPLETED,
            bot_bill_ignore = 0,
            bot_bill_reason = reason
        )
        self.action.addBill(billObj)
        return billObj
      
    def makeCloseBill(self, reason=None)->BotBill:
        billObj = BotBill(
            bot_bill_action = self.action.bot_act_id,
            bot_bill_act_type = BillActType.ACT_TYPE_CLOSE_ORDER,
            bot_bill_phase = None,
            bot_bill_status = BillStatus.STATUS_UNCOMPLETED,
            bot_bill_ignore = 0,
            bot_bill_reason = reason
        )
        
        self.action.addBill(billObj)
        return billObj

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
            order:BotOrder = pendingOrder[orderId]
            symbol = order.bot_order_symbol
            bestBid = self.priceData[symbol]['bestBid']
            volBid = self.priceData[symbol]['volBid']

            bestAsk = self.priceData[symbol]['bestAsk']
            volAsk = self.priceData[symbol]['volAsk']

            matchQty = None
           
            if(order.bot_order_type == OrderType.TYPE_LO):
                
                if(order.bot_order_matched_time is not None and self.runtime*1000 - order.bot_order_matched_time < 5000):
                    continue
                orderPrice = float(order.bot_order_price)
                orderUnmatch = float(order.bot_order_unmatched_qty)
                
                if(order.bot_order_side == OrderSide.SIDE_BUY):

                    if(bestAsk > 0 and bestAsk <= orderPrice):
                        if(self.runtime * 1000 - order.bot_order_time > 2000):
                            matchPrice = orderPrice
                        else:
                            matchPrice = bestAsk

                        if(orderUnmatch < volAsk):
                            matchQty = orderUnmatch
                        else:
                            matchQty = volAsk

                elif(order.bot_order_side == OrderSide.SIDE_SELL):
                    if(bestBid > 0 and bestBid >= orderPrice):
                        if(self.runtime * 1000 - order.bot_order_time > 2000):
                            matchPrice = orderPrice
                        else:
                            matchPrice = bestBid

                        if(orderUnmatch < volBid):
                            matchQty = orderUnmatch
                        else:
                            matchQty = volBid

                if(matchQty is not None):
                    newUnmatch = orderUnmatch - matchQty
                    if(order.bot_order_matched_qty > 0):
                        newMatch = order.bot_order_matched_qty + matchQty
                        newPrice = (matchQty * matchPrice + order.bot_order_matched_qty * order.bot_order_matched_price)/newMatch
                    else:
                        newMatch = matchQty
                        newPrice = matchPrice
                    
                   
                    newStatus = OrderStatus.STATUS_MATCHED_PART if newUnmatch > 0 else OrderStatus.STATUS_MATCHED_FULL
                    
                    self.action.updateOrder(order, {
                        'bot_order_matched_price': newPrice,
                        'bot_order_matched_qty': newMatch,
                        'bot_order_unmatched_qty': newUnmatch,
                        'bot_order_status': newStatus,
                        'bot_order_matched_time': int(self.runtime * 1000),
                    })
                    self.calCommit(order)
                    
                    self.sendTele('notice', 'Matched', Telegram.TELE_ICON_MATCHED, {
                        "Flow": self.action.bot_act_flow,
                        "Symbol": order.bot_order_symbol,
                        "Side": order.bot_order_side,
                        "Price": order.bot_order_matched_price,
                        "Qty": order.bot_order_matched_qty,
                        "Commission": order.bot_order_commission
                    })
                    isChange = True

            if(order.bot_order_type == OrderType.TYPE_MP):
                if(order.bot_order_side == OrderSide.SIDE_BUY):
                    matchPrice = bestAsk
                else:
                    matchPrice = bestBid
                if(matchPrice > 0):
                    
                    self.action.updateOrder(order, {
                        'bot_order_matched_price': matchPrice,
                        'bot_order_matched_qty': order.bot_order_qty,
                        'bot_order_unmatched_qty': 0,
                        'bot_order_status': OrderStatus.STATUS_MATCHED_FULL,
                        'bot_order_matched_time': int(self.runtime * 1000)
                    })
                    self.calCommit(order)
                    self.sendTele('notice', 'Matched', Telegram.TELE_ICON_MATCHED, {
                        "Flow": self.action.bot_act_flow,
                        "Symbol": order.bot_order_symbol,
                        "Side": order.bot_order_side,
                        "Price": order.bot_order_matched_price,
                        "Qty": order.bot_order_matched_qty,
                        "Commission": order.bot_order_commission
                    })
                    isChange = True

               
        
        if(isChange):
            self.onChangeOrder(order)
    
    def onChangeOrder(self, order:BotOrder):
        billId = order.bot_order_bill
        if(billId in self.action.bills):
            bill:BotBill = self.action.bills[billId]
            bill.updateStatus()
        self.action.updateMatchedStatus()       

    def cancelOrder(self, order:BotOrder, reason=''):
        self.sendTele('notice', 'Cancel', Telegram.TELE_ICON_CANCEL, {
            "Flow": self.action.bot_act_flow,
            "Symbol": order.bot_order_symbol,
            "Side": order.bot_order_side,
            "Price": order.bot_order_matched_price,
            "Qty": order.bot_order_qty,
            "Reason": reason
        })
        self.action.updateOrder(order, {
            'bot_order_status' : OrderStatus.STATUS_CANCELED,
            'bot_order_log' : f"{self.runtime} {reason}"
        })
        self.onChangeOrder(order)
        
        return Reply.make(True, 'success')
    
    def editOrder(self, order:BotOrder, newQty, newPrice, reason = ''):
        self.sendTele('notice', 'Edit order', Telegram.TELE_ICON_CANCEL, {
            "Flow": self.action.bot_act_flow,
            "Symbol": order.bot_order_symbol,
            "Old Price": order.bot_order_price,
            "New Price": newPrice,
            "Reason": reason
        })
        self.action.updateOrder(order, {
            'bot_order_price' : newPrice,
            'bot_order_qty': newQty,
            'bot_order_time': int(self.runtime * 1000),
            'bot_order_log' : f"{self.runtime} {reason}"
        })
        
        return Reply.make(True, 'success')
        
    def calCommit(self, order:BotOrder):
        qty = order.bot_order_matched_qty
        price = order.bot_order_matched_price
        order.bot_order_commission = qty * price * 0.04/100
        return order.bot_order_commission
    
    def summaryAction(self):
        self.log('Summary Action')
        pnl = 0
        matchedQty = 0
        totalBuyVol = 0
        totalSellVol = 0
        profit = 0
        commit = 0
        
        #reset tairling param
        self.advBase = None
        self.profitBase = None
        
        orderIds = list(self.action.orders.keys())
        for orderId in orderIds:
            order:BotOrder = self.action.orders[orderId]
            if(order.bot_order_status in [OrderStatus.STATUS_ERROR]): continue
            if order.bot_order_matched_qty > 0:
                if(order.bot_order_commission is not None): commit += order.bot_order_commission
                if order.bot_order_side == OrderSide.SIDE_BUY:    
                    totalBuyVol += order.bot_order_matched_qty * order.bot_order_matched_price
                    matchedQty += order.bot_order_matched_qty
                else:
                    totalSellVol += order.bot_order_matched_qty * order.bot_order_matched_price
        
        pnl  = totalSellVol - totalBuyVol
        if(totalBuyVol > 0): profit = pnl * 100 / totalBuyVol
        
        realPnl = pnl - commit
        
        self.updateEvent({
            'bot_act_pending': 0,
            'bot_act_pnl': pnl,
            'bot_act_profit': profit,
            'bot_act_real_pnl': realPnl,
            'bot_act_commission': commit,
            'bot_act_exit_time': int(self.runtime * 1000),
        })
        
        if(matchedQty > 0):
            icon = Telegram.TELE_ICON_TAKEPROFIT if realPnl > 0 else Telegram.TELE_ICON_STOPLOSS
            self.sendTele("notice_summary","==== SUMMARY ====", icon, {
                "Flow": self.action.bot_act_flow,
                "Total qty": matchedQty,
                "Total buy": f"{totalBuyVol:,}",
                "Total sell": f"{totalSellVol:,}",
                "Enter Price": f"{self.action.bot_act_matched_price}",
                "Exit Price": f"{self.action.bot_act_exit_price}",
                "PNL(No fee)": f"{pnl}",
                "Fee": f"{commit}",
                "Real PNL": f"{realPnl}"
            })

    

    def summaryTemp(self, forceUpdate = False):
        
        if(self.action is None or self.action.bot_act_pending == 0): return
        if(self.action.bot_act_status_maturity not in [None, ActionMaturityStatus.STATUS_MATURITY_DONE]): return
        symbolData = {}
        totalCommiss = 0
        orderIds = list(self.action.orders.keys())
        for orderId in orderIds:
            order:BotOrder = self.action.orders[orderId]
            if(order.bot_order_status in [OrderStatus.STATUS_ERROR]): continue
            symbol = order.bot_order_symbol
            if(symbol not in symbolData):
                symbolData[symbol] = {
                    'qty' : 0,
                    'matched_price': 0
                }
            if order.bot_order_matched_qty > 0:
                if(order.bot_order_commission is not None): totalCommiss += order.bot_order_commission
                if order.bot_order_side == OrderSide.SIDE_BUY:    
                    if (symbolData[symbol]['qty'] + order.bot_order_matched_qty) != 0:
                        symbolData[symbol]['matched_price'] = (symbolData[symbol]['matched_price'] * symbolData[symbol]['qty'] + order.bot_order_matched_qty * order.bot_order_matched_price)/(symbolData[symbol]['qty'] + order.bot_order_matched_qty)
                    symbolData[symbol]['qty'] += order.bot_order_matched_qty 
                else:
                    if (symbolData[symbol]['qty'] - order.bot_order_matched_qty) != 0:
                        symbolData[symbol]['matched_price'] = (symbolData[symbol]['matched_price'] * symbolData[symbol]['qty'] - order.bot_order_matched_qty * order.bot_order_matched_price)/(symbolData[symbol]['qty'] - order.bot_order_matched_qty)
                    symbolData[symbol]['qty'] -= order.bot_order_matched_qty 
        pnl = 0        
        
        enterPackage = 0
        priceData = self.priceData
        
        for symbol in symbolData:
            currentPrice = priceData.get(symbol, None)
            if(currentPrice is None): return
            currentPrice = currentPrice['last']
            currentPrice = float(currentPrice)
            pnl += (currentPrice - abs(symbolData[symbol]['matched_price'])) * symbolData[symbol]['qty']
            enterPackage += abs(symbolData[symbol]['matched_price'] * symbolData[symbol]['qty'])
        
        if enterPackage != 0:   
            profit = pnl * 100 / enterPackage
        else:
            profit = 0
        
        pnlNoFee = pnl
        realPNL = pnlNoFee - totalCommiss
        if(self.action.bot_act_dayfee is not None): realPNL -= self.action.bot_act_dayfee
        
        self.updateEvent({
            'bot_act_pnl': pnlNoFee,
            'bot_act_profit': profit,
            'bot_act_real_pnl': realPNL,
            'bot_act_commission': totalCommiss,
        }, forceUpdate)
        
         
    # =====================================
    
    # === Block Monitor position Status ===
    def monitorPosition(self):
        # startTime = self.runtime * 1000

        self.monitorOrder()
        
        if(self.action.bot_act_status_close == ActionCloseStatus.STATUS_CLOSE_PENDING):
            self.monitorClosePending()
            
        if(self.action.bot_act_status_close is None):
            
            if(self.action.bot_act_status_enter == ActionEnterStatus.STATUS_ENTER_WAITTING):
                self.monitorEnterWaitting()
            if(self.action.bot_act_status_enter == ActionEnterStatus.STATUS_ENTER_PENDING):
                self.monitorEnterPending()
            if(self.action.bot_act_status_enter == ActionEnterStatus.STATUS_ENTER_PART):
                self.monitorEnterMatchPart()
            
            if(self.action.bot_act_status_matched == ActionMatchedStatus.STATUS_MATCHED and self.action.bot_act_status_exit is None):
                self.monitorMatched()
                
            if(self.action.bot_act_status_exit == ActionExitStatus.STATUS_EXIT_PENDING):
                self.monitorExitPending()
                
            if(self.action.bot_act_status_enter == ActionMatchedStatus.STATUS_MATCHED):
                self.monitorClosePosition()
    
            try:
                if(not hasattr(self, 'lastSummaryTime') or self.runtime - self.lastSummaryTime > 2):# 5 seconds
                    self.lastSummaryTime = self.runtime
                    self.summaryTemp()
            except Exception as e:
                self.log(str(e))

        # print(f"Monitor time = {startTime - self.runtime*1000}ms")
        
    def monitorEnterWaitting(self):
        flowName = self.action.bot_act_flow
        phase = self.action.bot_act_enter_phase
        paseData = self.getEnterPhase(flowName, phase)
        if(paseData is None): raise Exception(f"Can not get phase {phase}")
        
        
        isMakeOrder = True
        isCancel = False
        cancelReason = ''
        enterReason = ''
        
        #Check enter rule
        enterRule = paseData.get('enter_rule')
        if(enterRule is not None):
            checkResult = self.compareOr(enterRule)
            if(not checkResult['result']): raise Exception(checkResult['message'])
            if(checkResult['data'] is not True):
                isMakeOrder = False
            else:
                isMakeOrder = True
                enterReason = checkResult['message']
        
        #Check enter cancle
        enterCancel = paseData.get('enter_cancel')
        if(enterCancel is not None):
            checkResult = self.compareOr(enterCancel)
            if(not checkResult['result']): raise Exception(checkResult['message'])
            if(checkResult['data'] is not True):
                isCancel = False
            else:
                isCancel = True
                cancelReason = checkResult['message']
                
        if(isCancel):
            self.action.bot_act_exit_reason = cancelReason
            if(not self.checkFinish()):
                self.updateEvent({
                    'bot_act_status_enter': ActionEnterStatus.STATUS_ENTER_PART
                })
            else:
                self.sendTele('notice', f'Cancel MAKE ORDER phase {phase}', Telegram.TELE_ICON_CANCEL, {
                    "Flow": flowName,
                    "Reason": cancelReason
                })
        
        if(isMakeOrder and not isCancel):
            bill = self.makeEnterBill(paseData.get("enter_bill"), enterReason)
            self.updateEvent({
                'bot_act_enter_bill': bill.bot_bill_id,
                'bot_act_status_enter': ActionEnterStatus.STATUS_ENTER_PENDING
            })
            self.sendTele('notice', f'Enter order phase {phase}', Telegram.TELE_ICON_LONG, {
                    "Flow": flowName,
                    "Reason": enterReason
                })
            self.monitorEnterPending()
    
    def monitorEnterMatchPart(self):
        phase = self.action.bot_act_enter_phase
        flowName = self.action.bot_act_flow
        currentBillId = self.action.bot_act_enter_bill
        if(currentBillId not in self.action.bills): raise Exception(f"Can not find bill {currentBillId}")
        currentBill:BotBill = self.action.bills[currentBillId]
        
        phases = self.getFlowData(flowName, 'enter')
        if(currentBill.bot_bill_status == BillStatus.STATUS_COMPLETED):
            if(phase >= len(phases) - 1): 
                self.updateEvent({
                    'bot_act_status_enter': ActionEnterStatus.STATUS_ENTER_FULL
                })
                return

            nextPhase = phase + 1
            nextPhaseCfg:dict = phases[nextPhase]
            nextPhaseCondition = nextPhaseCfg.get('condition')
            checkResult = self.compareOr(nextPhaseCondition)
            if(not checkResult['result']): raise Exception(checkResult['message'])
            if(checkResult['data'] is True):
                self.updateEvent({
                    'bot_act_status_enter' : ActionEnterStatus.STATUS_ENTER_WAITTING,
                    'bot_act_enter_phase': nextPhase
                })
                self.sendTele('notice', f'Waitting order phase {nextPhase}', Telegram.TELE_ICON_WAITTING, {
                    "Status": ActionEnterStatus.STATUS_ENTER_WAITTING,
                    "Flow": flowName,
                    "Reason": checkResult['message']
                })
                self.monitorEnterWaitting()
                
    def monitorEnterPending(self):
        
        # "Check if LO price is changed or not. If changed cancel old order"
        billId = self.action.bot_act_enter_bill
        if(billId not in self.action.bills): raise Exception(f"Can not find bill {billId}")
        bill:BotBill = self.action.bills[billId]
        if(bill.bot_bill_status == BillStatus.STATUS_COMPLETED):
            if(not self.checkFinish()):
                self.updateEvent({
                    'bot_act_status_enter': ActionEnterStatus.STATUS_ENTER_PART
                })
        elif(bill.bot_bill_status == BillStatus.STATUS_UNCOMPLETED):
                self.makeEnterBillPosition(bill)
    
    def makeEnterBillPosition(self, bill:BotBill):
        self.makeEnterBillPositionThread = True
        flowName = self.action.bot_act_flow
        phaseCfg = self.getEnterPhase(flowName, bill.bot_bill_phase)
        billCfg = phaseCfg.get('enter_bill')
        for cfg in billCfg:
            self.makeEnterBillOrder(bill, cfg)
        
    def makeEnterBillOrder(self, bill:BotBill, config:dict):
        
        symbol = self.calculateElement(config.get('symbol'))['data']
        if(symbol is None): raise Exception("No symbol")
        
        orderType = config.get('order_type', None)
        if(orderType is None): raise Exception('No Order Type')

        price = self.calculateElement(config.get('price', 0))
        if(not price['result']): raise Exception(price['message'])
        price = price['data']
        if(price is None):
            self.sendTele('warning','Can not make L0 order because Price=None')
            return Reply.make(False, 'Can not make order')

        if(price == 0 and orderType == OrderType.TYPE_LO): 
            self.sendTele('warning','Can not make L0 order because Price=0')
            return Reply.make(False, 'Can not make order')

        #calculate number and side 
        
        orderMatched = 0
        orderSide = None

        symbolData = bill.getPosition()
        symbolData = symbolData.get(symbol, {})

        orderMatched = symbolData.get('matched', 0)
        enterWaiting = symbolData.get('waiting', 0)
        
        if(enterWaiting != 0): return Reply.make(False, 'Bill are watting')

        cfgQty = self.calculateElement(config.get('quantity', None))
        if(not cfgQty['result']): return cfgQty
        cfgQty = float(cfgQty['data'])
        if(cfgQty is None): return

        cfgSide = config.get('order_side', None)
        if(cfgSide is None): return
        if(cfgSide == OrderSide.SIDE_BUY):
            orderQty = cfgQty - (orderMatched + enterWaiting)
        if(cfgSide == OrderSide.SIDE_SELL):
            orderQty = -cfgQty - (orderMatched + enterWaiting)
        
        if(orderQty > 0):
            orderSide = OrderSide.SIDE_BUY
        if(orderQty < 0):
            orderQty = -orderQty
            orderSide = OrderSide.SIDE_SELL

        if(orderSide is None): 
            return

        block = config.get('block', orderQty)
        interval = config.get('interval', False)
        
        bill.sending = True
        sent = 0
        delay = 0
    
        while sent < orderQty:
            currentOrderQty = min(block, orderQty-sent)
            try:
    
                newOrder = BotOrder()
                newOrder.bot_order_action = self.action.bot_act_id
                newOrder.bot_order_bill = bill.bot_bill_id
                newOrder.bot_order_qty = currentOrderQty
                newOrder.bot_order_act_type = bill.bot_bill_act_type
                newOrder.bot_order_symbol = symbol
                newOrder.bot_order_type = orderType
                newOrder.bot_order_price = price
                newOrder.bot_order_matched_qty = 0
                newOrder.bot_order_unmatched_qty = currentOrderQty
                newOrder.bot_order_side = orderSide
                newOrder.bot_order_status = OrderStatus.STATUS_SENDING
                newOrder.bot_order_time = int(self.runtime*1000) + delay
                newOrder.bot_order_phase = bill.bot_bill_phase
                newOrder.bot_order_exchange = config.get('exchange', 'ps')
                
                self.action.addOrder(newOrder, bill.bot_bill_id)
                
            finally:
                sent += currentOrderQty
                if(interval is False): break
                delay += interval * 1000
        
        bill.sending = False    
        bill.updateStatus()
            
        return Reply.make(True, "Success")

    def monitorMatched(self):
            
            #Check stoploss and takeprofit
            isClose = False
            reason = ''
            enterPhase = self.action.bot_act_enter_phase
            flowName = self.action.bot_act_flow
            enterPhaseCfg = self.getEnterPhase(flowName, enterPhase)
            session = getSession()
            if(session == 'LO' or session == 'TIMEOUT'):    
                if(not isClose):        
                    #check stoploss
                    
                    stoploss = enterPhaseCfg.get('stoploss', self.getFlowData(flowName, 'stoploss'))
                    if(stoploss is not None and stoploss is not False and self.action.bot_act_profit is not None):
                        if(self.action.bot_act_profit <= -float(stoploss)):
                            isClose = True
                            reason = f'Stoploss {stoploss}%'
                            
                if(not isClose):   
                    #check takeprofit
                    takeprofit = enterPhaseCfg.get('takeprofit', self.getFlowData(flowName, 'takeprofit'))
                    if(takeprofit is not None and takeprofit is not False and self.action.bot_act_profit is not None):
                        if(self.action.bot_act_profit >= float(takeprofit)):
                            isClose = True
                            reason = f'Takeprofit {takeprofit}%'
                        
                if(not isClose):           
                    #check tailing avantage
                    advantageCfg:dict = enterPhaseCfg.get('advantage')
                    if(advantageCfg is not None):
                        checkResult = True
                        if(self.advBase is None):
                            advCondition = advantageCfg.get('condition', None)
                            if(advCondition is not None):
                                checkCondition = self.compareOr(advCondition)
                                if(not checkCondition['result']): raise Exception(checkCondition['message'])
                                if(checkCondition['data'] is None or not checkCondition['data']): checkResult = False
                            
                        if(checkResult):
                            advObject = self.calculateElement(advantageCfg.get('object', None))['data']
                            advBase = self.calculateElement(advantageCfg.get('base', None))['data']
                            step = self.calculateElement(advantageCfg.get('step', None))['data']
                            back = self.calculateElement(advantageCfg.get('back', None))['data']
                            if(None not in [advObject, advBase, step, back]):
                                if(self.action.bot_act_matched_price is not None and self.action.bot_act_matched_price > 0 and self.action.bot_act_matched_qty != 0):
                                    if(self.action.bot_act_matched_qty > 0):
                                        currentAdv = advObject - self.action.bot_act_matched_price
                                    else:
                                        currentAdv = self.action.bot_act_matched_price - advObject
                                        
                                    if(currentAdv > advBase):
                                        newAdvBase = advBase + (currentAdv-advBase)//step * step
                                        if(self.advBase is None):
                                            self.advBase = newAdvBase
                                            self.sendTele('notice', f"Get base advantage", Telegram.TELE_ICON_TAKEPROFIT, {
                                                "Base Advantage": self.advBase,
                                                "Current Advantage": currentAdv
                                            })
                                        else:
                                            if(newAdvBase > self.advBase): 
                                                self.advBase = newAdvBase
                                                self.sendTele('notice', f"Get next base advantage", Telegram.TELE_ICON_TAKEPROFIT, {
                                                    "Base Advantage": self.advBase,
                                                    "Current Advantage": currentAdv
                                                })
                                        
                                    if(self.advBase is not None):
                                        if(self.advBase - currentAdv > back):
                                            reason = f"Base Advantage({self.advBase}) - Current Advantage({currentAdv}) > Back step({back})"
                                            isClose = True
                
                if(not isClose):           
                    #check tailing profit
                    profitCfg:dict = enterPhaseCfg.get('profit')
                    if(profitCfg is not None):
                        
                        checkResult = True
                        if(self.profitBase is None):
                            profitCondition = profitCfg.get('condition', None)
                            if(profitCondition is not None):
                                checkCondition = self.compareOr(profitCondition)
                                if(not checkCondition['result']): raise Exception(checkCondition['message'])
                                if(checkCondition['data'] is None or not checkCondition['data']): checkResult = False
                            
                        if(checkResult):
                            profitBase = self.calculateElement(profitCfg.get('base', None))['data']
                            step = self.calculateElement(profitCfg.get('step', None))['data']
                            back = self.calculateElement(profitCfg.get('back', None))['data']
                            if(None not in [profitBase, step, back]):
                                if(self.action.bot_act_profit is not None):
                                    currentProfit = self.action.bot_act_profit
                                    if(currentProfit > profitBase):
                                        newProfitBase = profitBase + (currentProfit-profitBase)//step * step
                                        if(self.profitBase is None):
                                            self.profitBase = newProfitBase
                                            self.sendTele('notice', f"Get base profit", Telegram.TELE_ICON_TAKEPROFIT, {
                                                "Base Profit": self.profitBase,
                                                "Current Profit": currentProfit
                                            })
                                        else:
                                            if(newProfitBase > self.profitBase):
                                                self.profitBase = newProfitBase
                                                self.sendTele('notice', f"Get next base profit", Telegram.TELE_ICON_TAKEPROFIT, {
                                                    "Base Profit": self.profitBase,
                                                    "Current Profit": currentProfit
                                                })
                                        
                                    if(self.profitBase is not None):
                                    
                                        if(self.profitBase - currentProfit > back):
                                            reason = f"Base Profit({self.profitBase}) - Current Profit({currentProfit}) > Back step({back})"
                                            isClose = True
                
                if(not isClose):
                    exitCondition = enterPhaseCfg.get('exit_condition')
                    if(exitCondition is not None):
                        checkResult = self.compareOr(exitCondition)
                        if(not checkResult['result']): raise Exception(checkResult['message'])
                        if(checkResult['data'] is True):
                            reason = checkResult['message']
                            isClose = True
                
                
                if(isClose):
                    self.sendTele('notice', f'Exit order phase {enterPhase}', Telegram.TELE_ICON_SHORT, {
                        "Flow": flowName,
                        "Reason": reason
                    })
                    bill = self.makeExitBill(reason)
                    self.updateEvent({
                        'bot_act_exit_data':json.dumps(self.checkData, default=str),
                        'bot_act_status_exit': ActionExitStatus.STATUS_EXIT_PENDING,
                        'bot_act_exit_bill' : bill.bot_bill_id,
                        'bot_act_exit_reason': reason
                    })
                    
                                
    def monitorExitPending(self):
        # print("monitorExitPending")
        # "Check if LO price is changed or not. If changed cancel old order"
        billId = self.action.bot_act_exit_bill
        if(billId not in self.action.bills): raise Exception(f"Can not find bill {billId}")
        bill:BotBill = self.action.bills[billId]
        if(bill.bot_bill_status == BillStatus.STATUS_COMPLETED):
            if(not self.checkFinish()):
                self.updateEvent({
                    'bot_act_status_exit': None
                })
        elif(bill.bot_bill_status == BillStatus.STATUS_UNCOMPLETED):
                self.makeExitBillPosition(bill)
    
    def makeExitBillPosition(self, bill:BotBill):
        self.makeExitBillPositionThread = True
        flowName = self.action.bot_act_flow
        phaseCfg = self.getEnterPhase(flowName, bill.bot_bill_phase)
        billCfg = phaseCfg.get('exit_bill')
        for cfg in billCfg:
            self.makeExitBillOrder(bill, cfg)
            
        
    def makeExitBillOrder(self, bill:BotBill, config:dict):
        
        symbol = self.calculateElement(config.get('symbol'))['data']
        if(symbol is None): raise Exception("No symbol")
        
        orderType = config.get('order_type', None)
        if(orderType is None): raise Exception('No Order Type')

        price = self.calculateElement(config.get('price', 0))
        if(not price['result']): return price
        price = price['data']

        if(price is None):
            self.sendTele('warning','Can not make L0 order because Price=None')
            return Reply.make(False, 'Can not make order')

        if(price == 0 and orderType == OrderType.TYPE_LO): 
            self.sendTele('warning','Can not make L0 order because Price=0')
            return Reply.make(False, 'Can not make order')
        

        orderMatched = 0
        orderSide = None

        symbolData = self.action.getPositionSymbol()
        symbolData = symbolData.get(symbol, {})

        orderMatched = symbolData.get('matched', 0)
        closeWaiting = symbolData.get('waiting', 0)
        orderSide = config.get('order_side', None)
                
        orderQty = orderMatched
        
        if(orderQty > 0):
            orderSide = OrderSide.SIDE_SELL
        if(orderQty < 0):
            orderQty = -orderQty
            orderSide = OrderSide.SIDE_BUY

        if(orderSide is None): 
            return Reply.make(False, f'Can not make order quantity: {orderQty}')
        
        cfgQty = config.get('quantity', None)
        cfgQty = self.calculateElement(cfgQty)['data']
        if(cfgQty is None): cfgQty = orderQty
        
        orderQty = min(orderQty, cfgQty)
        
        block = config.get('block', orderQty)
        interval = config.get('interval', False)
        
        bill.sending = True    
        sent = 0
        delay = 0
        while sent < orderQty:
            currentOrderQty = min(block, orderQty-sent)
            try:
    
                closeOrder = BotOrder()
                closeOrder.bot_order_action = self.action.bot_act_id
                closeOrder.bot_order_bill = bill.bot_bill_id
                closeOrder.bot_order_qty = currentOrderQty
                closeOrder.bot_order_act_type = bill.bot_bill_act_type
                closeOrder.bot_order_symbol = symbol
                closeOrder.bot_order_type = orderType
                closeOrder.bot_order_price = price
                closeOrder.bot_order_matched_qty = 0
                closeOrder.bot_order_unmatched_qty = currentOrderQty
                closeOrder.bot_order_side = orderSide
                closeOrder.bot_order_phase = bill.bot_bill_phase
                closeOrder.bot_order_status = OrderStatus.STATUS_SENDING
                closeOrder.bot_order_time = int(self.runtime*1000) + delay
                closeOrder.bot_order_exchange = config.get('exchange', 'ps')
                
                
                self.action.addOrder(closeOrder, bill.bot_bill_id)

               
                
            finally:
                
                sent += currentOrderQty
                if(interval is False): break
                delay += interval * 1000
        
        bill.sending = False    
        bill.updateStatus()
               
        return Reply.make(True, "Success")

    def monitorClosePosition(self):

        flowName = self.action.bot_act_flow
        closeCfg:dict = self.getFlowData(flowName, 'close')
        
        if(self.action.bot_act_status_close == ActionCloseStatus.STATUS_CLOSE_PENDING): return
        if(self.action.bot_act_status_close == ActionCloseStatus.STATUS_CLOSE_FORCE):
            closeResult = Reply.make(True, 'Force to Close', True)
        else:
            closeCondition = closeCfg('condition')
            if(closeCondition is None):
                return
            closeResult = self.compareOr(closeCondition)
            
        if(not closeResult['result']): raise Exception(closeResult['message'])

        if(closeResult['data'] is not None and closeResult['data']):

            closeBill = closeCfg.get('close_bill')
            if(closeBill is None or len(closeBill) == 0): 
                raise Exception('No close actions')

            #Cancel all order
            orderIds = list(self.action.orders.keys())
            for orderId in orderIds:
                order:BotOrder = self.action.orders[orderId]
                if(order.bot_order_status in [OrderStatus.STATUS_ERROR]): continue
                if(order.bot_order_status not in [OrderStatus.STATUS_CANCELED , OrderStatus.STATUS_MATCHED_FULL]):
                    self.cancelOrder(order, closeResult['message'])

            self.sendTele('notice', f'Close matched order', Telegram.TELE_ICON_CANCEL, {
                "Flow": self.action.bot_act_flow,
                "Reason": closeResult['message']
            })

            bill = self.makeCloseBill(closeResult['message'])
            self.updateEvent({
                'bot_act_exit_data': json.dumps(self.checkData, default=str),
                'bot_act_exit_reason': closeResult['message'],
                'bot_act_status_close' : ActionCloseStatus.STATUS_CLOSE_PENDING,
                'bot_act_close_bill': bill.bot_bill_id
            })
            self.monitorClosePending()
            
    def monitorClosePending(self):
        # print("monitorClosePending")
        # "Check if LO price is changed or not. If changed cancel old order"
        billId = self.action.bot_act_close_bill
        if(billId not in self.action.bills): raise Exception(f"Can not find bill {billId}")
        bill:BotBill = self.action.bills[billId]
        if(bill.bot_bill_status == BillStatus.STATUS_COMPLETED):
            if(not self.checkFinish()):
                self.updateEvent({
                    'bot_act_status_close': None
                })
        elif(bill.bot_bill_status == BillStatus.STATUS_UNCOMPLETED):
                self.makeCloseBillPosition(bill)
    
    def makeCloseBillPosition(self, bill:BotBill):
        self.makeCloseBillPositionThread = True
        flowName = self.action.bot_act_flow
        closeCfg:dict = self.getFlowData(flowName, 'close')
        billCfg = closeCfg.get('close_bill')
        for cfg in billCfg:
            self.makeCloseBillOrder(bill, cfg)
            
        
    def makeCloseBillOrder(self, bill:BotBill, config:dict):
        
        symbol = self.calculateElement(config.get('symbol'))['data']
        if(symbol is None): raise Exception("No symbol")
        
        orderType = config.get('order_type', None)
        if(orderType is None): raise Exception('No Order Type')

        price = self.calculateElement(config.get('price', 0))
        if(not price['result']): return price
        price = price['data']

        if(price is None):
            self.sendTele('warning','Can not make L0 order because Price=None')
            return Reply.make(False, 'Can not make order')

        if(price == 0 and orderType == OrderType.TYPE_LO): 
            self.sendTele('warning','Can not make L0 order because Price=0')
            return Reply.make(False, 'Can not make order')

        orderMatched = 0
        orderSide = None

        symbolData = self.action.getPositionSymbol()
        symbolData = symbolData.get(symbol, {})

        orderMatched = symbolData.get('matched', 0)
        closeWaiting = symbolData.get('waiting', 0)
        orderSide = config.get('order_side', None)
                
        orderQty = orderMatched
        
        if(orderQty > 0):
            orderSide = OrderSide.SIDE_SELL
        if(orderQty < 0):
            orderQty = -orderQty
            orderSide = OrderSide.SIDE_BUY

        if(orderSide is None): 
            return Reply.make(False, f'Can not make order quantity: {orderQty}')
        
        cfgQty = config.get('quantity', None)
        cfgQty = self.calculateElement(cfgQty)['data']
        
        if(cfgQty is None): cfgQty = orderQty
        orderQty = min(orderQty, cfgQty)
        block = config.get('block', orderQty)
        interval = config.get('interval', False)
        
        bill.sending = True
        sent = 0
        delay = 0
        while sent < orderQty:
            currentOrderQty = min(block, orderQty-sent)
            try:
    
                closeOrder = BotOrder()
                closeOrder.bot_order_action = self.action.bot_act_id
                closeOrder.bot_order_bill = bill.bot_bill_id
                closeOrder.bot_order_qty = currentOrderQty
                closeOrder.bot_order_act_type = bill.bot_bill_act_type
                closeOrder.bot_order_symbol = symbol
                closeOrder.bot_order_type = orderType
                closeOrder.bot_order_price = price
                closeOrder.bot_order_matched_qty = 0
                closeOrder.bot_order_unmatched_qty = currentOrderQty
                closeOrder.bot_order_side = orderSide
                closeOrder.bot_order_phase = bill.bot_bill_phase
                closeOrder.bot_order_status = OrderStatus.STATUS_SENDING
                closeOrder.bot_order_time = int(self.runtime*1000) + delay
                closeOrder.bot_order_exchange = config.get('exchange', 'ps')
                
                
                self.action.addOrder(closeOrder, bill.bot_bill_id)
            finally:
                sent += currentOrderQty
                if(interval is False): break
                delay += interval * 1000
        
        bill.sending = False    
        bill.updateStatus()
                
        return Reply.make(True, "Success")
    
    def checkFinish(self):
        if(self.action is None or self.action.bot_act_pending == 0): return
        symbolData = self.action.getPositionSymbol()
        isFinished = True
        currentPosition = {}
        for symbol in symbolData:
            symDt = symbolData[symbol]
            currentPosition[symbol] = symDt['matched']
            if(symDt['matched'] != 0 or symDt['waiting'] != 0):
                isFinished = False
        #Update current position    
        self.updateEvent({
            'bot_act_position': json.dumps(currentPosition, default=str)
        })
        
        if(isFinished):
            if(self.action.bot_act_pending == 1):
                self.summaryAction()
                
        return isFinished
    
    # def updateDayFee(self):
    #     if(self.action is None or self.action.bot_act_pending == 0): return
    #     lastUpdateDay = self.action.bot_act_dayfee_time
    #     if(lastUpdateDay is None): return
    #     lastUpdateDay = lastUpdateDay//86400
    #     currentDay = self.runtime//86400
    #     if(lastUpdateDay == currentDay): return
    #     currentDayFee = self.action.bot_act_dayfee
    #     if(currentDayFee is None): currentDayFee = 0
    #     currentPosition = self.action.getPositionSymbol()
    #     for sym in currentPosition:
    #         if(currentPosition[sym].get('exchange', 'ps') == 'cs'): continue
    #         currentDayFee += abs(currentPosition[sym].get('matched', 0)) * 2550
    #     self.updateEvent({
    #         'bot_act_dayfee': currentDayFee,
    #         'bot_act_dayfee_time': int(self.runtime)
    #     })
    
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
        dateTime = datetime.fromtimestamp(floor(self.runtime), VN_TZ)
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
            if(self.action.bot_act_pending == 0):
                self.periodAction = self.action        
        return Reply.make(True, 'success', self.action)

    def getActions(self):
        actions = {}
        for act in self.actions:
            actions[act] = self.actions[act].toDict()
        return actions
     
    