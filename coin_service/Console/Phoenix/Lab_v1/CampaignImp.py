from datetime import datetime
import json
from math import ceil, floor

import pytz
from Console.Helper.Defaults import *
from Console.Helper.Control import *
from Console.Helper.Reply import Reply
from Console.Models.Coin_lab import LabCampaigns, LabOrder, LabResults, LabAccount
from Console.Models.Wrappers.Lab.Coin_lab import LabAccountWrapper, LabEventLogsWrapper, LabOrderWrapper, LabResultsWrapper 
from Console.Models.Wrappers.Lab.Lab_candle import LabCandle1MWrapper 
from Console.Phoenix.CampaignInterface import CampaignInterface
from .function import *
from ..Helper.function_v1 import *
from pymongo import ASCENDING, DESCENDING

class CampaignImp(CampaignInterface):

    event = None #type: LabResults
    periodEvent = None #type: LabResults
    orders = []
    account = None #type: LabAccount
    rawRun = False

    #Optimization results
    totalPosition = 0
    totalInterval = 0
    maxInterval = 0

    #choice results
    choiceData = {}

    #commission
    takerCommit = 0.04
    makerCommit = 0.02


    def __init__(self, campaign, accountImp) -> None:
        super().__init__(accountImp)
        self.campaign = campaign #type: LabCampaigns
    
    def initial(self, optiParams, strategyId = None, rawRun=False):
        self.rawRun = rawRun
        self.symbol = self.campaign.lab_campaign_symbol
        params = self.campaign.lab_campaign_params
        if(params is None or params == ''): 
            self.params = []
        else:
            self.params = json.loads(params)

        self.account = self.accountImp.account
        if(strategyId is None):
            strategyId = self.campaign.lab_campaign_strategy
        
        self.cfgStrategy = processLabStrategy(strategyId, optiParams)
        # print(self.cfgStrategy)

        self.labPendingTime = 0 # save the time when event finish. 
        self.labPendingStop = 0 # the time pending to the next action

        self.maxOrderProfit = 0 # save the max profit of action
        self.event = None # save the last event of this campaign

        self.needData = {} # save the data need to load
        scanNeedData(self.cfgStrategy, self.symbol, self.needData)
        # print("self.needData")
        # print(self.needData)

        self.dependSymbols = {}
        scanDependSymbol(self.cfgStrategy, self.symbol, self.dependSymbols)

        self.enterBase = None #using for enter step
        self.releaseBase = None #using for release step

        self.matchedParamsPhase = None #save the phase of current localdata

        # order type
        self.side = self.campaign.lab_campaign_side if hasattr(self.campaign, 'lab_campaign_side') else 'BOTH'

        self.isTelegram = False
        self.priority = getPriorityIndex(self.account.lab_account_id)

        self.leapCheckResult = {}
        self.leapLeng = {
            "3m": 3*60*1000,
            "15m": 15*60*1000,
            "1h": 60*60*1000,
            "4h": 4*60*60*1000,
            "1d": 24*60*60*1000,
            "1w": 7*24*60*60*1000,
        }

        self.resetChoiceData()
            

    def setRun(self, checkData, runtime):
        self.checkData = checkData
        self.runtime = runtime
        self.checkResult = None
        # self.frame1m = None if len(self.checkData[self.symbol]['kline']['1m']) == 0 else self.checkData[self.symbol]['kline']['1m'][0]

    def run(self):
        '''
        is call in other thread when call evencheck.start()
        '''
        #Check Có lệnh hay chưa
        isPending = self.checkEvent()
        # print(f"{self.symbol} isPending: {isPending}")
        if(isPending):
            # check event if it exists/Kiểm tra dữ liệu
            if(not self.validateMonitorData()):
                self.checkResult = Reply.make(True, 'Not enough data', False)
                return
            else:
                self.lostPackage = 0
            

            checkResult = self.monitorEvent()
            
            if(not checkResult['result']):
                self.checkResult = checkResult
                print("checkResult")
                print(checkResult)
                return
            if(checkResult['data']['pending']):
                self.checkResult = Reply.make(True, 'Mornitor Event', self.event.lab_result_matched_qty > 0)
            else:
                isPending = False

        if(not isPending):
            #check event if it exist/Kiểm tra dữ liệu
            if(not self.validateOrderData()):
                self.checkResult = Reply.make(True, 'Not enough data', False)
                return
            else:
                self.lostPackage = 0
            
            
            #Check ĐK đợi lệnh
            checkResult = self.checkOrder()
            if(not checkResult['result']):
                self.checkResult = checkResult
            else:
                # print("Check Order")
                self.checkResult = Reply.make(True, 'Check Order', False)
            

    def validateMonitorData(self):
        '''
        Check if enough data for mornitor
        '''
        try:
            self.frame1m = self.checkData[self.symbol]['kline']['1m'][-1]
            return True
        except Exception as e:
            self.log(f"Does not enouth data for mornitor order: {e}")
            return False
    
    def validateOrderData(self):
        '''
        Check if enough data for make order
        '''
        
        for symbol in self.needData:
            if(not isset(self.checkData, symbol)): 
                self.log("Does not enough data for make order:" + str(symbol))
                return False

            #Check kline
            if('kline' in self.needData[symbol]):
                for frame in self.needData[symbol]['kline']:
                    if(not isset(self.checkData[symbol], 'kline')): 
                        self.log("Does not existed kline data for make order:" + str(symbol) + " " + str(frame))
                        return False
                    if(not isset(self.checkData[symbol]['kline'], frame)): 
                        self.log(f"Does not enough kline data frame {frame} for make order:" + str(symbol) + " " + str(frame))
                        return False
                    if( -self.needData[symbol]['kline'][frame] >= len(self.checkData[symbol]['kline'][frame])): 
                        self.log("Does not enough data for make order:" + str(symbol) + " " + str(frame) + " " + str(self.needData[symbol]['kline'][frame]))
                        return False
                    if(Number(self.checkData[symbol]['kline'][frame][-1]['close_time']) < self.runtime): 
                        self.log("Data kline too old for make order:" + str(symbol) + " " + str(frame) + " " + str(self.runtime))
                        return False

            #Check busd
            if('busd' in self.needData[symbol]):
                if(not isset(self.checkData[symbol], 'busd')): 
                    self.log("Does not existed busd data for make order:" + str(symbol))
                    return False
                if len(self.checkData[symbol]['busd']) == 0:
                    return False
                if( -self.needData[symbol]['busd'] >= len(self.checkData[symbol]['busd'])): 
                    self.log("Does not enough data for make order:" + str(symbol) + " " + str(self.needData[symbol]['busd']))
                    return False
                
                if 'timestamp' not in self.checkData[symbol]['busd'][-1]:
                    self.log("Data busd miss timestamp column:" + str(symbol))
                    return False
                lastTime = Number(self.checkData[symbol]['busd'][-1]['timestamp']) * 1000
                if(lastTime < self.runtime - 60000): 
                    self.log("Data busd too old for make order:" + str(symbol) + " " + str(lastTime) + " " + str(self.runtime))
                    return False
        
        #create frame 1m if enough data
        self.frame1m = self.checkData[self.symbol]['kline']['1m'][-1]
        return True
    
    #Fucntion check condition to make order
    def checkOrder(self):
        orderType = 0
        flow = None
        strategy = None
        container = None
        flowName = None
        logResults = {}
        makeOrderReason = None
        condition = None

        for flowN in self.cfgStrategy:
            flowData = self.cfgStrategy[flowN]
            if(not isset(flowData, 'type')): continue

            #check blacklist
            if(not self.checkBlacklist(flowN)): continue

            if(self.account.lab_account_sync == 1):
                #check if free position 
                freePosition = self.getFreePosition(flowN)
                if((not freePosition is None) and freePosition <= 0 ): continue

                #check if free slot
                freeSlot = self.getFreeSlot(flowN)
                if((not freeSlot is None) and freeSlot <= 0 ): continue

            #check interval
            interval = Number(self.getFlowData(flowN, 'interval'))
            if(self.runtime - self.labPendingTime < (interval * 60000)): continue

            #check after stoploss
            if(self.periodEvent is not None and self.periodEvent.lab_result_status == LabResultsWrapper.LAB_RESULT_STATUS_STOPLOSS):
                afterStoploss = self.getFlowData(flowN, 'after_stoploss')
                if(afterStoploss is not None):
                    if(afterStoploss is False): continue
                    if(type(afterStoploss) is not bool):
                        afterStoploss = Number(afterStoploss)
                        if(self.runtime - self.periodEvent.lab_result_sell_time < afterStoploss * 60000): continue

            flowType = flowData['type']
            if(self.side != 'BOTH' and flowType != self.side): continue
            condition = self.getMatchCondition(flowN, 0)
            # print(condition)
            if(not condition is None):
                logResult = self.compareOr(condition['condition'])                
                # print(logResult)
                logResults[flowN] = logResult
                if(not logResult['result']): return logResult
                
                # if(flowN == '508--4H-L50'): self.log(logResult)
                if(logResult['data']):
                    orderType = LabResultsWrapper.LAB_RESULT_TYPE_LONG if flowType == 'LONG' else LabResultsWrapper.LAB_RESULT_TYPE_SHORT
                    flow = flowData['name']
                    strategy = flowData['strategy']
                    container = get(flowData, 'container', None)
                    flowName = flowN
                    makeOrderReason = logResult['message']
                    break

        if(orderType != 0):

            if(not self.rawRun):
                if(isset(self.params, LabCampaignsWrapper.LAB_CAMPAIGN_PARAMS_LOG) and self.params[LabCampaignsWrapper.LAB_CAMPAIGN_PARAMS_LOG] == 1):
                    LabEventLogsWrapper().create({
                        LabEventLogsWrapper.lab_elog_time: self.runtime,
                        LabEventLogsWrapper.lab_elog_campaign: self.campaign.lab_campaign_id,
                        LabEventLogsWrapper.lab_elog_symbol: self.symbol,
                        LabEventLogsWrapper.lab_elog_matched: orderType,
                        LabEventLogsWrapper.lab_elog_chart : self.frame1m['open_time'],
                        LabEventLogsWrapper.lab_elog_result : json.dumps(logResults),
                        LabEventLogsWrapper.lab_elog_base : json.dumps(self.checkData)
                    })
            return self.wattingOrder(orderType, container, strategy, flow, flowName, makeOrderReason)

        return Reply.make(True, 'Not matched')

    def wattingOrder(self, orderType, container, strategy, flow, flowName, reason = ''):
        condition = self.getMatchCondition(flowName, 0)
        #reset all local data
        self.maker = None
        self.maxOrderProfit = 0
        self.baseProfit = Number(get(condition, 'baseprofit', self.getFlowData(flowName, 'baseprofit')))
        self.matchedParamsPhase = None
        
        closePrice = Number(self.frame1m['close'])
        self.enterBase = closePrice


        addData = {
            LabResultsWrapper.lab_result_enter_time : self.runtime,
            LabResultsWrapper.lab_result_enter_price : closePrice,
            LabResultsWrapper.lab_result_chart : self.runtime,
            LabResultsWrapper.lab_result_chart_price : closePrice,
            LabResultsWrapper.lab_result_campaign: self.campaign.lab_campaign_id,
            LabResultsWrapper.lab_result_symbol: self.symbol,
            LabResultsWrapper.lab_result_type: orderType,
            LabResultsWrapper.lab_result_low: Number(self.frame1m['low']),
            LabResultsWrapper.lab_result_high: Number(self.frame1m['high']),
            LabResultsWrapper.lab_result_pending: 1,
            LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_ENTER_WAITTING,
            LabResultsWrapper.lab_result_phase: 0,
            LabResultsWrapper.lab_result_order_phase: 0,
            LabResultsWrapper.lab_result_strategy: strategy,
            LabResultsWrapper.lab_result_start_reason: reason,
            LabResultsWrapper.lab_result_flow: flow,
            LabResultsWrapper.lab_result_account: self.account.lab_account_id,
            LabResultsWrapper.lab_result_container: container,
            LabResultsWrapper.lab_result_matched_qty: 0,
            LabResultsWrapper.lab_result_matched_price: 0,
            LabResultsWrapper.lab_result_log: f""
        }

        self.event = LabResults(**addData)
        self.event.lab_result_patr = self.getPATR()
        
        if(not self.rawRun): LabResultsWrapper().save(self.event)

        self.orders = []
        self.log("Check condition OK -> watting close:" + str(closePrice))
        return Reply.make(True, 'Watting an order')

    #check if there is any pending event or not
    def checkEvent(self):
        if(not self.event is None):
            if(self.event.lab_result_pending == 0):
                return False
            else: 
                return True
        else:
            self.event = LabResults(lab_result_pending=0)
            self.orders = []
            return False
            
    def monitorEvent(self):
        
        status = Number(self.event.lab_result_status)
        flowName = self.getFlowName()
       
        if(status == LabResultsWrapper.LAB_RESULT_STATUS_MATCHED or status == LabResultsWrapper.LAB_RESULT_STATUS_MATCHED_PART):
            if(self.matchedParamsPhase != self.event.lab_result_phase):
                phase = Number(self.event.lab_result_phase)
                condition = self.getMatchCondition(flowName, phase)
                cfgBaseProfit = Number(get(condition, 'baseprofit', self.getFlowData(flowName, 'baseprofit')))
                self.matchedParamsPhase = self.event.lab_result_phase
                self.maker = None
                self.maxOrderProfit = 0
                self.baseProfit = cfgBaseProfit
        if(status == LabResultsWrapper.LAB_RESULT_STATUS_PENDING or status == LabResultsWrapper.LAB_RESULT_STATUS_PHASE_PENDING):
            result = self.monitorPending(flowName)
            if(not result['result'] or not result['data']['continue']): return result
        if(Number(self.event.lab_result_matched_qty) > 0 and status != LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING):
            result = self.monitorMatched(flowName)
            if(not result['result'] or not result['data']['continue']): return result
        if(status == LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING):
            result = self.monitorStopPending(flowName)
            if(not result['result'] or not result['data']['continue']): return result
        if(status == LabResultsWrapper.LAB_RESULT_STATUS_ENTER_WAITTING):
            result = self.monitorEnterWaiting(flowName)
            if(not result['result'] or not result['data']['continue']): return result
        if(status == LabResultsWrapper.LAB_RESULT_STATUS_MATCHED_PART):
            result = self.monitorMatchedPart(flowName)
            if(not result['result'] or not result['data']['continue']): return result
        if(status == LabResultsWrapper.LAB_RESULT_STATUS_RELEASE_WAITTING):
            result = self.monitorReleaseWaiting(flowName)
            if(not result['result'] or not result['data']['continue']): return result
        if(status == LabResultsWrapper.LAB_RESULT_STATUS_RELEASE_PENDING):
            result = self.monitorReleasePending(flowName)
            if(not result['result'] or not result['data']['continue']): return result
        return Reply.make(True, 'Success', {'continue': True, 'pending': True})
    
    def monitorPending(self, flowName):

        enterPrice = Number(self.event.lab_result_order_price)
        closePrice = Number(self.frame1m['close'])
        price = self.getCheckPendingPrice(
            closePrice, 
            self.frame1m['high'], 
            self.frame1m['low'], 
            self.frame1m['open_time']
        )
        isMatched = False
        market = False
        isTaker = False
        if(not self.maker):
            matchPrice = closePrice
            isTaker = True
            self.maker = True
        else:
            matchPrice = enterPrice

        condition = self.getMatchCondition(flowName, Number(self.event.lab_result_phase))
        enterPriceSetting = get(condition, 'enter_price', 'market')
        
        if(enterPriceSetting == 'market'): market = True
        orderType = self.event.lab_result_type

        if(orderType == LabResultsWrapper.LAB_RESULT_TYPE_LONG):
            if(market or price <= enterPrice):
                isMatched = True
        elif(orderType == LabResultsWrapper.LAB_RESULT_TYPE_SHORT):
            if(market or price >= enterPrice):
                isMatched = True

        if(isMatched):
            cfgBaseProfit = Number(get(condition, 'baseprofit', self.getFlowData(flowName, 'baseprofit')))
            matchedQty = Number(self.event.lab_result_matched_qty)
            orderQty = Number(self.event.lab_result_order_qty)
            matchedPrice = Number(self.event.lab_result_matched_price)
            total = matchedQty + orderQty
            matchedAvgPrice = (matchedPrice * matchedQty + matchPrice * orderQty)/total
            self.log("Match price:" + str(matchedAvgPrice))
            nextPhase = Number(self.event.lab_result_order_phase)
            status = LabResultsWrapper.LAB_RESULT_STATUS_MATCHED if (nextPhase == self.getMatchLeng(flowName) - 1) else LabResultsWrapper.LAB_RESULT_STATUS_MATCHED_PART
            updateData = {
                LabResultsWrapper.lab_result_status: status,
                LabResultsWrapper.lab_result_matched_price: matchedAvgPrice,
                LabResultsWrapper.lab_result_matched_time: self.runtime,
                LabResultsWrapper.lab_result_matched_qty : total,
                LabResultsWrapper.lab_result_low : Number(self.frame1m['low']),
                LabResultsWrapper.lab_result_high : Number(self.frame1m['high']),
                LabResultsWrapper.lab_result_baseprofit : cfgBaseProfit,
                LabResultsWrapper.lab_result_phase : nextPhase,
                LabResultsWrapper.lab_result_last_price: matchPrice
            }
            
            if(self.event.lab_result_first_price is None): updateData[LabResultsWrapper.lab_result_first_price] = matchPrice

            commitPercent = self.takerCommit if isTaker else self.makerCommit
            commit = commitPercent * matchPrice * orderQty / 100

            #log to oder table
            order = LabOrder(**{
                LabOrderWrapper.lab_order_action: self.event.lab_result_id,
                LabOrderWrapper.lab_order_time: self.runtime,
                LabOrderWrapper.lab_order_symbol: self.symbol,
                LabOrderWrapper.lab_order_qty: orderQty,
                LabOrderWrapper.lab_order_type: orderType,
                LabOrderWrapper.lab_order_phase: nextPhase,
                LabOrderWrapper.lab_order_commit: commit,
                LabOrderWrapper.lab_order_price: matchPrice,
                LabOrderWrapper.lab_order_account: self.account.lab_account_id
            })
            if(not self.rawRun): LabOrderWrapper().save(order)
            self.orders.append(order)

            #update profit after add model
            self.updateProfit(-commit)

            #Cal event profit
            eventProfit = self.calEventProfit()
            updateData[LabResultsWrapper.lab_result_eventprofit] = eventProfit

            self.updateEvent(updateData)

            #update optimization result
            if(nextPhase == 0):
                if(orderType == LabResultsWrapper.LAB_RESULT_TYPE_LONG):
                    self.accountImp.totalLong += 1
                else:
                    self.accountImp.totalShort += 1

            self.log("Matched " + str(matchPrice))
            return Reply.make(True, 'Make Order', {'continue': False, 'pending': True})

        else:

            timeLife = Number(self.getFlowData(flowName, 'timelife'))
            if(timeLife > 0):
                startTime = Number(self.event.lab_result_order_time)
                matchedQty = Number(self.event.lab_result_matched_qty)
                if(self.runtime - startTime > timeLife * 60000):
                    status = LabResultsWrapper.LAB_RESULT_STATUS_MATCHED_PART if matchedQty > 0 else LabResultsWrapper.LAB_RESULT_STATUS_CANCLE
                    self.updateEvent({
                        LabResultsWrapper.lab_result_status: status,
                        LabResultsWrapper.lab_result_pending: 1 if matchedQty > 0 else 0,
                        LabResultsWrapper.lab_result_params: "Got the timelife " + str(timeLife) + " minutes"
                    })
                    return Reply.make(True, 'Cancle Order', {'continue': False, 'pending': matchedQty > 0})

            return Reply.make(True, 'Still Pending', {'continue': False, 'pending': True})

    def monitorMatched(self, flowName):
        matchedPrice = Number(self.event.lab_result_matched_price)
        matchedEma5 = Number(self.event.lab_result_matched_ema5)

        closePrice = Number(self.frame1m['close'])

        # cfgBackprofitBaseon = self.getFlowData(flowName, 'baseprofit_baseon')
        cfgBackprofitBaseon = 'close'
        
        orderType = self.event.lab_result_type
        price = self.getCheckMatchedPrice(
            closePrice, 
            Number(self.frame1m['high']), 
            Number(self.frame1m['low']), 
            Number(self.frame1m['open_time'])
        )

        if (orderType == LabResultsWrapper.LAB_RESULT_TYPE_LONG) :

            maxProfitReal = (price['max'] - matchedPrice) * 100 / matchedPrice
            minProfitReal = (price['min'] - matchedPrice) * 100 / matchedPrice
            profitReal = (closePrice - matchedPrice) * 100 / matchedPrice

            if (cfgBackprofitBaseon == 'close') :
                maxProfit = maxProfitReal
                minProfit = minProfitReal
                profit = profitReal
            
            
        else :

            maxProfitReal = (matchedPrice - price['min']) * 100 / matchedPrice
            minProfitReal = (matchedPrice - price['max']) * 100 / matchedPrice
            profitReal = (matchedPrice - closePrice) * 100 / matchedPrice

            if (cfgBackprofitBaseon == 'close') :
                maxProfit = maxProfitReal
                minProfit = minProfitReal
                profit = profitReal
            
                
        editData = {}
        finished = False
        isTakeprofit = False
        releasePercent = 100
        releaseIndex = None
        releaseQty = None

        #update profit for event before checking
        self.event.lab_result_profit = profitReal
        
        #Check liquid
        if(self.account.lab_account_margin_type == 'ISOLATE'):
            if(self.checkLiquidation()):
                editData = {
                    LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING,
                    LabResultsWrapper.lab_result_params: 'Liquidation'
                }
                finished = True
            
        #Check stoploss and takeprofit
        if (not finished):
            condition = self.getMatchCondition(flowName, Number(self.event.lab_result_phase))
            stoploss = get(condition, 'stoploss', self.getFlowData(flowName, 'stoploss'))
            stoploss = self.calculateElement(stoploss)['data']
            takeprofit = get(condition, 'takeprofit', self.getFlowData(flowName, 'takeprofit'))
            takeprofit = self.calculateElement(takeprofit)['data']
            
            if (takeprofit is not False):
                takeprofit = Number(takeprofit)
                if(maxProfitReal >= takeprofit):
                    editData = {
                        LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING,
                        LabResultsWrapper.lab_result_params: 'Profit >= ' + str(takeprofit)
                    }
                    finished = True
                    isTakeprofit = True
            

            if (stoploss is not False): 
                stoploss = Number(stoploss)
                if(minProfitReal <= -stoploss):
                    editData = {
                        LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING,
                        LabResultsWrapper.lab_result_params: 'Profit <= ' + str(-stoploss)
                    }
                    finished = True
                    isTakeprofit = True
            
        #Check base profit
        if (not finished):

            stepprofit = Number(get(condition, 'step_profit', self.getFlowData(flowName, 'step_profit')))
            backprofit = Number(get(condition, 'back_profit', self.getFlowData(flowName, 'back_profit')))

            if (maxProfit > self.maxOrderProfit):
                self.maxOrderProfit = maxProfit
            
            if (self.maxOrderProfit > (self.baseProfit + stepprofit)) :
                if(stepprofit > 0):
                    self.baseProfit = self.baseProfit + floor((self.maxOrderProfit - self.baseProfit) / stepprofit) * stepprofit
                else:
                    self.baseProfit = self.maxOrderProfit
            
            
            
            if (self.baseProfit > 0 and self.maxOrderProfit >= self.baseProfit and profit < self.baseProfit - backprofit) :
                
                editData = {
                    LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING,
                    LabResultsWrapper.lab_result_params: 'Profit <= Base profit (' + str(self.baseProfit) + ') - back Step Profit(' + str(backprofit) + ')'
                }
                finished = True
            
        

        # Price Rule for stop
        if (not finished):

            runningRelease = self.event.lab_result_order_release

            stops = self.getStopConditions(flowName)
            if (not stops is None) :
                for key, stop in enumerate(stops):
                
                    if(not runningRelease is None and runningRelease <= key): continue
                    stopCondition = stop['condition']
                    result = self.compareOr(stopCondition)
                    if (not result['result']): return result
                    if (result['data']):
                        editData = {
                            LabResultsWrapper.lab_result_params: result['message'],
                            LabResultsWrapper.lab_result_order_phase: get(stop, 'phase_update', self.event.lab_result_phase),
                            LabResultsWrapper.lab_result_order_release: key
                        }
                        finished = True
                        releasePercent = get(stop, 'release_percent', 100)
                        releaseIndex = key

                        if (releasePercent < 100) :
                            qty = Number(self.event.lab_result_matched_qty)
                            releaseQty = qty * releasePercent / 100
                        break
                    

        if (finished) :
            if (releaseIndex is None):
                self.log('matched -> stoppending eventprofit:' + str(self.event.lab_result_eventprofit) + " Close: " + str(closePrice) + " profit:" + str(self.event.lab_result_profit) + " lastprice:" + str(self.event.lab_result_last_price) + "high: "+str(self.frame1m['high']))
                editData[LabResultsWrapper.lab_result_status] = LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING
            else :
                self.log('matched -> releaseWatting eventprofit:' + str(self.event.lab_result_eventprofit) + " Close: " + str(closePrice) + " profit:" + str(self.event.lab_result_profit) + " lastprice:" + str(self.event.lab_result_last_price) + "high: "+str(self.frame1m['high']))
                editData[LabResultsWrapper.lab_result_status] = LabResultsWrapper.LAB_RESULT_STATUS_RELEASE_WAITTING
                editData[LabResultsWrapper.lab_result_order_qty] = releaseQty
                self.releaseBase = profitReal
            

        
        editData[LabResultsWrapper.lab_result_baseprofit] = self.baseProfit
        editData[LabResultsWrapper.lab_result_profit] = profitReal
        
        self.updateEvent(editData, finished)

        #Logging if is enabled 
        if(not self.rawRun):
            if(isset(self.params, LabCampaignsWrapper.LAB_CAMPAIGN_PARAMS_LOG) and self.params[LabCampaignsWrapper.LAB_CAMPAIGN_PARAMS_LOG] == 1):
                LabEventLogsWrapper().create({
                    LabEventLogsWrapper.lab_elog_time: self.runtime,
                    LabEventLogsWrapper.lab_elog_campaign: self.campaign.lab_campaign_id,
                    LabEventLogsWrapper.lab_elog_symbol: self.symbol,
                    LabEventLogsWrapper.lab_elog_matched: orderType,
                    LabEventLogsWrapper.lab_elog_chart : self.frame1m['open_time'],
                    LabEventLogsWrapper.lab_elog_result : json.dumps({'Status': 'Stop Pending' if finished else 'Matched'}),
                })
        

        if (finished):
            self.labPendingStop = self.runtime + 0.25 * 1000
            
        return Reply.make(True, 'Pending Event', {'continue': not finished, 'pending': True})
            
    def monitorStopPending(self, flowName):
    
        if (self.runtime < self.labPendingStop) :
            return Reply.make(True, 'Pending Event', {'continue': False, 'pending': True})
        
        matchedPrice = Number(self.event.lab_result_matched_price)
        price = Number(self.frame1m['close'])
        orderType = self.event.lab_result_type

        commitPercent = self.takerCommit
        commit = commitPercent * price * Number(self.event.lab_result_matched_qty) / 100
        if (orderType == LabResultsWrapper.LAB_RESULT_TYPE_LONG):
            pnl = (price - matchedPrice) * Number(self.event.lab_result_matched_qty)
        else :
            pnl = (matchedPrice - price) * Number(self.event.lab_result_matched_qty)
        
        order = LabOrder(**{
            LabOrderWrapper.lab_order_action: self.event.lab_result_id,
            LabOrderWrapper.lab_order_time: self.runtime,
            LabOrderWrapper.lab_order_symbol: self.symbol,
            LabOrderWrapper.lab_order_qty: Number(self.event.lab_result_matched_qty),
            LabOrderWrapper.lab_order_type: LabResultsWrapper.LAB_RESULT_TYPE_SHORT if orderType == LabResultsWrapper.LAB_RESULT_TYPE_LONG else LabResultsWrapper.LAB_RESULT_TYPE_LONG,
            LabOrderWrapper.lab_order_phase: self.event.lab_result_phase,
            LabOrderWrapper.lab_order_commit: commit,
            LabOrderWrapper.lab_order_pnl: pnl,
            LabOrderWrapper.lab_order_price: price,
            LabOrderWrapper.lab_order_account: self.account.lab_account_id
        })
        if(not self.rawRun): LabOrderWrapper().save(order)
        self.orders.append(order)

        #update profit righ after create order
        self.updateProfit(pnl - commit)
       
        pnlData = self.calCommit()
        commit = pnlData['commit']
        pnl = pnlData['pnl']
        isProfit = pnl > commit
        package = Number(self.event.lab_result_budget)
        realPNL = pnl - commit
        realProfit = (realPNL) * 100 / package
        invest = Number(self.event.lab_result_matched_qty) * matchedPrice
        profit = realPNL * 100 / invest

        resultInterval = self.runtime - Number(self.event.lab_result_chart)

        #update optimization result
        if(self.maxInterval < resultInterval): self.maxInterval = resultInterval
        self.totalInterval += resultInterval
        self.totalPosition += 1
        if(isProfit):
            self.accountImp.totalTakeprofit += 1
        else:
            self.accountImp.totalStoploss += 1

        #update choice result
        self.choiceData['total_position'] += 1
        self.choiceData['total_interval'] += resultInterval
        self.choiceData['profit'] += realPNL

        

        editData = {
            LabResultsWrapper.lab_result_pending: 0,
            LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_TAKEPROFIT if isProfit else LabResultsWrapper.LAB_RESULT_STATUS_STOPLOSS,
            LabResultsWrapper.lab_result_sell_price: price,
            LabResultsWrapper.lab_result_sell_time: self.runtime,
            LabResultsWrapper.lab_result_close_time: self.runtime,
            LabResultsWrapper.lab_result_realprofit: realProfit,
            LabResultsWrapper.lab_result_eventprofit: profit,
            LabResultsWrapper.lab_result_realpnl: realPNL,
            LabResultsWrapper.lab_result_interval: resultInterval,


        }

        self.updateEvent(editData)

        #update period event. need to after update event
        self.labPendingTime = self.runtime
        self.periodEvent = self.event

        if(isset(self.params, LabCampaignsWrapper.LAB_CAMPAIGN_PARAMS_LOG) and self.params[LabCampaignsWrapper.LAB_CAMPAIGN_PARAMS_LOG] == 1):
            LabEventLogsWrapper().create({
                LabEventLogsWrapper.lab_elog_time: self.runtime,
                LabEventLogsWrapper.lab_elog_campaign: self.campaign.lab_campaign_id,
                LabEventLogsWrapper.lab_elog_symbol: self.symbol,
                LabEventLogsWrapper.lab_elog_matched: orderType,
                LabEventLogsWrapper.lab_elog_chart : self.frame1m['open_time'],
                LabEventLogsWrapper.lab_elog_result : json.dumps({'Status': 'Take profit' if isProfit else 'Stoploss'}),
                LabEventLogsWrapper.lab_elog_profit: self.event.lab_result_profit,
            })

        self.autoArrange(realPNL)

        self.log("Stopped -> finished: close" + str(price))
        
        return Reply.make(True, 'No Pending Event', {'continue': False, 'pending': False})

    def monitorEnterWaiting(self, flowName):
        isMakeOrder = False
        isCancle = False
        cancleReason = ''

        nextPhase = Number(self.event.lab_result_order_phase)
        oderType = self.event.lab_result_type
        nextCondition = self.getMatchCondition(flowName, nextPhase)
        closePrice = Number(self.frame1m['close'])

        enterRule = get(nextCondition,'enter_rule', None)
        enterCancle = get(nextCondition,'enter_cancle', None)

        if (not enterRule is None) :

            result = self.compareOr(enterRule)
            if (not result['result']): return result
            isMakeOrder = result['data']
            cancleReason = result['message']

            if (not enterCancle is None and not isMakeOrder) :
                result = self.compareOr(enterCancle)
                if (not result['result']): return result
                isCancle = result['data']
                cancleReason = result['message']
            
        
        if (enterRule == None) :

            enterStep = Number(get(nextCondition,'enter_step', 0))
            enterBack = Number(get(nextCondition,'enter_back', 0))
            enterPrice = Number(self.event.lab_result_enter_price)

            if (enterStep > 0) :

                checkPrice = self.getCheckWaitingPrice(
                    closePrice, 
                    Number(self.frame1m['high']), 
                    Number(self.frame1m['low']), 
                    Number(self.frame1m['open_time'])
                )


                if (oderType == LabResultsWrapper.LAB_RESULT_TYPE_LONG):

                    down = (enterPrice - checkPrice['min']) * 100 / enterPrice
                    downBase = (enterPrice - self.enterBase) * 100 / enterPrice
                    currentDown = (enterPrice - closePrice) * 100 / enterPrice

                    if (down > (downBase + enterStep)):
                        downBase = floor(down / enterStep) * enterStep
                        self.enterBase = enterPrice - (enterPrice *  downBase / 100)
                    

                    if (downBase - currentDown >= enterBack) :
                        if (currentDown >= 0 or self.getFlowData(flowName, 'allow_negative_price_rate')) :
                            isMakeOrder = True
                            self.log("Waiting -> enterpending down:" + str(down) + " downbase: " + str(downBase) + " currentDown:" + str(currentDown) + " enterback: " + str(enterBack))
                        else :
                            isCancle = True
                            cancleReason = 'Do not allow negative price rate'
                    else:
                        self.log("Waiting down:" + str(down) + " downbase: " + str(downBase) + " currentDown:" + str(currentDown) + " enterback: " + str(enterBack))
                        
                    
                elif (oderType == LabResultsWrapper.LAB_RESULT_TYPE_SHORT) :

                    up = (checkPrice['max'] - enterPrice) * 100 / enterPrice
                    upBase = (self.enterBase - enterPrice) * 100 / enterPrice
                    currentUp = (closePrice - enterPrice) * 100 / enterPrice

                    if (up > (upBase + enterStep)) :
                        upBase = floor(up / enterStep) * enterStep
                        self.enterBase = enterPrice + (enterPrice * upBase / 100)
                    

                    if (upBase - currentUp >= enterBack) :

                        if (currentUp >= 0 or self.getFlowData(flowName, 'allow_negative_price_rate')): 
                            isMakeOrder = True
                        else :
                            isCancle = True
                            cancleReason = 'Do not allow negative price rate'

            else:
                # if enter step = 0 then make order
                isMakeOrder = True


        #Check max trade open limit

        if (nextPhase == 0) :

            if(self.account.lab_account_sync == 1):
                freePossition = self.getFreePosition(flowName)
                if (not freePossition is None and freePossition <= 0) :
                    isCancle = True
                    isMakeOrder = False
                    cancleReason = 'Position limit. Free Position ' + str(freePossition)
                
                freeSlot = self.getFreeSlot(flowName)
                if (not freeSlot is None and freeSlot <= 0) :
                    isCancle = True
                    isMakeOrder = False
                    cancleReason = 'Slot limit. Free slot ' + str(freeSlot)
                

                if (isMakeOrder):
                    checkPossitionPriority = self.checkPositionPriority(flowName, freePossition)
                    if (not checkPossitionPriority['result']): return checkPossitionPriority
                    if (not checkPossitionPriority['data']):
                        isMakeOrder = False
                    
                if (isMakeOrder):
                    checkSlotPriority = self.checkSlotPriority(flowName, freeSlot)
                    if (not checkSlotPriority['result']): return checkSlotPriority
                    if (not checkSlotPriority['data']):
                        isMakeOrder = False


        if (isMakeOrder):
            makeOrderResult = self.makeOrder(closePrice, nextPhase, self.runtime)
            if(not makeOrderResult['result']): return makeOrderResult
            return Reply.make(True, 'Pending Event', {'continue': False, 'pending': True})

        if (isCancle):
            status = LabResultsWrapper.LAB_RESULT_STATUS_MATCHED_PART if (Number(self.event.lab_result_matched_qty) > 0) else LabResultsWrapper.LAB_RESULT_STATUS_CANCLE

            self.updateEvent({
                LabResultsWrapper.lab_result_status: status,
                LabResultsWrapper.lab_result_pending: 1 if (Number(self.event.lab_result_matched_qty) > 0) else 0,
                LabResultsWrapper.lab_result_params: cancleReason,
                LabResultsWrapper.lab_result_close_time: self.runtime
            })

            self.log(f"Cancle watting: {cancleReason}")

            return Reply.make(True, 'Pending Event', {'pending': Number(self.event.lab_result_matched_qty) > 0, 'continue': False})

        return Reply.make(True, 'Pending Event', {'continue': False, 'pending': True})
        
    def monitorMatchedPart(self, flowName):
        phase = Number(self.event.lab_result_phase)
        condition = self.getMatchCondition(flowName, phase)
        if (phase < (self.getMatchLeng(flowName) - 1)) :

            afterPhase = self.getNextPhase(condition, phase)
            if (not afterPhase['result']): return afterPhase
            afterPhase = afterPhase['data']
            afterCondition = self.getMatchCondition(flowName, afterPhase)
            #check enterpackage
            enterPackage = self.calculateElement(get(afterCondition, 'enter_package', 100))['data']
            if(enterPackage <= 0): return Reply.make(True, 'Pending', {'continue': False, 'pending': True})

            checkResult = self.compareOr(afterCondition['condition'])
            if (not checkResult['result']): return checkResult
            if (checkResult['data']) :
                self.log("matchpart -> Waitting for phase: " + str(afterPhase))
                enterStep = get(afterCondition,'enter_step', 0)
                enterRule = get(afterCondition,'enter_rule', None)

                closePrice = Number(self.frame1m['close'])

                # baseonData = json.loads(self.event.lab_result_base)
                # baseonData[afterPhase] = self.data

                updateData = {
                    LabResultsWrapper.lab_result_enter_time: self.runtime,
                    LabResultsWrapper.lab_result_enter_price: closePrice,
                    LabResultsWrapper.lab_result_low: self.frame1m['low'],
                    LabResultsWrapper.lab_result_high: self.frame1m['high'],
                    LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_ENTER_WAITTING,
                    LabResultsWrapper.lab_result_order_phase: afterPhase
                }

                self.updateEvent(updateData)

                if (enterStep <= 0 and enterRule is None):
                    makeOrderResult = self.makeOrder(closePrice, afterPhase, self.runtime)
                    if(not makeOrderResult['result']): return makeOrderResult
                else:
                    #set enterbase and go to watting
                    self.enterBase = closePrice

            return Reply.make(True, 'Pending', {'continue': False, 'pending': True})
            
        else :
            self.updateEvent({LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_MATCHED})
            return Reply.make(True, 'Pending', {'continue': False, 'pending': True})

    def monitorReleaseWaiting(self, flowName):

        self.log('Release waitting close:' + str(self.frame1m['close']))

        releaseCondition = self.getStopCondition(flowName, self.event.lab_result_order_release)

        isRelease = True
        isCancle = False

        releaseRule = get(releaseCondition, 'release_rule', None)
        releaseCancle = get(releaseCondition, 'release_cancle', None)

        if (not releaseRule is None) :
            result = self.compareOr(releaseRule)
            if (not result['result']): return result
            isRelease = result['data']

            if (not releaseCancle is None and not isRelease) :
                result = self.compareOr(releaseCancle)
                if (not result['result']): return result
                isCancle = result['data']

        if (releaseRule == None) :

            releaseStep = Number(get(releaseCondition, 'release_step', 0))
            releaseBack = Number(get(releaseCondition, 'release_back', 0))
            if(self.releaseBase is None): self.releaseBase = 0

            if (releaseStep > 0) :
                #echo "check release step" . self.releaseBase . "\n"
                matchedPrice = Number(self.event.lab_result_matched_price)
                oderType = self.event.lab_result_type

                high = Number(self.frame1m['high'])
                low = Number(self.frame1m['low'])
                closePrice = Number(self.frame1m['close'])

                if (oderType == LabResultsWrapper.LAB_RESULT_TYPE_LONG) :
                    maxProfit = (high - matchedPrice) * 100 / matchedPrice
                    profit = (closePrice - matchedPrice) * 100 / matchedPrice
                elif (oderType == LabResultsWrapper.LAB_RESULT_TYPE_SHORT):
                    maxProfit = (matchedPrice - low) * 100 / matchedPrice
                    profit = (matchedPrice - closePrice) * 100 / matchedPrice
                

                if (maxProfit > (self.releaseBase + releaseStep)):
                    self.releaseBase = floor(maxProfit / releaseStep) * releaseStep

                if (self.releaseBase - profit > releaseBack):
                    isRelease = True
                else :
                    isRelease = False
                
        if (isRelease) :

            if (self.event.lab_result_order_qty is None):
                releaseQty =  Number(self.event.lab_result_matched_qty)
            else :
                releaseQty =  Number(self.event.lab_result_order_qty)
            
            totalQty = Number(self.event.lab_result_matched_qty) - releaseQty

            self.updateEvent({
                LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_RELEASE_PENDING if totalQty > 0 else LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING
            })

            self.labPendingStop = self.runtime + 0.25 * 1000

        elif (isCancle) :

            status = LabResultsWrapper.LAB_RESULT_STATUS_MATCHED_PART if Number(self.event.lab_result_matched_qty) > 0 else LabResultsWrapper.LAB_RESULT_STATUS_CANCLE

            self.updateEvent({
                LabResultsWrapper.lab_result_status: status,
                LabResultsWrapper.lab_result_pending: 1 if Number(self.event.lab_result_matched_qty) > 0 else 0,
                LabResultsWrapper.lab_result_order_release: None
            })
            
        return Reply.make(True, 'Pending Event', {'continue': False, 'pending': True})

    def monitorReleasePending(self, flowName):
        
        self.log('Release pending close:' + str(self.frame1m['close']))
        #Delay
        if (self.runtime < self.labPendingStop):
            return Reply.make(True, 'Pending Event', {'continue': False, 'pending': True})
        
        matchedPrice = Number(self.event.lab_result_matched_price)
        orderType = self.event.lab_result_type
        nextPhase = Number(self.event.lab_result_order_phase)
        closePrice = Number(self.frame1m['close'])

        commitPercent = self.takerCommit
        commit = commitPercent * closePrice * Number(self.event.lab_result_order_qty) / 100
        if (orderType == LabResultsWrapper.LAB_RESULT_TYPE_LONG) :
            pnl = (closePrice - matchedPrice) * Number(self.event.lab_result_order_qty)
        else :
            pnl = (matchedPrice - closePrice) * Number(self.event.lab_result_order_qty)
    
        releaseProfit = pnl - commit

        order = LabOrder(**{
            LabOrderWrapper.lab_order_action: self.event.lab_result_id,
            LabOrderWrapper.lab_order_time: self.runtime,
            LabOrderWrapper.lab_order_symbol: self.symbol,
            LabOrderWrapper.lab_order_qty: Number(self.event.lab_result_order_qty),
            LabOrderWrapper.lab_order_type: LabResultsWrapper.LAB_RESULT_TYPE_SHORT if orderType == LabResultsWrapper.LAB_RESULT_TYPE_LONG else LabResultsWrapper.LAB_RESULT_TYPE_LONG,
            LabOrderWrapper.lab_order_phase: nextPhase,
            LabOrderWrapper.lab_order_commit: commit,
            LabOrderWrapper.lab_order_pnl: pnl,
            LabOrderWrapper.lab_order_price: closePrice,
            LabOrderWrapper.lab_order_account: self.account.lab_account_id
        })
        if(not self.rawRun): LabOrderWrapper().save(order)
        self.orders.append(order)
        self.updateProfit(releaseProfit)

        totalQty = Number(self.event.lab_result_matched_qty) - Number(self.event.lab_result_order_qty)
        status = LabResultsWrapper.LAB_RESULT_STATUS_MATCHED if nextPhase == (self.getMatchLeng(flowName) - 1) else LabResultsWrapper.LAB_RESULT_STATUS_MATCHED_PART
        nextCondition = self.getMatchCondition(flowName, nextPhase)
        cfgBaseProfit = Number(get(nextCondition, 'baseprofit', self.getFlowData(flowName, 'baseprofit')))
        
        self.updateEvent({
            LabResultsWrapper.lab_result_status: status,
            LabResultsWrapper.lab_result_matched_qty: totalQty,
            LabResultsWrapper.lab_result_baseprofit: cfgBaseProfit,
            LabResultsWrapper.lab_result_order_release: None,
            LabResultsWrapper.lab_result_eventprofit : self.calEventProfit(),
            LabResultsWrapper.lab_result_last_price : closePrice,
            LabResultsWrapper.lab_result_phase: nextPhase
        })

        
        return Reply.make(True, 'Pending Event', {'continue': False, 'pending': True})


    def getPATR(self):
        try:
            if(self.event is None): return None
            patrCfg = self.getFlowData(self.getFlowName(), 'patr')
            return self.calculateElement(patrCfg)['data']
        except Exception as e:
            print(e)
            return None

    def calculateElement(self, struct:dict, dynamicIndex = None):
        
        if(type(struct) in [int, float, bool]): return Reply.make(True, str(struct), struct)

        if(isNumeric(struct)): return Reply.make(True, str(struct), Number(struct))

        if(type(struct) is str):
            if(struct == 'order_time'):
                if(self.event is None): return Reply.make(False, 'No event')
                return Reply.make(True, struct, Number(self.event.lab_result_order_time))
            
            if(struct == 'budget'):
                value = self.getInvestBudget()
                return Reply.make(True, f"{struct}({value})", value)
            
            if(struct == 'patr'):
                value = self.getPATR()
                return Reply.make(True, f"{struct}({value})", value)
            
            return Reply.make(True, struct, struct)

        
        structType = get(struct, 'type', 'frame')
        
        if(structType == 'frame'):
            
            frame = get(struct, 'frame', None)
            indexCfg = get(struct, 'index', 0)
            column = get(struct, 'column', None)
            symbol = get(struct, 'symbol', self.symbol)
            
            if(indexCfg == 'dynamic'):
                index = dynamicIndex
            else:
                index = Number(indexCfg) - 1

            des = symbol + " Frame "+str(frame)+" "+str(column)+"("+str(indexCfg)+")"
            if(frame is None or index is None or column is None):
                return Reply.make(False, 'Please define symbol, frame, column and index ' + des + json.dumps(struct))
        
            try:
                if column not in self.checkData[symbol]['kline'][frame][index]:
                    value = None
                else:
                    value = self.checkData[symbol]['kline'][frame][index][column]
                
                if(isNumeric(value)):
                    value = Number(value)
                    percent = struct.get('percent', None)
                    if(percent is not None):
                        percent = float(percent)
                        value = value * percent/100
                        des = f"({des}) {percent}% {column}"
                        
                    multiply = struct.get('multiply', None)
                    if(multiply is not None):
                        multiplyNumber = self.calculateElement(multiply)
                        if(not multiplyNumber['result'] or multiplyNumber['data'] is None): return multiplyNumber
                        value = value * Number(multiplyNumber['data'])
                        des = f"({des}) * {multiplyNumber['message']}"
                        
                    divide = struct.get('divide', None)
                    if(divide is not None):
                        divideNumber = self.calculateElement(divide)
                        if(not divideNumber['result'] or divideNumber['data'] is None): return divideNumber
                        divideNum = Number(divideNumber['data'])
                        if(divideNum == 0): return Reply.make(False, f"Can not divide zero: {divideNumber['message']}")
                        value = value / divideNum
                        des = f"({des}) / {divideNumber['message']}"
                        
                    add = struct.get('add', None)
                    if(add is not None):
                        addNumber = self.calculateElement(add)
                        if(not addNumber['result'] or addNumber['data'] is None): return addNumber
                        value = value + Number(addNumber['data'])
                        des = f"{des} + {addNumber['message']}"
                        
                    subtract = struct.get('subtract', None)
                    if(subtract is not None):
                        subtractNumber = self.calculateElement(subtract)
                        if(not subtractNumber['result'] or subtractNumber['data'] is None): return subtractNumber
                        value = value - Number(subtractNumber['data'])
                        des = f"{des} - {subtractNumber['message']}"
                
                return Reply.make(True, f"{des}[{value}]", value)
                

            except Exception:
                return Reply.make(False, 'Can not get Data ' + symbol + " " + frame + " " + str(indexCfg) + " " + str(column))

        elif(structType == 'event'):
            if(self.event is None): return Reply.make(False, 'No Event')
            column = get(struct, 'column', None)
            des = f"Event {column}"
            column = 'lab_result_' + str(column)
            if(column == LabResultsWrapper.lab_result_interval):
                value = (self.runtime - Number(self.event.lab_result_chart))/60000
            else:
                if(not hasattr(self.event, column)): return Reply.make(False, 'Can not find column ' + column)
                value = getattr(self.event, column)
            if(isNumeric(value)):
                value = Number(value)
                percent = struct.get('percent', None)
                if(percent is not None):
                    percent = float(percent)
                    value = value * percent/100
                    des = f"({des}) {percent}% {column}"
                    
                multiply = struct.get('multiply', None)
                if(multiply is not None):
                    multiplyNumber = self.calculateElement(multiply)
                    if(not multiplyNumber['result'] or multiplyNumber['data'] is None): return multiplyNumber
                    value = value * Number(multiplyNumber['data'])
                    des = f"({des}) * {multiplyNumber['message']}"
                    
                divide = struct.get('divide', None)
                if(divide is not None):
                    divideNumber = self.calculateElement(divide)
                    if(not divideNumber['result'] or divideNumber['data'] is None): return divideNumber
                    divideNum = Number(divideNumber['data'])
                    if(divideNum == 0): return Reply.make(False, f"Can not divide zero: {divideNumber['message']}")
                    value = value / divideNum
                    des = f"({des}) / {divideNumber['message']}"
                    
                add = struct.get('add', None)
                if(add is not None):
                    addNumber = self.calculateElement(add)
                    if(not addNumber['result'] or addNumber['data'] is None): return addNumber
                    value = value + Number(addNumber['data'])
                    des = f"{des} + {addNumber['message']}"
                    
                subtract = struct.get('subtract', None)
                if(subtract is not None):
                    subtractNumber = self.calculateElement(subtract)
                    if(not subtractNumber['result'] or subtractNumber['data'] is None): return subtractNumber
                    value = value - Number(subtractNumber['data'])
                    des = f"{des} - {subtractNumber['message']}"
                    
            return Reply.make(True, f"{des}[{value}]", value)

        elif(structType == 'calculate'):
            number1 = get(struct, 'number_1', None)
            number2 = get(struct, 'number_2', None)
            logic = get(struct, 'logic', None)
            if(number1 is None or number2 is None or logic is None):
                Reply.make(False, "Please define number_1, number_2 and logic " + json.dumps(struct))
            num1 = self.calculateElement(number1)
            if(not num1['result']): return num1
            num2 = self.calculateElement(number2)
            if(not num2['result']): return num2

            des1 = num1['message']
            des2 = num2['message']
            des = des1 + " " + str(logic) + " " + des2

            value = None
            # print(num1)
            # print(num2)
            num1 = Number(num1['data'])
            num2 = Number(num2['data'])
            if(num1 is not None and num2 is not None):
                if(logic == '+'): value = num1 + num2
                elif (logic == '-'): value = num1 - num2
                elif (logic == '*'): value = num1 * num2
                elif (logic == '/'): value = num1 / num2
                else: return Reply.make(False, 'Does not support logic ' + logic)
            
            
            if(isNumeric(value)):
                value = Number(value)
                percent = struct.get('percent', None)
                if(percent is not None):
                    percent = float(percent)
                    value = value * percent/100
                    des = f"({des}) {percent}% {column}"
                    
                multiply = struct.get('multiply', None)
                if(multiply is not None):
                    multiplyNumber = self.calculateElement(multiply)
                    if(not multiplyNumber['result'] or multiplyNumber['data'] is None): return multiplyNumber
                    value = value * Number(multiplyNumber['data'])
                    des = f"({des}) * {multiplyNumber['message']}"
                    
                divide = struct.get('divide', None)
                if(divide is not None):
                    divideNumber = self.calculateElement(divide)
                    if(not divideNumber['result'] or divideNumber['data'] is None): return divideNumber
                    divideNum = Number(divideNumber['data'])
                    if(divideNum == 0): return Reply.make(False, f"Can not divide zero: {divideNumber['message']}")
                    value = value / divideNum
                    des = f"({des}) / {divideNumber['message']}"
                    
                add = struct.get('add', None)
                if(add is not None):
                    addNumber = self.calculateElement(add)
                    if(not addNumber['result'] or addNumber['data'] is None): return addNumber
                    value = value + Number(addNumber['data'])
                    des = f"{des} + {addNumber['message']}"
                    
                subtract = struct.get('subtract', None)
                if(subtract is not None):
                    subtractNumber = self.calculateElement(subtract)
                    if(not subtractNumber['result'] or subtractNumber['data'] is None): return subtractNumber
                    value = value - Number(subtractNumber['data'])
                    des = f"{des} - {subtractNumber['message']}"
                    
            return Reply.make(True, f"{des}[{value}]", value)
        
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
                    
        elif(structType == 'BUSD'):
            indexCfg = get(struct, 'index', 0)
            column = get(struct, 'column', None)
            symbol = get(struct, 'symbol', self.symbol)
            percent = Number(get(struct, 'percent', 100))

            index = Number(indexCfg) - 1

            if(percent != 100):
                des = symbol + " BUSD "+str(percent)+"% "+str(column)+"("+str(indexCfg)+")"
            else:
                des = symbol + " BUSD "+str(column)+"("+str(indexCfg)+")"
            if(index is None or column is None):
                return Reply.make(False, 'Please define symbol, column and index ' + des + json.dumps(struct))
           
            try:
                busdData = self.checkData[symbol]['busd']
                if(not isset(busdData, index) or not isset(busdData[index], column)): return Reply.make(True, des, None)
                value = busdData[index][column]
                if(isNumeric(value)): value = Number(value)
                if(percent != 100 and isNumeric(value)):
                    value = value * percent/100
                return Reply.make(True, des, value)
            except Exception as e:
                return Reply.make(False, 'Can not get Data ' + symbol + " " + str(indexCfg) + " " + str(column))
        
        elif(structType == 'OrderBook'):
            indexCfg = get(struct, 'index', 0)
            column = get(struct, 'column', None)
            symbol = get(struct, 'symbol', self.symbol)
            percent = Number(get(struct, 'percent', 100))

            index = Number(indexCfg) - 1

            if(percent != 100):
                des = symbol + " OrderBook "+str(percent)+"% "+str(column)+"("+str(indexCfg)+")"
            else:
                des = symbol + " OrderBook "+str(column)+"("+str(indexCfg)+")"
            if(index is None or column is None):
                return Reply.make(False, 'Please define symbol, column and index ' + des + json.dumps(struct))
           
            try:
                orderBookData = self.checkData[symbol]['orderbook']
                if(not isset(orderBookData, index) or not isset(orderBookData[index], column)): return Reply.make(True, des, None)
                value = orderBookData[index][column]
                if(isNumeric(value)): value = Number(value)
                if(percent != 100 and isNumeric(value)):
                    value = value * percent/100
                return Reply.make(True, des, value)
            except Exception:
                return Reply.make(False, 'Can not get Data ' + symbol + " " + str(indexCfg) + " " + str(column))

        elif(structType == 'Pressure'):
            indexCfg = get(struct, 'index', 0)
            column = get(struct, 'column', None)
            symbol = get(struct, 'symbol', self.symbol)
            if(symbol == 'ftx2binance'): symbol = ftx2binance(symbol)
            if(symbol == 'binance2ftx'): symbol = binance2ftx(symbol)
            percent = Number(get(struct, 'percent', 100))

            index = Number(indexCfg) - 1

            if(percent != 100):
                des = symbol + " Pressure "+str(percent)+"% "+str(column)+"("+str(indexCfg)+")"
            else:
                des = symbol + " Pressure "+str(column)+"("+str(indexCfg)+")"
            if(index is None or column is None):
                return Reply.make(False, 'Please define symbol, column and index ' + des + json.dumps(struct))
           
            try:
                pressureData = self.checkData[symbol]['pressure']
                if(not isset(pressureData, index) or not isset(pressureData[index], column)): return Reply.make(True, des, None)
                value = pressureData[index][column]
                if(isNumeric(value)): value = Number(value)
                if(percent != 100 and isNumeric(value)):
                    value = value * percent/100
                return Reply.make(True, des, value)
            except Exception:
                return Reply.make(False, 'Can not get Data ' + symbol + " " + str(indexCfg) + " " + str(column))




    def makeOrder(self, closePrice, phase, runtime):
        self.log('Make an order ' + str(closePrice))
        
        self.maker = False
        type = self.event.lab_result_type
        flowName = self.getFlowName()
        condition = self.getMatchCondition(flowName, phase)

        enterPriceSetting = get(condition, 'enter_price', 'market')
        margin = Number(get(condition, 'margin', self.getFlowData(flowName, 'margin')))

        if(margin < Number(self.event.lab_result_margin)):
            return Reply.make(False, 'Can not reduce margin')
        

        if (isNumeric(enterPriceSetting)):
            enterPrice = closePrice * Number(enterPriceSetting) / 100
        else :
            enterPrice = closePrice
        
    
        budget = self.getInvestBudget()
        enterPackage = self.calculateElement(get(condition, 'enter_package', 100))['data']
        phaseBudget = budget * enterPackage / 100
        qty = phaseBudget / enterPrice
        qty = qty * margin
        
        if(qty <= 0): return Reply.make(False, "Quantity must be greater than 0")

        self.updateEvent({
            LabResultsWrapper.lab_result_order_price: enterPrice,
            LabResultsWrapper.lab_result_order_time: runtime,
            LabResultsWrapper.lab_result_order_qty: qty,
            LabResultsWrapper.lab_result_order_phase: phase,
            LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_PENDING if phase == 0 else LabResultsWrapper.LAB_RESULT_STATUS_PHASE_PENDING,
            LabResultsWrapper.lab_result_low: self.frame1m['low'],
            LabResultsWrapper.lab_result_high: self.frame1m['high'],
            LabResultsWrapper.lab_result_margin: margin,
            LabResultsWrapper.lab_result_budget: budget,
        })

        return Reply.make(True, "Success")
           
    # String FlowName
    
    def getFlowName(self):
        flow = self.event.lab_result_flow
        strategy = self.event.lab_result_strategy
        flowName = str(strategy) + "--" + str(flow)
        return flowName


    def checkPositionPriority(self, flowName, freeSlot = None):
    
        # print('checkPositionPriority')
        if (freeSlot is None): freeSlot = self.getFreePosition(flowName)
        if (freeSlot is None): return Reply.make(True, 'success', True)

        priority = get(self.priority, self.symbol, 0)
        waittingTrades = self.accountImp.getWattingPosition()
        takenSlot = 0
        watting:LabResults
        for watting in waittingTrades:
            symbol = watting.lab_result_symbol
            otherPriority = get(self.priority, symbol, 0)
            if (otherPriority > priority):
                takenSlot += 1
        return Reply.make(True, 'success', freeSlot > takenSlot)
    
    #Check if the symbol is allowed to make order check strategy_slot
    def checkSlotPriority(self, flowName, freeSlot = None):
        # print('checkSlotPriority')
        if (freeSlot is None): freeSlot = self.getFreeSlot(flowName)
        if (freeSlot is None): return Reply.make(True, 'success', True)
        
        strategyId = self.getFlowData(flowName, 'strategy')
        priority = get(self.priority, self.symbol, 0)
        waittingTrades = self.accountImp.getWattingSlot(strategyId)
        takenSlot = 0
        watting:LabResults
        for watting in waittingTrades:
            symbol = watting.lab_result_symbol
            otherPriority = get(self.priority, symbol, 0)
            if (otherPriority > priority):
                takenSlot += 1
        return Reply.make(True, 'success', freeSlot > takenSlot)

    def checkBlacklist(self, flowName):
        blacklist = self.getFlowData(flowName, 'blacklist')
        if (not type(blacklist) is list): return True
        symbol = self.campaign.lab_campaign_symbol
        return not symbol in blacklist

    def checkLiquidation(self):
        
        high = Number(self.frame1m['high'])
        low = Number(self.frame1m['low'])
        matchedQty = Number(self.event.lab_result_matched_qty)
        matchedPrice = Number(self.event.lab_result_matched_price)
        margin = Number(self.event.lab_result_margin)
        if(margin == 0): margin = 1
        
        invest = matchedQty * matchedPrice / margin
        if(self.event.lab_result_type == LabResultsWrapper.LAB_RESULT_TYPE_LONG):
            worstPrice = low
            loss = (matchedPrice - worstPrice) * matchedQty
        else:
            worstPrice = high
            loss = (high - matchedPrice) * matchedQty
        

        liquid = loss > (invest * 90/100)

        return liquid
        
    def updateEvent(self, editData, force = True):
        if(not self.event is None):

            for key in editData:
                setattr(self.event, key, editData[key])
            
            if(isset(editData, LabResultsWrapper.lab_result_pending) and editData[LabResultsWrapper.lab_result_pending] == 0):
                if(not self.rawRun): self.event.save()

        return Reply.make(True, 'success', self.event)
    

    def getCheckWaitingPrice(self, price, high, low, open_time):
        if (open_time > self.event.lab_result_enter_time): return {'max' : high, 'min' : low}
        max = price
        min = price
        if (high != self.event.lab_result_high): max = high
        if (low != self.event.lab_result_low): min = low
        return {'max' : max, 'min' : min}
    

    def getCheckPendingPrice(self, price, high, low, open_time):
        eventType = self.event.lab_result_type
        if (eventType == LabResultsWrapper.LAB_RESULT_TYPE_LONG):
            if (open_time > self.event.lab_result_order_time): return low
            if (low != self.event.lab_result_low): return low
        elif (eventType == LabResultsWrapper.LAB_RESULT_TYPE_SHORT):
            if (open_time > self.event.lab_result_order_time): return high
            if (high != self.event.lab_result_high): return high
        return price
    

    def getCheckMatchedPrice(self, price, high, low, open_time):
        if (open_time > self.event.lab_result_matched_time): return {'max' : high, 'min' : low}
        max = price
        min = price
        if (high != self.event.lab_result_high): max = high
        if (low != self.event.lab_result_low): min = low
        return {'max' : max, 'min' : min}
    
    
    def calEventProfit(self):
        commit = self.calCommit()
        realPNL = commit['pnl'] - commit['commit']
        budget = commit['position_qty'] * commit['position_price']
        eventProfit = 0
        if (budget > 0):
            eventProfit = (realPNL) * 100 / budget
        return eventProfit

    def calCommit(self):
        # print('calCommit')
        orderType = self.event.lab_result_type
        commit = 0
        pnl = 0
        postitionQty = 0
        avgPrice = 0
        timePoint = time() * 1000
        
        order: LabOrder
        for order in self.orders:
            commit += Number(order.lab_order_commit)
            pnl += Number(order.lab_order_pnl)
            if(orderType == order.lab_order_type):
                avgPrice = (postitionQty * avgPrice + Number(order.lab_order_qty) * Number(order.lab_order_price))/(postitionQty + Number(order.lab_order_qty))
                postitionQty += Number(order.lab_order_qty)
            else:
                postitionQty -= Number(order.lab_order_qty)
        
        # print("calcommit data time: " + str(time() * 1000 - timePoint) + " ms")
        self.log("calculate commit " + json.dumps({
            'commit': commit,
            'pnl': pnl,
            'position_qty': postitionQty,
            'position_price': avgPrice
        }))
        return {
            'commit': commit,
            'pnl': pnl,
            'position_qty': postitionQty,
            'position_price': avgPrice
        }

    def updateProfit(self, profit):
        self.accountImp.updateProfit(profit)
    

    def autoArrange(self, profit=0):

        # print('autoArrange')
       
        account = self.accountImp.account #type: LabAccount
        if(account is None): return Reply.make(False, "No account")
        
        if (account.lab_account_compound == 1 and account.lab_account_sync == 1):
            
            # campaigns = LabCampaignsWrapper().filter({LabCampaignsWrapper.lab_campaign_account: account.lab_account_id}) 
            campaigns = self.accountImp.campaigns
            reserve = Number(account.lab_account_reserve)
            used = 0
            campaign: LabCampaigns
            for campaign in campaigns:
                budget = Number(campaign.lab_campaign_budget)
                used += budget
            
            balance = Number(account.lab_account_balance)
            balance = balance * (100 - reserve) / 100

            free = balance - used

            # if (free <= 0):
            #     return Reply.make(True, 'Free less than 0')
            
            added = floor(free * 1000 / len(campaigns)) / 1000

            for campaign in campaigns:
                campaign.lab_campaign_budget += added
               
            self.log("Auto arrange Balance: " + str(balance) + " free: " + str(free) + " added: " + str(added))
            return Reply.make(True, 'Success')
                
        elif(self.campaign.lab_campaign_compound == 1):
            self.campaign.lab_campaign_budget += Number(profit)
            return Reply.make(True, 'Success')
            
        return Reply.make(True, 'Compound is diabled')


    def getInvestBudget(self):
        campaign = self.campaign
        return Number(campaign.lab_campaign_budget) * Number(campaign.lab_campaign_active_budget) / 100


    def log(self, mess, runtime = None):
        return
        # if(self.symbol != 'VETUSDT'): return
        if(runtime is None): runtime = self.runtime
        name = self.campaign.lab_campaign_name
        dateTime = datetime.fromtimestamp(floor(runtime/1000), pytz.timezone("Asia/Ho_Chi_Minh"))
        print(f"{str(dateTime)}:[{name}] {str(mess)}")
        # print(str(dateTime) + ": [" + name + "] " + str(mess))

    # Create checking result for phase 0
    def createLeapCheckResult(self):
        leapResult = {}
        shortestLeap = getShortestLeap(self.cfgStrategy)
        self.shortestLeap = shortestLeap
        print(self.symbol + " Find leap on the strategy: " + str(shortestLeap))
        if(shortestLeap is None): raise Exception("No leap on the strategy")
        checkIsWorkingLeap(self.cfgStrategy, self)
        leapCondition = genLeapCondition(self.cfgStrategy)
        
        leapLeng = self.leapLeng
        campStartTime = Number(self.campaign.lab_campaign_start) * 1000
        campStopTime = Number(self.campaign.lab_campaign_stop) * 1000
        campStopTime = ceil(campStopTime/leapLeng[shortestLeap]) * leapLeng[shortestLeap] - 1

        #scan require data for leap testing
        needLeapData = {}
        scanNeedData(leapCondition, self.symbol, needLeapData, {})
        print(self.symbol + " Calcualte require data for leap")
        # print(needLeapData)
        #get index data
        needFrame = list(needLeapData[self.symbol]['kline'].keys())
        indexData = {}
        for frame in needFrame:
            if(frame == '1m'): raise Exception("Leap does not working if depend on frame 1m")
            symbolColName = "symbol"
            closeTimeColName = "close_time"
            startPointName = "is_close"
            collName = f"candle_{frame}"
            print(f"Get leap block data {self.symbol} " + frame + " from " + str(datetime.fromtimestamp(campStartTime/1000)) + " to " + str(datetime.fromtimestamp(campStopTime/1000)))
            
            frameData = list(self.accountImp.klineModel.setCollection(collName).find({
                symbolColName: self.symbol,
                startPointName: 1,
                closeTimeColName : {"$gte": campStartTime, "$lte": campStopTime}
            }).sort(closeTimeColName, ASCENDING))
            # print(len(frameData))
            if len(frameData) > 0:
                for data in frameData:
                    symbol = data[symbolColName]
                    if(not isset(indexData, symbol)): indexData[symbol] = {}
                    if(not isset(indexData[symbol], frame)): indexData[symbol][frame] = {}
                    indexData[symbol][frame][data[closeTimeColName]] = data
            else:
                if(not isset(indexData, self.symbol)): indexData[self.symbol] = {}
                indexData[self.symbol][frame] = {}

       
        #create fisrt check data for leap testing
        checkData = self.createLeapCheckData(needLeapData, campStartTime)
        
        if(not isset(indexData, self.symbol)): return leapResult
        longSymData = indexData[self.symbol][shortestLeap]
        # print(json.dumps(indexData, default=str))
        for runtime in longSymData:
            #update data to check data
            # print(json.dumps(needLeapData, default=str))
            for symbol in needLeapData:
                needDataSym = needLeapData[symbol]['kline']
                lastData = {'kline':{}}
                for frame in needDataSym:
                    if(isset(indexData, symbol)):
                        if(isset(indexData[symbol][frame], runtime)):
                            lastData['kline'][frame] = indexData[symbol][frame][runtime]
                        else:
                            tempFrameCloseTime = ceil(runtime/self.leapLeng[frame]) * self.leapLeng[frame] - 1
                            if(isset(indexData[symbol][frame], tempFrameCloseTime)):
                                lastData['kline'][frame] = indexData[symbol][frame][tempFrameCloseTime]
                            else:
                                tempFrameOpenTime = floor(runtime/self.leapLeng[frame]) * self.leapLeng[frame]
                                tempSymbolColName = "symbol"
                                tempTimeColName = "timestamp"
                                collName = f"candle_{frame}"
                                lastDataDb = list(self.accountImp.klineModel.setCollection(collName).find({
                                    tempSymbolColName: self.symbol,
                                    tempTimeColName : {"$gte": tempFrameOpenTime/1000, "$lte": tempFrameCloseTime/1000}
                                }).sort(tempTimeColName, DESCENDING))                                
                                print(f"{symbol} {frame} {runtime} get missing data {len(lastDataDb)}")
                                if(len(lastDataDb) > 0):
                                    lastData['kline'][frame] = lastDataDb[0]


                if(len(lastData.keys()) > 0):
                    updateCheckData(checkData, symbol, lastData, self.accountImp.checkDataLeng)
                    # print(json.dumps(checkData))
                    # exit(0)     
            #set running
            self.checkData = checkData
            checkResult = self.compareOr(leapCondition)
            if(not checkResult['result']):
                leapResult[runtime] = True
            else:
                leapResult[runtime] = checkResult['data']
        
        print(self.symbol + " Size of leap datas: " + str(len(leapResult)))
        return leapResult



    def createLeapCheckData(self, needData, startTime):
        print(self.symbol + " Create leap checking data " + str(self.accountImp.checkDataLeng))
        checkData = {}
        for symbol in needData:
            checkData[symbol] = {'kline': {}}
            for frame in needData[symbol]['kline']:
                symbolColName = "symbol"
                timeColName = "timestamp"
                startPointName = "is_close"
                collName = f"candle_{frame}"
                checkData[symbol]['kline'][frame] = []
                firstData = list(self.accountImp.klineModel.setCollection(collName).find({
                    symbolColName: self.symbol,
                    startPointName: 1,
                    timeColName : {"$lte": int(startTime/1000)}
                }).sort(timeColName, DESCENDING).limit(1))
                
           
                if(not isset(firstData, 0)): continue
                firstData = firstData[0]
                checkData[symbol]['kline'][frame].insert(0,firstData)
                nextData = list(self.accountImp.klineModel.setCollection(collName).find({
                    symbolColName: self.symbol,
                    startPointName: 1,
                    timeColName : {"$lt": int(firstData[timeColName])}
                }).sort(timeColName, DESCENDING).limit(self.accountImp.checkDataLeng))
               
                checkData[symbol]['kline'][frame] += nextData
                checkData[symbol]['kline'][frame].reverse()
                
        
        return checkData

    def canLeaping(self, runtime):
        isPending = self.checkEvent()
        if(isPending): return False
        leapLeng = self.leapLeng[self.shortestLeap]
        closeTime = ceil(runtime/leapLeng) * leapLeng - 1
        if(not isset(self.leapCheckResult, closeTime)): return False
        return not self.leapCheckResult[closeTime]


    #choice data functions
    def resetChoiceData(self):
        self.choiceData = {
            'symbol': self.symbol,
            'total_position': 0,
            'total_interval': 0,
            'profit': 0,
        }
    
    def getChoiceData(self, startTime):
        returnData = {}
        returnData['symbol'] = self.choiceData['symbol']
        returnData['profit'] = self.choiceData['profit']
        returnData['total_position'] = self.choiceData['total_position']
        totalPosition = self.choiceData['total_position']
        totalInterval = self.choiceData['total_interval']
        if(isset(self.event, 'lab_result_pending') and self.event.lab_result_pending == 1):
            totalPosition += 1
            if(startTime < self.event.lab_result_chart):
                totalInterval += self.runtime - self.event.lab_result_chart
            else:
                totalInterval += self.runtime - startTime
        if(totalPosition > 0):
            avgInterval = Round((totalInterval/totalPosition)/60000)
        else:
            avgInterval = 0
        returnData['avg_interval'] = avgInterval

        self.resetChoiceData()
        return returnData





        



    
            
            
