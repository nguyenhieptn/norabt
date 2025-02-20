import copy
from datetime import datetime
from math import ceil, floor
import os
from crypto_lab.settings import WORK_DIR

import orjson
import json
from Console.Helper.Telegram import Tele
from Console.Models.Coin_lab import LabCampaigns, LabResults, LabTrackBalance
from Console.Models.Wrappers.Lab.Coin_lab import LabAccountWrapper, LabCampaignsWrapper, LabEventLogsWrapper, LabResultsWrapper, LabTrackBalanceWrapper
from .CampaignImp import CampaignImp
from .CampaignImp1m import CampaignImp1m
from Console.Phoenix.AccountInterface import AccountInterface
from .function import *
from Console.Phoenix.Helper.function import *
from Console.Helper.Defaults import *
from time import time
from models.Mongo.KlineModel import KlineModel
from models.Mongo.BusdModel import BusdModel
from models.Mongo.OrderbookModel import OrderbookModel
from pymongo import ASCENDING, DESCENDING
import pandas as pd
class AccountImp(AccountInterface):
    campaigns = []
    account = None #type: LabAccount
    isOptimize = False
    blockDataLeng = None

    #optimization result
    balance = 0
    marginBalance = 0
    maxUnrealize = 0
    maxInvest = 0
    totalPosition = 0
    totalInterval = 0
    totalLong = 0
    totalShort = 0
    totalStoploss = 0
    totalTakeprofit = 0
    maxInterval = 0
    avgInterval = 0
    pendingEvent = []
    strategies = {}
    originBalance = 0

    #choice
    choiceCoinData = None

    def __init__(self, accountId, isOptimize = False):
        self.accountId = accountId
        self.isOptimize = isOptimize
        

        
    def initial(self, rawRun=False):
        
        self.checkDataLeng = 1

        #get account
        self.account = getAccount(self.accountId)
        self.account.lab_account_log = ''
        if(not self.account): raise Exception("Can not foud any account")
        print("Get account successuflly")

        self.originBalance = self.account.lab_account_balance

        # #create models
        # if(self.account.lab_account_db != 'backtest_data_1m'):
        #     print(f"Create model to get data: backtest_data")
        #     self.klineModel = KlineModel()
        #     self.busdModel = BusdModel()
        #     self.orderbookModel = OrderbookModel()
        # else:
        
        if(self.account.lab_account_db is None or self.account.lab_account_db == ''): self.account.lab_account_db = 'backtest_data'
        print(f"Create model to get data: {self.account.lab_account_db}")
        self.klineModel = KlineModel(self.account.lab_account_db)
        self.busdModel = BusdModel(self.account.lab_account_db)
        self.orderbookModel = OrderbookModel(self.account.lab_account_db)
            
        self.isLeap = self.account.lab_account_leap == 1
        print("Data type : " + str(self.account.lab_account_data_type))
        if(self.account.lab_account_data_type is None):
            self.is1m = True
        else:
            self.is1m = self.account.lab_account_data_type == '1m'

        if(self.blockDataLeng is None):
            self.blockDataLeng = self.account.lab_account_data_length
        if(self.blockDataLeng is None):
            self.blockDataLeng = 1 if self.is1m else 1 #days

        print(f"Start Lab in Sync mode. Block Data Leng {self.blockDataLeng} days")
        
        if(not rawRun):
            self.startStatus()

        print("Get precision")
        getPrecision('')

        #get all campaigns
        self.campaigns = LabCampaignsWrapper().filter(lab_campaign_account = self.account.lab_account_id).order_by("-" + LabCampaignsWrapper.lab_campaign_priority)
        print("Get all campain of account: " + str(len(self.campaigns)))

        self.startTime = None
        self.stopTime = None 
        self.longSym = None
        self.total = {}

        #load param from account
        if(not self.isOptimize):
            try:
                accountParam = self.account.lab_account_params
                accountParam = json.loads(accountParam)
                self.optiParams.update(accountParam)
            except Exception:
                pass

        #get the longest time range
        for campaign in self.campaigns:
            tempStartTime = int(campaign.lab_campaign_start) * 1000
            tempStopTime = int(campaign.lab_campaign_stop) * 1000
            if(self.startTime is None):
                self.startTime = tempStartTime
            else:
                if(tempStartTime < self.startTime): self.startTime = tempStartTime

            if(self.stopTime is None):
                self.stopTime = tempStopTime
            else:
                if(tempStopTime < self.stopTime): self.stopTime = tempStopTime
        
        print("Scan campaigns to find total events")
        longestData = 0
        for campaign in self.campaigns:
            #check total event
            symbol = campaign.lab_campaign_symbol
            if(not self.lock is None): self.lock.acquire()
            contextKey = f"count_{symbol}"
            if(isset(self.context, contextKey)):
                campaignTotal = self.context[contextKey]
            else:
                campaignTotal = self.klineModel.setCollection('candle_1m').count({
                    'symbol': symbol,
                    'timestamp': {"$gte":self.startTime/1000, '$lte':self.stopTime/1000},
                })
                self.context[contextKey] = campaignTotal

            if(not self.lock is None): self.lock.release()

            self.total[symbol] = campaignTotal
            if(longestData <= campaignTotal):
                self.longSym = symbol
                longestData = campaignTotal

        print(f"The longest symbol: {self.longSym} {longestData}")

    def createCampaignImps(self, strategyId=None, rawRun=False):
        print(f"Create Campaign implement with strategy: {strategyId}")

        self.campaignImps = {}
        self.campaignImpsBySymbol = {}
        self.totalNeedData = {}
        self.totalDependSymbol = {}
        self.totalDataColumns = {} # total required column need to query from database
        self.isBUSD = False
        self.isOrderBook = False
        
        campaign: LabCampaigns
        for campaign in self.campaigns: 

            campImp = CampaignImp1m(campaign, self) if self.is1m else CampaignImp(campaign, self)
            campImp.initial(self.optiParams, strategyId, rawRun)
           
            #save strategy for optimization result
            if(not isset(self.strategies, campImp.campaign.lab_campaign_strategy)):
                self.strategies[campImp.campaign.lab_campaign_strategy] = campImp.cfgStrategy
                checkMatchPriceResult = checkMatchPrice(campImp.cfgStrategy)
                if(not checkMatchPriceResult['result']):
                    ms = Tele.TELE_ICON_WARNING + " LAB [" + self.account.lab_account_name + "] " + checkMatchPriceResult['message']
                    Tele.send(ms, Tele.TELE_SIMULATE_ERROR, Tele.TELE_BOT_DEFAULT)
                scanLeng = scanDataLeng(campImp.cfgStrategy)
                if(self.checkDataLeng < scanLeng): self.checkDataLeng = scanLeng

            

            #create leap result. it depend on self.checkDataLeng
            if(self.isLeap): 
                campImp.leapCheckResult = campImp.createLeapCheckResult()
                

            campaign.lab_campaign_log = ''
            campaign.lab_campaign_running = 1
            campaign.lab_campaign_last = int(time())
            campaign.lab_campaign_status = '0,0'
            campaign.lab_campaign_runtime = None

            self.campaignImps[campaign.lab_campaign_id] = campImp
            self.campaignImpsBySymbol[campaign.lab_campaign_symbol] = campImp
            
            #calculate need data of all campaign
            needData = campImp.needData
            # print("Nic")
            # print(needData)
            for symbol in needData:
                if(not isset(self.totalNeedData, symbol)):
                    self.totalNeedData[symbol] = needData[symbol]
                else:
                    for frame in needData[symbol]:
                        max = needData[symbol][frame]
                        if(not isset(self.totalNeedData[symbol], frame)):
                            self.totalNeedData[symbol][frame] = max
                        else:
                            if(max < self.totalNeedData[symbol][frame]):
                                self.totalNeedData[symbol][frame] = max

            if(findStrategy(campImp.cfgStrategy, 'BUSD')): self.isBUSD = True
            if(findStrategy(campImp.cfgStrategy, 'OrderBook')): self.isOrderBook = True

            #calculate all depend symbols
            self.totalDependSymbol.update(campImp.dependSymbols)

            #calculate all require columns
            dataColumns = campImp.dataColumns
            print(dataColumns)
            for colType in dataColumns:
                if(not isset(self.totalDataColumns, colType)): self.totalDataColumns[colType] = {}
                self.totalDataColumns[colType].update(dataColumns[colType])


        

        print("Total require data:")
        print(self.totalNeedData)
        print("Total depend symbols:")
        print(self.totalDependSymbol)
        print("Total required columns")
        print(self.totalDataColumns)

    def createCheckData(self):
        if(not self.lock is None): self.lock.acquire()
        if(isset(self.context, 'createCheckDataResult')):
            self.checkData = copy.deepcopy(self.context['createCheckDataResult'])
        else:
            print("Create checking data " + str(self.checkDataLeng))
            self.checkData = {}
            for symbol in self.totalNeedData:
                self.checkData[symbol] = {
                    'kline': {},
                    'busd': [],
                    'orderbook': []
                }
                for frame in self.totalNeedData[symbol]:
                    collName = f"candle_{frame}"
                    self.checkData[symbol]['kline'][frame] = []
                    firstData = self.klineModel.setCollection(collName).find({
                        'symbol': symbol,
                        'timestamp': {"$lte": int(self.startTime/1000)}
                    }).sort('timestamp', DESCENDING).limit(1)
                    if(not isset(firstData, 0)): continue
                    firstData = firstData[0]
                    self.checkData[symbol]['kline'][frame].insert(0,firstData)
                    nextData = self.klineModel.setCollection(collName).find({
                        'symbol': symbol,
                        'timestamp': {"$lt": int(firstData['timestamp'])},
                        'is_close': 1
                    }).sort('timestamp', DESCENDING).limit(self.checkDataLeng)
                    self.checkData[symbol]['kline'][frame] += list(nextData)

                if(self.isBUSD):
                    busdData = self.busdModel.find({
                        'symbol': symbol,
                        'timestamp': {"$lte": int(self.startTime/1000)}
                    }, self.totalDataColumns['BUSD']).sort('timestamp', DESCENDING).limit(10)
                    self.checkData[symbol]['busd'] = list(busdData)

                if(self.isOrderBook):
                    orderbookData = self.orderbookModel.find({
                        'symbol': symbol,
                        'timestamp': {"$lte": int(self.startTime/1000)}
                    }, self.totalDataColumns['OrderBook']).sort('timestamp', DESCENDING).limit(10)
                    self.checkData[symbol]['orderbook'] = list(orderbookData)

            self.context['createCheckDataResult'] = copy.deepcopy(self.checkData)

        if(not self.lock is None): self.lock.release()

    def getData(self, startTime, stopTime):
      
        indexData = {}

        for symbol in self.totalNeedData:
            indexData[symbol] = {
                'kline': {},
                'busd': {},
                'orderbook': {}
            }
            for frame in self.totalNeedData[symbol]:
                indexData[symbol]['kline'][frame] = {}

                collName = f"candle_{frame}"
                # start_point = time()
                klineFrameData = list(self.klineModel.setCollection(collName).find({
                    'symbol': symbol,
                    'timestamp': {"$lte": stopTime, "$gte": startTime},
                }).sort('timestamp', ASCENDING))
                # print(f"Get Kline data: {time()-start_point}s: {len(klineFrameData)}")
                if(len(klineFrameData) > 0):
                    klineFramePandas = pd.DataFrame.from_dict(klineFrameData).drop(columns=['_id']).drop_duplicates(subset='timestamp', keep='last').set_index('timestamp')
                    indexData[symbol]['kline'][frame] = klineFramePandas.to_dict('index')
                    # print(f"Kline data to Pandas: {time()-start_point}s")

            if(self.isBUSD):
                # start_point = time()
                # print(f'{symbol}-{stopTime}-{startTime}')
                busdData = list(self.busdModel.find({
                    'symbol': symbol,
                    'timestamp': {"$lte": stopTime, "$gte": startTime},
                }, self.totalDataColumns['BUSD']).sort('timestamp', ASCENDING))
                # print(f"Get BUSD data: {time()-start_point}s: {len(busdData)}")
                if(len(busdData) > 0):
                    busdPandas = pd.DataFrame.from_dict(busdData).drop(columns=['_id']).drop_duplicates(subset='timestamp', keep='last').set_index('timestamp')
                    indexData[symbol]['busd'] = busdPandas.to_dict('index')
                    # print(f"BUSD data to Pandas: {time()-start_point}s")

            if(self.isOrderBook):
                orderbookData = list(self.orderbookModel.find({
                    'symbol': symbol,
                    'timestamp': {"$lte": stopTime, "$gte": startTime},
                }, self.totalDataColumns['OrderBook']).sort('timestamp', ASCENDING))
                if(len(klineFrameData) > 0):
                    orderbookPandas = pd.DataFrame.from_dict(orderbookData).drop_duplicates(subset='timestamp', keep='last').set_index('timestamp')
                    indexData[symbol]['orderbook'] = orderbookPandas.to_dict('index')

        return indexData
                


    def startStatus(self):
        #update status for all campain
        print("Update status for all campain")
        LabCampaignsWrapper().filter(lab_campaign_account = self.account.lab_account_id).update(
            lab_campaign_running = 1,
            lab_campaign_last = int(time()),
            lab_campaign_status = '0,0',
            lab_campaign_runtime = None,
            lab_campaign_log = ''
        )
    
        self.account.lab_account_running = 1
        self.account.save()

        print("Delete all old data of account")
        LabTrackBalanceWrapper().drop(lab_track_bl_account = self.account.lab_account_id)
        LabResultsWrapper().drop(lab_result_account = self.account.lab_account_id)
        for campaign in self.campaigns:
            LabEventLogsWrapper().drop(lab_elog_campaign=campaign.lab_campaign_id)

    def finishStatus(self):
        self.account.lab_account_running = 0
        self.account.save()

        print("Update status for all campain")
        for campaign in self.campaigns:
            campaign.save()

        for camId in self.campaignImps:
            event = self.campaignImps[camId].event #type: LabResults
            if(not event is None and event.lab_result_pending == 1):
                LabResultsWrapper().save(event)

        if(len(self.__trackBalanceData) > 0):
            LabTrackBalanceWrapper().bulk_create(self.__trackBalanceData)
    
    def run(self, optiParams = {}, context={}, lock=None, optiId=0, blockDataLeng=None):
        self.context = context
        self.lock = lock
        self.optiId = optiId
        self.optiParams = optiParams
        self.blockDataLeng = blockDataLeng
        
        self.runChoiceCoin()
        self.runMainStrategy()
    
    def runMainStrategy(self):
        print("=====Running Main Strategy....=====")
        self.initial(rawRun=self.isOptimize)
        self.createCampaignImps(None, self.isOptimize)

        processed = 0
        getDataStartTime = self.startTime
        getDataStopTime = getDataStartTime + self.blockDataLeng * 86400 * 1000
        if(getDataStopTime > self.stopTime): getDataStopTime = self.stopTime

        speedTime = time()

        needSymbolByFrame = {}
        for symbol in self.totalNeedData:
            needDataSym = self.totalNeedData[symbol]
            for frame in needDataSym:
                if(not isset(needSymbolByFrame, frame)):
                    needSymbolByFrame[frame] = [symbol]
                else:
                    needSymbolByFrame[frame].append(symbol)
        
        breaker = False
        
        self.createCheckData()
        
        #get choice period time
        choicePeriodTime = Number(self.account.lab_account_choice_period) * 24*60*60000
        
        while processed < self.total[self.longSym]:
            # print(f"{processed} < {self.total[self.longSym]}")
            if(breaker): break

            print("Get block data from " 
            + str(datetime.fromtimestamp(floor(getDataStartTime/1000))) 
            + " to " 
            + str(datetime.fromtimestamp(floor(getDataStopTime/1000))))
            
            if(getDataStartTime >= getDataStopTime): 
                breaker = True
                break

            #key to seach in context
            contexKey = f"indexData_{str(getDataStartTime)}_{str(getDataStopTime)}"
            tempFolder = f"{WORK_DIR}/tmp/phoenix_opti_cache/tempFolder_{str(self.optiId)}_{str(self.account.lab_account_id)}"
            tempFile = f"{tempFolder}/{contexKey}"

            if(not self.lock is None): self.lock.acquire()
            #if not isset data create new index data and save in contex
            if(os.path.isfile(tempFile)):
                if(not self.lock is None): self.lock.release()
                deepCpTime = time()
                try:
                    f = open(tempFile, 'rb')
                    indexData = json.load(f)
                    f.close()
                except Exception as e:
                    print(e)
                    f = open(tempFile, 'rb')
                    indexData = json.load(f)
                    f.close()

                print("Get data from cache file " + str(time()-deepCpTime) + " seconds")
                
            else:
                print("Query Database from " 
                    + str(datetime.fromtimestamp(floor(getDataStartTime/1000))) 
                    + " to " 
                    + str(datetime.fromtimestamp(floor(getDataStopTime/1000))))
                indexData = self.getData(int(getDataStartTime/1000) + 1, int(getDataStopTime/1000))

                if(self.isOptimize): 
                    deepCpTime = time()
                    os.umask(0)
                    os.makedirs(tempFolder, exist_ok=True, mode=0o777)
                    f = open(tempFile, 'w+')
                    json.dump(indexData, f)
                    f.close()
                    print("Save index data to file " + str(time()-deepCpTime) + " seconds")

                if(not self.lock is None): self.lock.release()


            if(not isset(indexData, self.longSym) or not isset(indexData[self.longSym]['kline'], '1m') or len(indexData[self.longSym]['kline']['1m']) <= 0):
                getDataStartTime = getDataStopTime
                getDataStopTime = getDataStartTime + self.blockDataLeng * 86400 * 1000
                if(getDataStopTime > self.stopTime): getDataStopTime = self.stopTime
                continue

            # longSymData = indexData[self.longSym]['kline']['1m']
            #get longest data 
            longSymData = []
            for symbol in indexData:
                if 'kline' in indexData[symbol]:
                    for frame in indexData[symbol]['kline']:
                        if(len(indexData[symbol]['kline'][frame]) > len(longSymData)): longSymData = indexData[symbol]['kline'][frame]
           
            for runtime in longSymData:
                runtimeInt = Number(runtime) * 1000
                if(breaker): break
                start_time = time() * 1000
                getDataStartTime = runtimeInt
                processed += 1
                activeSymbol = {}

                #update data to check data
                for symbol in self.totalNeedData:
                    needDataSym = self.totalNeedData[symbol]
                    lastData = {'kline':{}}
                    for frame in needDataSym:
                        if(isset(indexData, symbol) and isset(indexData[symbol]['kline'][frame], runtime)):
                            lastData['kline'][frame] = indexData[symbol]['kline'][frame][runtime]
                    if(self.isBUSD):
                        if(isset(indexData, symbol) and isset(indexData[symbol]['busd'], runtime)):
                            lastData['busd'] = indexData[symbol]['busd'][runtime]
                    if(self.isOrderBook):
                        if(isset(indexData, symbol) and isset(indexData[symbol]['orderbook'], runtime)):
                            lastData['orderbook'] = indexData[symbol]['orderbook'][runtime]
                    
                    if(len(lastData['kline'].keys()) > 0):
                        updateCheckData(self.checkData, symbol, lastData, self.checkDataLeng)
                        activeSymbol[symbol] = True
                        

                campaign: LabCampaigns
                pendingEvents = []
                activeCamps = []
                for campaign in self.campaigns:
                    campSym = campaign.lab_campaign_symbol
                    if(not isset(activeSymbol, campSym)): continue
                    proce = self.campaignImps[campaign.lab_campaign_id] #type: CampaignImp
                    if(not proce.active): continue

                    #check leap
                    if(self.isLeap):
                        if(proce.canLeaping(runtimeInt)): 
                            continue

                    #check choice coin
                    if(self.choiceCoinData is not None):
                        choiceTime = floor(runtimeInt/choicePeriodTime)*choicePeriodTime
                        if(isset(self.choiceCoinData, choiceTime)):
                            allowSymbol = self.choiceCoinData[choiceTime]['symbols']
                            if(campSym not in allowSymbol):
                                continue

                    proce = self.campaignImpsBySymbol[campSym] #type: CampaignImp
                    proce.setRun(self.checkData, runtimeInt)
                    proce.run()
                    checkResult = proce.checkResult
                    if(not checkResult['result']): 
                        campaign.lab_campaign_log = checkResult['message']
                        proce.active = False
                    activeCamps.append(proce.campaign.lab_campaign_id)
                    if(checkResult['data']): pendingEvents.append(proce)

                
                checkLiquid = self.checkLiquidation(pendingEvents, runtimeInt)
                if(not checkLiquid['result']): 
                    campaign.lab_campaign_log = checkLiquid['message']
                    breaker = True
                    break
                if(checkLiquid['data']): 
                    breaker = True
                    break

                # extime = time() * 1000 - start_time
                # print("Process time: " + str(extime) + " ms")
                # if(extime > 10): exit()
                
                if(processed % 2000 == 0):
                    keys = activeCamps
                    for campaign in self.campaigns:
                        campaign.lab_campaign_running = 1
                        campaign.lab_campaign_status = str(self.total[self.longSym]) + ',' + str(processed)
                        campaign.lab_campaign_runtime = runtimeInt

                    if(not self.isOptimize):
                        LabCampaignsWrapper().filter(lab_campaign_id__in = keys).update(
                            lab_campaign_running = 1,
                            lab_campaign_status = str(self.total[self.longSym]) + ',' + str(processed),
                            lab_campaign_runtime = runtimeInt
                        )
                        self.account.lab_account_running = 1
                        self.account.lab_account_log = "Running Main Strategy..."
                        self.account.save()

                    speed = floor(2000/(time() - speedTime))
                    print('Lab Speed : ' + str(speed) + " events/second" , end='\r')
                    speedTime = time()


            getDataStopTime = getDataStartTime + self.blockDataLeng * 86400 * 1000
            if(getDataStopTime > self.stopTime): getDataStopTime = self.stopTime

        #update status for all campaign
        for campaign in self.campaigns:
            campaign.lab_campaign_running = 0
            campaign.lab_campaign_status = str(processed)+',' + str(self.total[self.longSym])
        
        #calculate optimization result
        self.balance = self.account.lab_account_balance
        for campaignId in self.campaignImps:
            campImp = self.campaignImps[campaignId] #type: CampaignImp
            campEvent = campImp.event 

            
            if(not campEvent is None and campEvent.lab_result_pending == 1):
                #update pending event time
                intervalTime = Number(campImp.frame1m['event_time']) - Number(campEvent.lab_result_chart)
                campEvent.lab_result_interval = intervalTime

                package = Number(campEvent.lab_result_budget)
                totalProfit = Number(campEvent.lab_result_eventprofit) + Number(campEvent.lab_result_profit)
                invest = Number(campEvent.lab_result_matched_qty) * Number(campEvent.lab_result_matched_price)

                campEvent.lab_result_realpnl = invest * totalProfit/100
                if(package > 0): campEvent.lab_result_realprofit = campEvent.lab_result_realpnl*100/package

                if(campImp.maxInterval < intervalTime): campImp.maxInterval = intervalTime
                campImp.totalInterval += intervalTime
                campImp.totalPosition += 1
                self.pendingEvent.append(campEvent)

            if(self.maxInterval < campImp.maxInterval): self.maxInterval = campImp.maxInterval
            self.totalPosition += campImp.totalPosition
            self.totalInterval += campImp.totalInterval
        if(self.totalPosition > 0): self.avgInterval = self.totalInterval/self.totalPosition
    
        if(not self.isOptimize):

            self.finishStatus()

            Tele.send("LAB [" + self.account.lab_account_name + "] Finished"
                + "\n- Origin Balance: " + str(Round(self.originBalance, 3)) + " USDT"
                + "\n- Balance: " + str(Round(self.balance, 3)) + " USDT"
                + "\n- Margin Balance: " + str(Round(self.marginBalance, 3)) + " USDT"
                + "\n- Close Position: " + str(self.totalPosition)
                + "\n- Take Profit: " + str(self.totalTakeprofit)
                + "\n- Stoploss: " + str(self.totalStoploss)
                + "\n- Pending Position: " + str(len(self.pendingEvent))
                + "\n- Max Unrealize: " + str(Round(-self.maxUnrealize, 3)) + " %"
                + "\n- Max Invest: " + str(Round(self.maxInvest, 3)) + " %"
                + "\n- Max Interval: " + str(Round(self.maxInterval/60000)) + " minutes"
                + "\n- Avg Interval: " + str(Round(self.avgInterval/60000)) + " minutes",
            Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT)

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
                high = Number(khung1m['high'])
                low = Number(khung1m['low'])
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

            #calculate optimization result
            balance = Number(self.account.lab_account_balance)
            percentInvest = totalInvest*100/balance
            percentUnrealize = totalUnrelize*100/balance
            if(percentInvest > self.maxInvest): self.maxInvest = percentInvest
            if(percentUnrealize > self.maxUnrealize): self.maxUnrealize = percentUnrealize
            self.marginBalance = balance - totalUnrelize

            updatedAccount = self.account
            if(not self.isOptimize):
                if(self.account.lab_account_track_balance == 1 and totalInvest > 0):
                    
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
                
                if(totalUnrelize > (balance * 90/100)):
                    print("Liquidation")
                    if(not self.isOptimize):
                        Tele.send(Tele.TELE_ICON_WARNING + "LAB [" + self.account.lab_account_name + "] liquidation"
                        + "\n Balance: " + str(balance) + " USDT"
                        + "\n Unrealize: " + str(totalUnrelize) + "USDT",
                        Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT)

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

# Choice functions

    # Run account with Choice strategy
    def runChoiceCoin(self):

        #check if Choice Strategy is set or not
        self.initial(rawRun=self.isOptimize)

        #clear choice result
        if(not self.isOptimize): 
            self.account.lab_account_choice_result = None
            self.account.save()

        if(self.account.lab_account_choice_strategy is None 
        or self.account.lab_account_choice_period is None
        or self.account.lab_account_choice_condition is None
        ):
            return

        print("=====Running Choice coin strategy...=====")
        
        self.createCampaignImps(self.account.lab_account_choice_strategy, True)
        self.createCheckData()

        choiceCoinCondition = json.loads(self.account.lab_account_choice_condition)

        processed = 0
        getDataStartTime = self.startTime
        getDataStopTime = getDataStartTime + self.blockDataLeng * 86400 * 1000
        if(getDataStopTime > self.stopTime): getDataStopTime = self.stopTime

        speedTime = time()

        needSymbolByFrame = {}
        for symbol in self.totalNeedData:
            needDataSym = self.totalNeedData[symbol]
            for frame in needDataSym:
                if(not isset(needSymbolByFrame, frame)):
                    needSymbolByFrame[frame] = [symbol]
                else:
                    needSymbolByFrame[frame].append(symbol)
        
        breaker = False
        periodTime = Number(self.account.lab_account_choice_period) * 24*60*60000
        choiceTime = None
        while processed < self.total[self.longSym]:
            if(breaker): break

            print("Get block data from " 
            + str(datetime.fromtimestamp(floor(getDataStartTime/1000))) 
            + " to " 
            + str(datetime.fromtimestamp(floor(getDataStopTime/1000))))

            if(getDataStartTime >= getDataStopTime): 
                breaker = True
                break

            #key to seach in context
            contexKey = f"indexData_{str(getDataStartTime)}_{str(getDataStopTime)}"
            tempFolder = f"{WORK_DIR}/tmp/phoenix_opti_cache/tempFolder_{str(self.optiId)}_{str(self.account.lab_account_id)}"
            tempFile = f"{tempFolder}/{contexKey}"

            if(not self.lock is None): self.lock.acquire()
            #if not isset data create new index data and save in contex
            if(os.path.isfile(tempFile)):
                if(not self.lock is None): self.lock.release()
                deepCpTime = time()
                try:
                    f = open(tempFile, 'rb')
                    indexData = orjson.loads(f.read())
                    f.close()
                except Exception as e:
                    print(e)
                    f = open(tempFile, 'rb')
                    indexData = orjson.loads(f.read())
                    f.close()

                print("Get data from cache file " + str(time()-deepCpTime) + " seconds")
                
            else:
                deepCpTime = time()
                indexData = {}
                for frame in needSymbolByFrame:
                    symbolColName = "lab_candle_" + frame + "_symbol"
                    timeColName = "lab_candle_" + frame + "_time"

                    print("Query Database " + frame + " from " 
                    + str(datetime.fromtimestamp(floor(getDataStartTime/1000))) 
                    + " to " 
                    + str(datetime.fromtimestamp(floor(getDataStopTime/1000))))

                    indexData = self.getData(int(getDataStartTime/1000) + 1, int(getDataStopTime/1000))
                    
                print("Get data from Database " + str(time()-deepCpTime) + " seconds")

                #cache data for main strategy
                deepCpTime = time()
                os.umask(0)
                os.makedirs(tempFolder, exist_ok=True, mode=0o777)
                f = open(tempFile, 'w+')
                json.dump(indexData, f)
                f.close()
                print("Save index data to file " + str(time()-deepCpTime) + " seconds")

                if(not self.lock is None): self.lock.release()


            if(not isset(indexData, self.longSym) or not isset(indexData[self.longSym]['kline'], '1m') or len(indexData[self.longSym]['kline']['1m']) <= 0):
                getDataStartTime = getDataStopTime
                getDataStopTime = getDataStartTime + self.blockDataLeng * 86400 * 1000
                if(getDataStopTime > self.stopTime): getDataStopTime = self.stopTime
                continue

            longSymData = indexData[self.longSym]['kline']['1m']
           
            for runtime in longSymData:
                runtimeInt = Number(runtime)
                if(breaker): break

                #create choice time
                if(choiceTime is None):
                    choiceTime = ceil(runtimeInt/periodTime)*periodTime

                start_time = time() * 1000
                getDataStartTime = runtimeInt
                processed += 1
                activeSymbol = {}

                #update data to check data
                for symbol in self.totalNeedData:
                    needDataSym = self.totalNeedData[symbol]

                    lastData = {'kline':{}}
                    for frame in needDataSym:
                        if(isset(indexData, symbol) and isset(indexData[symbol]['kline'][frame], runtime)):
                            lastData['kline'][frame] = indexData[symbol]['kline'][frame][runtime]
                    if(self.isBUSD):
                        if(isset(indexData, symbol) and isset(indexData[symbol]['busd'], runtime)):
                            lastData['busd'] = indexData[symbol]['busd'][runtime]
                    if(self.isOrderBook):
                        if(isset(indexData, symbol) and isset(indexData[symbol]['orderbook'], runtime)):
                            lastData['orderbook'] = indexData[symbol]['orderbook'][runtime]

                    if(len(lastData['kline'].keys()) > 0):
                        updateCheckData(self.checkData, symbol, lastData, self.checkDataLeng)
                        activeSymbol[symbol] = True
                        

                campaign: LabCampaigns
                pendingEvents = []
                activeCamps = []
                for campaign in self.campaigns:
                    campSym = campaign.lab_campaign_symbol
                    if(not isset(activeSymbol, campSym)): continue
                    proce = self.campaignImps[campaign.lab_campaign_id] #type: CampaignImp
                    if(self.isLeap):
                        if(proce.canLeaping(runtimeInt)): 
                            continue
                    
                    proce = self.campaignImpsBySymbol[campSym] #type: CampaignImp
                    proce.setRun(self.checkData, runtimeInt)
                    proce.run()
                    checkResult = proce.checkResult
                    if(not checkResult['result']): 
                        campaign.lab_campaign_log = checkResult['message']
                        breaker = True
                        break
                    activeCamps.append(proce.campaign.lab_campaign_id)
                    if(checkResult['data']): pendingEvents.append(proce)

                #get data for choice coin result
                if(runtimeInt > choiceTime):
                    periodChoiceData = []
                    for campId in self.campaignImps:
                        campImp = self.campaignImps[campId] #type: CampaignImp
                        choiceData = campImp.getChoiceData(choiceTime - periodTime)
                        periodChoiceData.append(choiceData)

                    tempData = copy.deepcopy(periodChoiceData[0])
                    for name in tempData:
                        if(name == 'symbol'): continue
                        def shortItem(e): return e[name]
                        periodChoiceData.sort(key=shortItem, reverse=True)
                        index = 0
                        for data in periodChoiceData:
                            index += 1
                            data[name + '_index'] = index

                    filterResult = self.filterChoiceCoin(periodChoiceData, choiceTime, choiceCoinCondition)
                    if(not filterResult['result']): raise Exception(filterResult['message'])
                    choiceTime = ceil(runtimeInt/periodTime)*periodTime
                
                if(processed % 2000 == 0):
                    keys = activeCamps
        
                    if(not self.isOptimize):
                        LabCampaignsWrapper().filter(lab_campaign_id__in = keys).update(
                            lab_campaign_running = 1,
                            lab_campaign_status = str(self.total[self.longSym]) + ',' + str(processed),
                            lab_campaign_runtime = runtimeInt
                        )

                    speed = floor(2000/(time() - speedTime))
                    print('Lab Speed : ' + str(speed) + " events/second" , end='\r')
                    speedTime = time()

            getDataStopTime = getDataStartTime + self.blockDataLeng * 86400 * 1000
            if(getDataStopTime > self.stopTime): getDataStopTime = self.stopTime
        
        LabAccountWrapper().edit({
            LabAccountWrapper.lab_account_id: self.accountId
        }, {
            LabAccountWrapper.lab_account_choice_result : json.dumps(self.choiceCoinData)
        })

        

    def calculateChoiceItem(self, item, data):
        if(type(item) is str and isset(data, item)):
            return Reply.make(True, str(item), data[item])
        if(isNumeric(item)):
            return Reply.make(True, str(item), Number(item))
        return Reply.make(False, 'Does not support ' + str(item))

    def filterChoiceCoin(self, periodChoiceData, choiceTime, condition):
        symbols = []
        for data in periodChoiceData:
            compareResult = compareOr(condition, self.calculateChoiceItem, data)
            if(not compareResult['result']): return compareResult
            if(compareResult['data']):
                symbols.append(data['symbol'])

        if(self.choiceCoinData is None): self.choiceCoinData = {}
        self.choiceCoinData[choiceTime] = {
            'symbols': symbols,
            'data' : periodChoiceData,
        }

        return Reply.make(True, 'Success', symbols)






        



        
    

                
               






            



        

