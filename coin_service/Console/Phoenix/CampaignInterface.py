
# import threading
from Console.Helper.Defaults import *
from Console.Helper.Control import *
from Console.Helper.Reply import Reply
from Console.Phoenix.AccountInterface import AccountInterface



# class EventCheckThread(threading.Thread):
#     def __init__(self, event) -> None:
#         threading.Thread.__init__(self)
#         self.event = event  # type: EventCheckInterface

#     def run(self):
#         self.event.run()


class CampaignInterface():

    campaign = None 
    runtime = None
    checkData = None
    checkResult = None
    event = None 
    frame1m = None #type: dict
    cfgStrategy = None  #type: dict
    account = None 
    needData = None  #type: dict
    priority = None #type: dict
    accountImp = None #type: AccountInterface

    # MUTEX = threading.Lock()
    
    
    def __init__(self, accountImp) -> None:
        self.accountImp = accountImp
        self.runtime = None
        self.checkData = None
        self.checkResult = None
        self.event = None
        self.frame1m = None

    def initial(self):
        raise Exception('no implementation')

    # def start(self):
    #     thr = EventCheckThread(self)
    #     thr.start()
    #     return thr

    def run(self):
        raise Exception('no implementation')

    def calculateElement(self, struct, dynamicIndex=None):
        return Reply.make(False, "Please implement calculateElement function")

    # make comparision with struct: OR(AND(FORMULAR, OR...), AND, ....)

    def compare(self, element, dynamicIndex=None):
        firstNumber = self.calculateElement(element[0], dynamicIndex)
        formula = element[1]
        secondsNumber = self.calculateElement(element[2], dynamicIndex)
        if(not firstNumber['result']):
            return firstNumber
        if(not secondsNumber['result']):
            return secondsNumber

        log = f"{firstNumber['message']}({firstNumber['data']}) {formula} {secondsNumber['message']}({secondsNumber['data']})"

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

    def compareAnd(self, conditions, dynamicIndex=None):
        logs = []
        for condition in conditions:
            if(type(condition) is list):
                if(len(condition) == 3 and condition[1] in ['<', '>', '=', '>=', '<=', '!=']):
                    result = self.compare(condition, dynamicIndex)
                    if(not result['result']):
                        return result
                else:
                    result = self.compareOr(condition, dynamicIndex)
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

    def compareOr(self, conditions, dynamicIndex=None):
        logs = []
        for condition in conditions:
            result = self.compareAnd(condition, dynamicIndex)
            if(not result['result']):
                return result
            logs.append(result['message'])
            if(result['data'] is None):
                return Reply.make(True, ' OR '.join(logs), None)
            if(result['data'] is True):
                return Reply.make(True, ' OR '.join(logs), True)
        return Reply.make(True, ' OR '.join(logs), False)

    # End comparision function block

    # return attribute of flow by flow's name
    def getFlowData(self, flowName, key):
        default = {
            'timelife': 6,
            'interval': 0,
            'takeprofit': False,
            'stoploss': False,
            'step_profit': 0.1,
            'back_profit': 0.1,
            'baseprofit': 0.8,
            'baseprofit_baseon': 'close',
            'margin': 1,
            'allow_negative_price_rate': True,
            'after_stoploss': True,
            'using_match_price': True,
        }
        flowData = self.cfgStrategy[flowName]
        if(isset(flowData, key) and not flowData[key] is None):
            return flowData[key]
        if(isset(default, key)):
            return default[key]
        return None

    #return the next phase
    def getNextPhase(self, condition, currentPhase):
        currentPhase = int(currentPhase)
        if (not isset(condition, 'next_phase')): return Reply.make(True, 'next phase is not configured', currentPhase + 1)
        nextPhase = self.calculateElement(condition['next_phase'])
        return nextPhase

    #return make order condition of phase
    def getMatchCondition(self, flow, phase):
        phase = int(phase)
        straType = self.cfgStrategy[flow]
        if (isset(straType, 'disable') and straType['disable']): return None
        if (not isset(straType, 'match')): return None
        if (not isset(straType['match'], phase)): return None
        return straType['match'][phase]
    
    #return leng of match condition
    def getMatchLeng(self, flow):
        return len(self.cfgStrategy[flow]['match'])
    
    def getStopCondition(self, flow, index):
        index = int(index)
        straType = self.cfgStrategy[flow]
        if (not isset(straType, 'stop')): return None
        if (not isset(straType['stop'], index)): return None
        return straType['stop'][index]
    
    def getStopConditions(self, flow):
        straType = self.cfgStrategy[flow]
        if (not isset(straType, 'stop')): return None
        return straType['stop']

    def getFreePosition(self, flowName):
        maxTrades = self.getFlowData(flowName, 'max_open_trades')
        if (maxTrades is None or maxTrades == ''): return None
        taken = self.countPosition()
        freeSlot = int(maxTrades) - taken
        return freeSlot

    def getFreeSlot(self, flowName):
        maxTrades = self.getFlowData(flowName, 'strategy_slot')
        # print(f"maxTrades: {maxTrades}")
        if (maxTrades is None or maxTrades == ''): return None
        taken = self.countSlot(flowName)
        freeSlot = int(maxTrades) - taken
        return freeSlot
    
    #Number of postion opened
    def countPosition(self):
        return self.accountImp.countPosition()

    #Number of slot of strategy is taken
    def countSlot(self, flowName):
        strategyId = self.getFlowData(flowName, 'strategy')
        return self.accountImp.countSlot(strategyId)
    