from math import floor
from multiprocessing import Process, Manager
import os
from Console.Helper.Telegram import Tele
from Console.Models.Coin_lab import LabCampaigns, LabResults, LabTrackBalance
from Console.Models.Wrappers.Lab.Coin_lab import LabAccountWrapper, LabCampaignsWrapper, LabEventLogsWrapper, LabResultsWrapper, LabTrackBalanceWrapper
from Console.Models.Wrappers.Lab.Lab_candle import LabCandle15MWrapper, LabCandle1DWrapper, LabCandle1HWrapper, LabCandle1MWrapper, LabCandle1WWrapper, LabCandle3MWrapper, LabCandle4HWrapper
from .CampaignImp import CampaignImp
from .CampaignImp1m import CampaignImp1m
from Console.Phoenix.AccountInterface import AccountInterface
from .function import *
from Console.Phoenix.Helper.function import *
from Console.Helper.Defaults import *
from time import time
from django import db


class AccountAsyncImp(AccountInterface):
    campaigns = []
    account = None #type: LabAccount
    rawRun = False

    #optimization result
    balance = 0
    marginBalance = 0
    maxUnrealize = 0
    maxInvest = 0
    totalPosition = 0
    totalInterval = 0
    maxInterval = 0
    avgInterval = 0
    pendingEvent = []
    strategies = {}
    
    def __init__(self, accountId, rawRun = False):
        #get account
        self.account = getAccount(accountId)
        self.account.lab_account_log = ''
        if(not self.account): raise Exception("Can not foud any account")
        self.checkDataLeng = 1
        
        if(self.account.lab_account_data_type is None):
            self.is1m = True
        else:
            self.is1m = self.account.lab_account_data_type == '1m'

        self.blockDataLeng = 30 if self.is1m else 2 #days
        self.rawRun = rawRun

    def initial(self, optiParams = {}):
        print("Start Lab in Async mode")

        if(not self.rawRun): self.startStatus()

        self.frameModels = {
            '1m': LabCandle1MWrapper(self.account.lab_account_db),
            '3m': LabCandle3MWrapper(self.account.lab_account_db),
            '15m': LabCandle15MWrapper(self.account.lab_account_db),
            '1h': LabCandle1HWrapper(self.account.lab_account_db),
            '4h': LabCandle4HWrapper(self.account.lab_account_db),
            '1d': LabCandle1DWrapper(self.account.lab_account_db),
            '1w': LabCandle1WWrapper(self.account.lab_account_db)
        }

        print("Get precision")
        getPrecision('')

        self.campaigns = LabCampaignsWrapper().filter(lab_campaign_account = self.account.lab_account_id).order_by("-" + LabCampaignsWrapper.lab_campaign_priority)
        print("Get all campain of account: " + str(len(self.campaigns)))

        #load param from account
        if(not self.rawRun):
            try:
                accountParam = self.account.lab_account_params
                accountParam = json.loads(accountParam)
                optiParams.update(accountParam)
            except Exception:
                pass

        self.campaignImps = {}
       
        campaign: LabCampaigns
        for campaign in self.campaigns: 
            campImp = CampaignImp1m(campaign, self) if self.is1m else CampaignImp(campaign, self)
            campImp.initial(optiParams)
            self.campaignImps[campaign.lab_campaign_id] = campImp

            #save strategy for optimization result
            if(not isset(self.strategies, campImp.campaign.lab_campaign_strategy)):
                self.strategies[campImp.campaign.lab_campaign_strategy] = campImp.cfgStrategy
                checkMatchPriceResult = checkMatchPrice(campImp.cfgStrategy)
                if(not checkMatchPriceResult['result']):
                    ms = Tele.TELE_ICON_WARNING + " LAB [" + self.account.lab_account_name + "] " + checkMatchPriceResult['message']
                    Tele.send(ms, Tele.TELE_SIMULATE_ERROR, Tele.TELE_BOT_DEFAULT)
                scanLeng = scanDataLeng(campImp.cfgStrategy)
                if(self.checkDataLeng < scanLeng): self.checkDataLeng = scanLeng
            
            campaign.lab_campaign_log = ''
            campaign.lab_campaign_running = 1
            campaign.lab_campaign_last = int(time())
            campaign.lab_campaign_status = '0,0'
            campaign.lab_campaign_runtime = None
           
        
    def createCheckData(self, needData, startTime):
        print("Create checking data")
        checkData = {}
        for symbol in needData:
            checkData[symbol] = {}
            for frame in needData[symbol]:
                symbolColName = "lab_candle_" + frame + "_symbol"
                timeColName = "lab_candle_" + frame + "_time"
                startPointName = "lab_candle_" + frame + "_startpoint"
                checkData[symbol][frame] = []
                firstData = self.frameModels[frame].filter({symbolColName: symbol, timeColName + "__lte": int(startTime)}).order_by("-"+timeColName)[:1].values()
                if(not isset(firstData, 0)): continue
                firstData = firstData[0]
                checkData[symbol][frame].insert(0,firstData)
                nextData = self.frameModels[frame].filter({
                    symbolColName: symbol, 
                    timeColName + "__lt": int(firstData[timeColName]),
                    startPointName: 1
                }).order_by("-"+timeColName)[:self.checkDataLeng].values()
                checkData[symbol][frame] += nextData
        return checkData

    def startStatus(self):
        #update status for all campain
        print("Update status for all campain")
        LabCampaignsWrapper().filter(lab_campaign_account = self.account.lab_account_id).update(
            lab_campaign_running = 1,
            lab_campaign_last = int(time()),
            lab_campaign_status = '0,0',
            lab_campaign_runtime = None,
            lab_campaign_log = '',
            
        )
        
        self.account.lab_account_running = 1
        self.account.save()

        print("Delete all old data of account")
        LabTrackBalanceWrapper().drop(lab_track_bl_account = self.account.lab_account_id)
        LabResultsWrapper().drop(lab_result_account = self.account.lab_account_id)

        

    def finishStatus(self, processed=0):
        self.account.lab_account_running = 0
        self.account.save()
        
    
    def start(self):

        manager = Manager()
        return_dict = manager.dict()
        
        blocks = []
        block = []
        for campaign in self.campaigns:
            block.append(campaign)
            if(len(block) == 20):
                blocks.append(block)
                block = []

        if(len(block) > 0): blocks.append(block)

        for blockCam in blocks:
            db.connections.close_all()
            threads = []
            for campaign in blockCam:
                thread = Process(target=self.run, args=[campaign, return_dict])
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()

        originBalance = self.account.lab_account_balance

        #update result from other process
        self.campaigns = []
        totalUnrealize = 0
        for camid in return_dict:
            returnValues = return_dict[camid]
            acc = returnValues['account'] #type: LabAccount
            profit = acc.lab_account_balance - originBalance
            self.account.lab_account_balance += profit

            self.campaigns.append(returnValues['campaign'])
            self.totalInterval += returnValues['totalInterval']
            self.totalPosition += returnValues['totalPosition']
            
            if(self.maxInterval < returnValues['maxInterval']): self.maxInterval = returnValues['maxInterval']

            camEvent = returnValues['event'] #type: LabResults
            if(not camEvent is None and camEvent.lab_result_pending == 1):
                self.pendingEvent.append(camEvent)
                if(camEvent.lab_result_matched_qty > 0):
                    eventProfit = camEvent.lab_result_profit * camEvent.lab_result_matched_price * camEvent.lab_result_matched_qty / 100
                    totalUnrealize += eventProfit

        self.balance = self.account.lab_account_balance
        self.marginBalance = self.balance + totalUnrealize
        if(self.totalPosition > 0): self.avgInterval = self.totalInterval/self.totalPosition
        
        if(not self.rawRun): 
            self.finishStatus()
            Tele.send("LAB [" + self.account.lab_account_name + "] Finished"
                + "\n- Balance: " + str(Round(self.balance, 3)) + " USDT"
                + "\n- Margin Balance: " + str(Round(self.marginBalance, 3)) + " USDT"
                + "\n- Closed Position: " + str(self.totalPosition)
                + "\n- Pending Position: " + str(len(self.pendingEvent))
                + "\n- Max Unrealize: " + str(Round(-self.maxUnrealize, 3)) + " %"
                + "\n- Max Invest: " + str(Round(self.maxInvest, 3)) + " %"
                + "\n- Max Interval: " + str(Round(self.maxInterval/60000)) + " minutes"
                + "\n- Avg Interval: " + str(Round(self.avgInterval/60000)) + " minutes",
            Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT)

    
    def run(self, campaign:LabCampaigns, returnDic):  

        print("Running " + str(campaign.lab_campaign_name))
        campaignImp = self.campaignImps[campaign.lab_campaign_id] #type: CampaignImp
        

        try:
       
            #intital start and stop time
            stopTime = Number(campaign.lab_campaign_stop) * 1000
            startTime = Number(campaign.lab_campaign_start) * 1000
            getDataStartTime = startTime
            getDataStopTime = getDataStartTime + self.blockDataLeng * 86400 * 1000
            if(getDataStopTime > stopTime): getDataStopTime = stopTime

            #cal total data leng
            totalData = 0
            mainSymbol = campaign.lab_campaign_symbol
            totalData = LabCandle1MWrapper().filter({
                LabCandle1MWrapper.lab_candle_1m_symbol: mainSymbol,
                LabCandle1MWrapper.lab_candle_1m_time + "__gte":startTime,
                LabCandle1MWrapper.lab_candle_1m_time + "__lte":stopTime 
            }).count()

            print("Total data " + str(mainSymbol) + ": " + str(totalData))

            speedTime = time()

            needSymbolByFrame = {}
            needData = campaignImp.needData
            for symbol in needData:
                needDataSym = needData[symbol]
                for frame in needDataSym:
                    if(not isset(needSymbolByFrame, frame)):
                        needSymbolByFrame[frame] = [symbol]
                    else:
                        needSymbolByFrame[frame].append(symbol)

            #create leap result. it depend on self.checkDataLeng
            if(self.account.lab_account_leap == 1): 
                campaignImp.leapCheckResult = campaignImp.createLeapCheckResult()

            checkData = self.createCheckData(needData, startTime)
        
            processed = 0
            breaker = False
            while processed < totalData:
                if(breaker): break
                indexData = {}

                if(getDataStartTime >= getDataStopTime): 
                    breaker = True
                    break

                for frame in needSymbolByFrame:
                    symbolColName = "lab_candle_" + frame + "_symbol"
                    timeColName = "lab_candle_" + frame + "_time"
                    print(f"Get block data {mainSymbol} " + frame + " from " + str(getDataStartTime) + " to " + str(getDataStopTime))
                    
                    frameData = self.frameModels[frame].filter({
                        symbolColName + "__in": needSymbolByFrame[frame],
                        timeColName + "__gt": getDataStartTime,
                        timeColName + "__lte": getDataStopTime
                    }).order_by(timeColName).values()
                    for data in frameData:
                        symbol = data[symbolColName]
                        if(not isset(indexData, symbol)): indexData[symbol] = {}
                        if(not isset(indexData[symbol], frame)): indexData[symbol][frame] = {}
                        indexData[symbol][frame][data[timeColName]] = data

                if(not isset(indexData, mainSymbol) or len(indexData[mainSymbol]['1m']) <= 0):
                    getDataStartTime = getDataStopTime
                    getDataStopTime = getDataStartTime + self.blockDataLeng * 86400 * 1000
                    if(getDataStopTime > stopTime): getDataStopTime = stopTime
                    continue

                longSymData = indexData[mainSymbol]['1m']
            
                for runtime in longSymData:
                    start_time = time() * 1000
                    getDataStartTime = runtime
                    processed += 1

                    #update data to check data
                    for symbol in needData:
                        needDataSym = needData[symbol]
                        lastData = {}
                        for frame in needDataSym:
                            if(isset(indexData, symbol) and isset(indexData[symbol][frame], runtime)):
                                lastData[frame] = indexData[symbol][frame][runtime]
                        if(len(lastData.keys()) > 0):
                            updateCheckData(checkData, symbol, lastData, self.checkDataLeng)
                    
                    if(self.account.lab_account_leap == 1):
                        if(campaignImp.canLeaping(int(runtime))): 
                            continue
            
                    campaignImp.setRun(checkData, runtime)
                    campaignImp.run()
                    checkResult = campaignImp.checkResult
                    if(not checkResult['result']): 
                        raise Exception(checkResult['message'])
                    
                    # extime = time() * 1000 - start_time
                    # print("Process time: " + str(extime) + " ms")
                    # if(extime > 10): exit()

                    if(processed % 2000 == 0):
                        campaign.lab_campaign_running = 1
                        campaign.lab_campaign_status = str(totalData) + ',' + str(processed)
                        campaign.lab_campaign_runtime = runtime

                        if(not self.rawRun):
                            campaign.save()
                            self.account.lab_account_running = 1
                            self.account.save()
                            

                        speed = floor(2000/(time() - speedTime))
                        print(f'Lab Speed : {mainSymbol} ' + str(speed) + " events/second" , end='\r')
                        speedTime = time()

                getDataStopTime = getDataStartTime + self.blockDataLeng * 86400 * 1000
                if(getDataStopTime > stopTime): getDataStopTime = stopTime

            campaign.lab_campaign_status = str(totalData) + ',' + str(processed)
            campaign.lab_campaign_running = 0
            campaign.lab_campaign_runtime = stopTime
            if(not self.rawRun): campaign.save()

            pendingEvent = campaignImp.event
            if(not pendingEvent is None and pendingEvent.lab_result_pending == 1):
                intervalTime = Number(campaignImp.frame1m[LabCandle1MWrapper.lab_candle_1m_time]) - Number(pendingEvent.lab_result_chart)
                if(campaignImp.maxInterval < intervalTime): campaignImp.maxInterval = intervalTime
                campaignImp.totalInterval += intervalTime
                campaignImp.totalPosition += 1
                if(not self.rawRun): LabResultsWrapper().save(pendingEvent)

            returnDic[campaign.lab_campaign_id] = {
                "account":self.account, 
                "campaign": campaign,
                "event": campaignImp.event,
                "totalPosition": campaignImp.totalPosition,
                "totalInterval": campaignImp.totalInterval,
                "maxInterval": campaignImp.maxInterval
            }
            
        except Exception as e:
            campaign.lab_campaign_running = 0
            campaign.lab_campaign_runtime = stopTime
            exInfo = exceptionInfo(e)
            ms = "LAB [" + str(campaign.lab_campaign_name) + "] Stopped. " + exInfo['message'] + ": " 
            ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
            campaign.lab_campaign_log = ms
            
            returnDic[campaign.lab_campaign_id] = {
                "account":self.account, 
                "campaign": campaign,
                "event": campaignImp.event,
                "totalPosition": campaignImp.totalPosition,
                "totalInterval": campaignImp.totalInterval,
                "maxInterval": campaignImp.maxInterval
            }

            if(not self.rawRun): 
                campaign.save()
                Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
                print(ms)

    __trackBalanceData = []
    def checkLiquidation(self, events, runtime):
        if(self.account.lab_account_margin_type == 'CROSS' or self.account.lab_account_track_balance == 1):
            totalUnrelize = 0
            totalInvest = 0
            totalBudget = 0
            campImp: CampaignImp
            for campImp in events:

                checkResult = campImp.checkResult
                if(not checkResult['result']): return checkResult
                if(not checkResult['data']): continue
                khung1m = campImp.frame1m #type: dict
                high = Number(khung1m[LabCandle1MWrapper.lab_candle_1m_high])
                low = Number(khung1m[LabCandle1MWrapper.lab_candle_1m_low])
                matchedQty = Number(campImp.event.lab_result_matched_qty)
                matchedPrice = Number(campImp.event.lab_result_matched_price)
                margin = Number(campImp.event.lab_result_margin)
                if(margin == 0): margin = 1
                budget = Number(campImp.event.lab_result_budget)
                
                invest = matchedQty * matchedPrice / margin
                if(campImp.event.lab_result_type == LabResultsWrapper.LAB_RESULT_TYPE_LONG):
                    worstPrice = low
                    loss = (matchedPrice - worstPrice) * matchedQty
                else:
                    worstPrice = high
                    loss = (high - matchedPrice) * matchedQty

                totalUnrelize += loss
                totalInvest += invest
                totalBudget += budget


            updatedAccount = self.account
            if(not self.rawRun):
                if(self.account.lab_account_track_balance == 1 and totalInvest > 0):
                    balance = Number(updatedAccount.lab_account_balance)
                    if(len(self.__trackBalanceData) > 1000):
                        LabTrackBalanceWrapper().bulk_create(self.__trackBalanceData)
                        self.__trackBalanceData = []
                    else:
                        self.__trackBalanceData.append(LabTrackBalance(
                            **{
                                LabTrackBalanceWrapper.lab_track_bl_time: runtime,
                                LabTrackBalanceWrapper.lab_track_bl_account: updatedAccount.lab_account_id,
                                LabTrackBalanceWrapper.lab_track_bl_margin_bl: balance - totalUnrelize,
                                LabTrackBalanceWrapper.lab_track_bl_invest: totalInvest,
                                LabTrackBalanceWrapper.lab_track_bl_balance: balance,
                                LabTrackBalanceWrapper.lab_track_bl_unrealize: -totalUnrelize
                            }
                        ))

            if(self.account.lab_account_margin_type == 'CROSS' and totalInvest > 0):
                
                balance = Number(updatedAccount.lab_account_balance)
                if(totalUnrelize > (balance * 90/100)):
                    if(not self.rawRun):
                        Tele.send(Tele.TELE_ICON_WARNING + "LAB [" + self.account.lab_account_name + "] liquidation"
                        + "\n Balance: " + str(balance) + " USDT"
                        + "\n Unrealize: " + str(totalUnrelize) + "USDT",
                        LabCampaignsWrapper.TELE_SIMULATE_ERROR, LabCampaignsWrapper.TELE_BOT_DEFAULT)
                    self.account.lab_account_log = f"Liquidation balance: {str(Round(balance, 3))} unrealize: {str(Round(totalUnrelize, 3))}"
                    return Reply.make(True, 'Liquid', True)

        return Reply.make(True, 'Dont need to check', False)

    def updateProfit(self, profit):
        self.account.lab_account_balance += profit

    def countPosition(self):
        count = 0
        for campaignId in self.campaignImps:
            imp = self.campaignImps[campaignId] #type: CampaignImp
            event = imp.event #type: LabResults
            if(event is None): continue
            if(event.lab_result_pending == 0): continue
            if(event.lab_result_matched_qty == 0 and event.lab_result_status == LabResultsWrapper.LAB_RESULT_STATUS_ENTER_WAITTING): continue
            count +=1
        return count

    def countSlot(self, strategyId):
        count = 0
        for campaignId in self.campaignImps:
            imp = self.campaignImps[campaignId] #type: CampaignImp
            event = imp.event #type: LabResults
            if(event is None): continue
            if(event.lab_result_pending == 0): continue
            if(event.lab_result_matched_qty == 0 and event.lab_result_status == LabResultsWrapper.LAB_RESULT_STATUS_ENTER_WAITTING): continue
            if(event.lab_result_strategy != strategyId): continue
            count +=1
        return count

    def getWattingPosition(self):
        events = []
        for campaignId in self.campaignImps:
            imp = self.campaignImps[campaignId] #type: CampaignImp
            event = imp.event #type: LabResults
            if(event is None): continue
            if(event.lab_result_pending == 0): continue
            if(event.lab_result_matched_qty == 0 and event.lab_result_status == LabResultsWrapper.LAB_RESULT_STATUS_ENTER_WAITTING):
                events.append(event)
        return events

    def getWattingSlot(self, strategyId):
        events = []
        for campaignId in self.campaignImps:
            imp = self.campaignImps[campaignId] #type: CampaignImp
            event = imp.event #type: LabResults
            if(event is None): continue
            if(event.lab_result_pending == 0): continue
            if(event.lab_result_strategy != strategyId): continue
            if(event.lab_result_matched_qty == 0 and event.lab_result_status == LabResultsWrapper.LAB_RESULT_STATUS_ENTER_WAITTING):
                events.append(event)
        return events



        
    

                
               






            



        

