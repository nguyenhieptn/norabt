import json
from Console.Helper.Defaults import *
from Console.Helper.Control import *
from Console.Helper.Reply import Reply
from Console.Models.Coin_lab import LabCampaigns, LabOrder, LabResults
from Console.Models.Wrappers.Lab.Coin_lab import LabAccountWrapper, LabEventLogsWrapper, LabOrderWrapper, LabResultsWrapper 
from .CampaignImp import CampaignImp
from .function import *
from ..Helper.function import *

class CampaignImp1m(CampaignImp):

    event = None #type: LabResults
    orders = []


    def run(self):
        
        isPending = self.checkEvent()

        if(isPending):
            #check event if it exist
            if(not self.validateMonitorData()):
                self.checkResult = Reply.make(True, 'Not enough data', False)
                return

            checkResult = self.monitorEvent()
            if(not checkResult['result']):
                self.checkResult = checkResult
                return
            if(checkResult['data']['pending']):
                self.checkResult = Reply.make(True, 'Mornitor Event', self.event.lab_result_matched_qty > 0)
            else:
                isPending = False

        if(not isPending):
            #check event if it exist
            if(not self.validateOrderData()):
                self.checkResult = Reply.make(True, 'Not enough data', False)
                return
            checkResult = self.checkOrder()
            if(not checkResult['result']):
                self.checkResult = checkResult
            else:
                if(not self.event is None and self.event.lab_result_pending == 1):
                    #retun pending 
                    self.checkResult = Reply.make(True, 'Check Order', self.event.lab_result_matched_qty > 0)
                else:
                    self.checkResult = Reply.make(True, 'Check Order', False)


    def wattingOrder(self, orderType, container, strategy, flow, flowName, reason = ''):
        condition = self.getMatchCondition(flowName, 0)
        #reset all local data
        self.maker = None
        self.maxOrderProfit = 0
        self.baseProfit = Number(get(condition, 'baseprofit', self.getFlowData(flowName, 'baseprofit')))
        self.matchedParamsPhase = None

        closePrice = Number(self.frame1m['close'])
        self.enterBase = closePrice

        btcwma1d = None
        btcwma1w = None
        if(isset(self.checkData, 'BTCUSDT')):
            if(isset(self.checkData['BTCUSDT'], '1d')): btcwma1d = round(get(self.checkData['BTCUSDT']['1d'][0], 'lab_candle_1d_rsi_wma', 0),3)
            if(isset(self.checkData['BTCUSDT'], '1w')): btcwma1w = round(get(self.checkData['BTCUSDT']['1w'][0], 'lab_candle_1w_rsi_wma', 0),3)

        
        rsi_4h = None
        rsi_1h = None
        rsi_4h_1 = None
        rsi_1h_1 = None
        if(isset(self.checkData[self.symbol], '4h')):
            if(isset(self.checkData[self.symbol]['4h'], 0)): rsi_4h = Round(get(self.checkData[self.symbol]['4h'][0], 'lab_candle_4h_rsi14', 0), 3)
            if(isset(self.checkData[self.symbol]['4h'], 1)): rsi_4h_1 = Round(get(self.checkData[self.symbol]['4h'][1], 'lab_candle_4h_rsi14', 0), 3)
        if(isset(self.checkData[self.symbol], '1h')):
            if(isset(self.checkData[self.symbol]['1h'], 0)): rsi_1h = Round(get(self.checkData[self.symbol]['1h'][0], 'lab_candle_1h_rsi14', 0), 3)
            if(isset(self.checkData[self.symbol]['1h'], 1)): rsi_1h_1 = Round(get(self.checkData[self.symbol]['1h'][1], 'lab_candle_1h_rsi14', 0), 3)
        
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
            LabResultsWrapper.lab_result_btc_wma45_1w: btcwma1w,
            LabResultsWrapper.lab_result_btc_wma45_1d: btcwma1d,
            LabResultsWrapper.lab_result_account: self.account.lab_account_id,
            LabResultsWrapper.lab_result_container: container,
            LabResultsWrapper.lab_result_matched_qty: 0,
            LabResultsWrapper.lab_result_matched_price: 0,
            LabResultsWrapper.lab_result_log: f"RSI4h:{str(rsi_4h)} RSI4h(-1):{str(rsi_4h_1)} RSI1h:{str(rsi_1h)} RSI1h(-1):{str(rsi_1h_1)}"
        }

        self.event=LabResults(**addData)
        if(not self.rawRun): LabResultsWrapper().save(self.event)
        self.event.lab_result_patr = self.getPATR()
        self.orders = []
        self.log("Check condition OK -> make order:" + str(closePrice))
        #skip waitting and go to step make order. match price is calculate in make order function.
        
        # makeOrderResult = self.makeOrder(closePrice, 0, self.runtime)
        # if(not makeOrderResult['result']): return makeOrderResult
        
        #continue monitor watting status
        return self.monitorEnterWaiting(flowName)

   
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
        else:   
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
                # print(f"freeSlot: {freeSlot}")
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
            return self.monitorPending(flowName)

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
            #get match price calculated
            matchPrice = Number(self.event.lab_result_order_price)
            
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

            commitPercent = 0.04 if isTaker else 0.02
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

        cfgBackprofitBaseon = self.getFlowData(flowName, 'baseprofit_baseon')
        
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
        releasePrice = None
        finishPrice = None

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


            if (stoploss is not False): 
                stoploss = Number(stoploss)
                if(minProfitReal <= -stoploss):
                    editData = {
                        LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING,
                        LabResultsWrapper.lab_result_params: 'Profit <= ' + str(-stoploss)
                    }
                    finished = True
                    isTakeprofit = True
                    #calculate finished price
                    if (orderType == LabResultsWrapper.LAB_RESULT_TYPE_LONG) :
                        finishPrice = matchedPrice * (100 - stoploss)/100
                    else:
                        finishPrice = matchedPrice * (100 + stoploss)/100
            
            if (not finished and takeprofit is not False):
                takeprofit = Number(takeprofit)
                if(maxProfitReal >= takeprofit):
                    editData = {
                        LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING,
                        LabResultsWrapper.lab_result_params: 'Profit >= ' + str(takeprofit)
                    }
                    finished = True
                    isTakeprofit = True
                    #calculate finished price
                    if (orderType == LabResultsWrapper.LAB_RESULT_TYPE_LONG) :
                        finishPrice = matchedPrice * (100 + takeprofit)/100
                    else:
                        finishPrice = matchedPrice * (100 - takeprofit)/100
            
            
        #Check base profit
        if (not finished):

            # stepprofit = Number(get(condition, 'step_profit', self.getFlowData(flowName, 'step_profit')))
            # backprofit = Number(get(condition, 'back_profit', self.getFlowData(flowName, 'back_profit')))

            # if (maxProfit > self.maxOrderProfit):
            #     self.maxOrderProfit = maxProfit
            
            # if (stepprofit > 0 and self.maxOrderProfit > (self.baseProfit + stepprofit)) :
            #     self.baseProfit = self.baseProfit + floor((self.maxOrderProfit - self.baseProfit) / stepprofit) * stepprofit
            

            # if (self.baseProfit > 0 and self.maxOrderProfit > self.baseProfit and profit < self.baseProfit - backprofit) :
                
            #     editData = {
            #         LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING,
            #         LabResultsWrapper.lab_result_params: 'Profit <= Base profit (' + str(self.baseProfit) + ') - back Step Profit(' + str(backprofit) + ')'
            #     }
            #     finished = True

            #ignore step profit and backprofit

            cfgBaseProfit = Number(get(condition, 'baseprofit', self.getFlowData(flowName, 'baseprofit')))
            if(maxProfit >= cfgBaseProfit):
                finished = True
                #calculate finish price
                if (orderType == LabResultsWrapper.LAB_RESULT_TYPE_LONG) :
                    finishPrice = matchedPrice * (100 + cfgBaseProfit)/100
                else:
                    finishPrice = matchedPrice * (100 - cfgBaseProfit)/100

                editData = {
                    LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING,
                    LabResultsWrapper.lab_result_params: 'Profit >= Base profit (' + str(cfgBaseProfit) + ') : Stop Price(' + str(finishPrice) + ')'
                }


            
        

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

                        releasePriceFormula = get(stop, 'release_price', None)
                        if(releasePriceFormula is not None):
                            releasePrice = self.calculateElement(releasePriceFormula)

                        if (releasePercent < 100) :
                            qty = Number(self.event.lab_result_matched_qty)
                            releaseQty = qty * releasePercent / 100
                            pre = getPrecision(self.symbol)
                            if(isset(pre, 'quantity')):
                                preQty = pre['quantity']
                                releaseQty = Round(releaseQty * (10 ** preQty)) / 10 ** preQty
                        break
                    

        if (finished) :
            if (releaseIndex is None):
                self.log('matched -> stoppending eventprofit:' + str(self.event.lab_result_eventprofit) + " Close: " + str(closePrice) + " profit:" + str(self.event.lab_result_profit) + " lastprice:" + str(self.event.lab_result_last_price) + "high: "+str(self.frame1m['high']))
                editData[LabResultsWrapper.lab_result_status] = LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING
            else :
                self.log('matched -> releaseWatting eventprofit:' + str(self.event.lab_result_eventprofit) + " Close: " + str(closePrice) + " profit:" + str(self.event.lab_result_profit) + " lastprice:" + str(self.event.lab_result_last_price) + "high: "+str(self.frame1m['high']))
                releaseStatus = LabResultsWrapper.LAB_RESULT_STATUS_RELEASE_WAITTING if (releaseQty is not None and releaseQty < self.event.lab_result_matched_qty) else LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING
                editData[LabResultsWrapper.lab_result_status] = releaseStatus
                editData[LabResultsWrapper.lab_result_order_qty] = releaseQty
                self.releaseBase = profitReal
            

        
        editData[LabResultsWrapper.lab_result_baseprofit] = self.baseProfit
        editData[LabResultsWrapper.lab_result_profit] = profitReal
        
        self.updateEvent(editData, finished)

        #Logging if is enabled 
        if(not self.rawRun):
            if(isset(self.params, LabCampaignsWrapper.LAB_CAMPAIGN_PARAMS_LOG) and Number(self.params[LabCampaignsWrapper.LAB_CAMPAIGN_PARAMS_LOG]) == 1):
                LabEventLogsWrapper().create({
                    LabEventLogsWrapper.lab_elog_time: self.runtime,
                    LabEventLogsWrapper.lab_elog_campaign: self.campaign.lab_campaign_id,
                    LabEventLogsWrapper.lab_elog_symbol: self.symbol,
                    LabEventLogsWrapper.lab_elog_matched: orderType,
                    LabEventLogsWrapper.lab_elog_chart : self.frame1m['open_time'],
                    LabEventLogsWrapper.lab_elog_result : json.dumps({'Status': 'Stop Pending' if finished else 'Matched'}),
                })
        

        if (finished):
            if (isTakeprofit):
                self.labPendingStop = self.runtime + 0.25 * 1000
            else:
                self.labPendingStop = self.runtime + 0.5 * 1000
            #if stop go to pending
            if(self.event.lab_result_status == LabResultsWrapper.LAB_RESULT_STATUS_STOP_PENDING):
                return self.monitorStopPending(flowName, finishPrice)
            else:
                return self.monitorReleasePending(flowName, releasePrice)
            
            
        return Reply.make(True, 'Pending Event', {'continue': not finished, 'pending': True})
            
    def monitorStopPending(self, flowName, price = None):
    
        # if (self.runtime < self.labPendingStop) :
        #     return Reply.make(True, 'Pending Event', {'continue': False, 'pending': True})

        orderType = self.event.lab_result_type
        
        matchedPrice = Number(self.event.lab_result_matched_price)
        if(price is None): 
            price = Number(self.frame1m['close'])

        commitPercent = 0.04
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
            LabOrderWrapper.lab_order_account: self.account.lab_account_id,
            
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
            LabResultsWrapper.lab_result_interval: resultInterval

        }

        self.updateEvent(editData)

        #update period event. need to after update event
        self.labPendingTime = self.runtime
        self.periodEvent = self.event

        self.labPendingTime = self.runtime
        if(not self.rawRun):
            if(isset(self.params, LabCampaignsWrapper.LAB_CAMPAIGN_PARAMS_LOG) and Number(self.params[LabCampaignsWrapper.LAB_CAMPAIGN_PARAMS_LOG]) == 1):
                
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

                #skip watting and go to make order
                makeOrderResult = self.makeOrder(closePrice, afterPhase, self.runtime)
                if(not makeOrderResult['result']): return makeOrderResult
                self.monitorPending(flowName)

                # if (enterStep <= 0 and enterRule is None):
                #     self.makeOrder(closePrice, afterPhase, self.runtime)
                # else:
                #     #set enterbase and go to watting
                #     self.enterBase = closePrice

            return Reply.make(True, 'Pending', {'continue': False, 'pending': True})
            
        else :
            self.updateEvent({LabResultsWrapper.lab_result_status: LabResultsWrapper.LAB_RESULT_STATUS_MATCHED})
            return Reply.make(True, 'Pending', {'continue': False, 'pending': True})

    def monitorReleasePending(self, flowName, closePrice=None):
        
        self.log('Release pending close:' + str(self.frame1m['close']))
        #Delay
        if (self.runtime < self.labPendingStop):
            return Reply.make(True, 'Pending Event', {'continue': False, 'pending': True})
        
        matchedPrice = Number(self.event.lab_result_matched_price)
        orderType = self.event.lab_result_type
        nextPhase = Number(self.event.lab_result_order_phase)

        if(closePrice is None):
            closePrice = Number(self.frame1m['close'])

        commitPercent = 0.04
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
    
    def makeOrder(self, closePrice, phase, runtime):
        self.log('Make an order ' + str(closePrice))
        pre = getPrecision(self.symbol)
        self.maker = False
        type = self.event.lab_result_type
        flowName = self.getFlowName()
        condition = self.getMatchCondition(flowName, phase)

        enterPriceSetting = get(condition, 'enter_price', 'market')
        margin = Number(get(condition, 'margin', self.getFlowData(flowName, 'margin')))

        if(margin < Number(self.event.lab_result_margin)):
            return Reply.make(False, 'Can not reduce margin')
        
        # calculate match price and quatity
        matchPriceRule = get(condition, 'match_price', None)
        if(not matchPriceRule is None): 
            enterPrice = self.calculateMatchPrice(matchPriceRule)
        else:
            if (isNumeric(enterPriceSetting)):
                enterPrice = closePrice * enterPriceSetting / 100
            else :
                enterPrice = closePrice
        
        # if (isset(pre, 'tickSize')):
        #     enterPrice = Round(enterPrice / Number(pre['tickSize'])) * Number(pre['tickSize'])
        
        budget = self.getInvestBudget()
        enterPackage = self.calculateElement(get(condition, 'enter_package', 100))['data']
        phaseBudget = budget * enterPackage / 100
        qty = phaseBudget / enterPrice
        qty = qty * margin
        if(isset(pre, 'quantity')):
            preQty = Number(pre['quantity'])
            qty = Round(qty * (10 ** preQty)) / 10 ** preQty
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


    
    def calculateMatchPrice(self, matchPriceRule):
        enterPrice = self.calculateElement(matchPriceRule)
        if(not enterPrice['result']): return enterPrice
        enterPrice = enterPrice['data']

        if(not self.periodEvent is None):
            if(not self.periodEvent.lab_result_sell_time is None):
                if(self.runtime - self.periodEvent.lab_result_sell_time < 60000):
                    enterPrice = self.periodEvent.lab_result_sell_price

        #if enter price of of range of frame 1m then match price is low or high
        low = Number(self.frame1m['low'])
        high = Number(self.frame1m['high'])
        if(enterPrice > high): enterPrice = high
        if(enterPrice < low): enterPrice = low

        return enterPrice

    

    
            
            
