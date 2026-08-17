import json
import multiprocessing
import os
import shutil
import sys
from time import sleep, time

from django import db
from Console.Helper.Defaults import *
from Console.Models.Wrappers.Lab.Coin_lab import LabAccountWrapper, LabCampaignsWrapper, LabOptResultWrapper, LabOptimizationWrapper, LabResultsWrapper
from Console.Models.Coin_lab import LabAccount, LabOptResult, LabOptimization
from multiprocessing import Process, Manager, Lock, Array
from Console.Helper.Telegram import Tele

from .AccountAsyncImp import AccountAsyncImp
from .AccountImp import AccountImp
from crypto_lab.settings import WORK_DIR

class Optimization:
    def __init__(self, optiId, isContinue=False) -> None:
        self.optiId = optiId
        self.isContinue = isContinue


    def initial(self):
        self.opti = LabOptimizationWrapper().get({LabOptimizationWrapper.lab_opt_id: self.optiId}) #type: LabOptimization
        params = json.loads(self.opti.lab_opt_params)
        self.paramsList = [{}]
        for itemParams in params:
            self.paramsList = self.processParamsItem(self.paramsList, itemParams)

        self.totalParam = len(self.paramsList)
        self.processed = 0

        if(self.isContinue):
            self.paramsList = self.filterDoneParams(self.paramsList)
            #drop unfinished processed
            LabOptResultWrapper().drop({
                LabOptResultWrapper.lab_opt_result_optimization: self.optiId,
                LabOptResultWrapper.lab_opt_result_done: 0
            })
        else:
            #delete all old result
            LabOptResultWrapper().drop({
                LabOptResultWrapper.lab_opt_result_optimization: self.opti.lab_opt_id
            })

        manager = Manager()
        self.context = manager.dict()
        self.contextLock = Lock()


    def filterDoneParams(self, paramsList):
        unProcessed = []
        doneProcesses = LabOptResultWrapper().filter({
            LabOptResultWrapper.lab_opt_result_optimization: self.optiId,
            LabOptResultWrapper.lab_opt_result_done: 1
        })
        processedParams = []
        processDone: LabOptResult
        for processDone in doneProcesses:
            processedParams.append(json.loads(processDone.lab_opt_result_params))
        
        for param in paramsList:
            isProcess = False
            for processed in processedParams:
                if(self.compareObject(param, processed)):
                    isProcess = True
                    break
            if(not isProcess):
                unProcessed.append(param)
        self.totalParam = len(unProcessed) + len(processedParams)
        self.processed = len(processedParams)
        return unProcessed

    def compareObject(self, object1, object2):
        for key in object1:
            if(not isset(object2, key)): return False
            if(object2[key] != object1[key]): return False
        return True



    def processParamsItem(self, totalParams, itemParams):
        itemType = itemParams['type']
        itemDatas = itemParams['data']
        newTotalParam = []
        if(itemType == "INPUT"):
            for param in totalParams:
                for itemData in itemDatas:
                    value = self.calItem(itemData, param, itemParams['name'])
                    param.update({"#" + itemParams['name'] + "#": value})
                    newTotalParam.append({**param})
            return newTotalParam

        if(itemType == "SETS"):
            for param in totalParams:
                for itemData in itemDatas:
                    tempParam = {}
                    for key, val in enumerate(itemData):
                        value = self.calItem(val, param, itemParams['name'])
                        tempParam[f"#{itemParams['name']}[{key}]#"] = value
                    param.update(tempParam)
                    newTotalParam.append({**param})
            return newTotalParam

        if(itemType == "EXPRESSIONS"):
            for param in totalParams:
                itemData = itemParams['data']
                value = self.calItem(itemData, param, itemParams['name'])
                param.update({"#" + itemParams['name'] + "#": value})
                newTotalParam.append({**param})
            return newTotalParam

    def calItem(self, itemData, param, name):
        itemData = str(itemData)
        matcheds = re.findall(r"\#[^\#]+\#", itemData)
        for matched in matcheds:
            if(isset(param, matched)):
                itemData = itemData.replace(matched, str(param[matched]))
        check = re.search(r"\#[^\#]+\#", itemData)
        if(not check is None):
            raise Exception(f"Please define {check[0]} before {name}")
        value = str2num(itemData)
        return value

    def start(self):
        self.account = LabAccountWrapper().get({LabAccountWrapper.lab_account_id: self.opti.lab_opt_account}) #type: LabAccount
        self.opti.lab_opt_start_time = int(time())
        self.opti.lab_opt_stop_time = None
        self.opti.save()

        from helper.ResourceGuard import ResourceGuard
        safe_thread_count = ResourceGuard.get_safe_worker_count(self.opti.lab_opt_thread)
        blockLeng = safe_thread_count

        if self.account.lab_account_sync == 0:
            numberOfCamp = LabCampaignsWrapper().filter({LabCampaignsWrapper.lab_campaign_account: self.opti.lab_opt_account}).count()
            if(numberOfCamp >= 20):
                blockLeng = 1
            else:
                blockLeng = min(safe_thread_count, max(1, int(20/numberOfCamp)))

        for param in self.paramsList:
            block.append(param)
            if(len(block) == blockLeng):
                blocks.append(block)
                block = []

        if(len(block) > 0): blocks.append(block)
        
        for blockParms in blocks:
            # Kiểm tra RAM khả dụng trước khi kích hoạt block mới
            is_safe, msg = ResourceGuard.is_safe_to_run(min_available_gb=2.5)
            if not is_safe:
                sleep(2) # Tạm dừng 2s để bộ nhớ hồi phục
                ResourceGuard.cleanup_memory()

            self.opti.lab_opt_log = f"Processing block {str(len(blockParms))} sets of params (Max workers: {blockLeng})"
            self.opti.lab_opt_processed = f"{self.totalParam},{self.processed}"
            self.opti.save()

            db.connections.close_all()
            threads = []
            for param in blockParms:
                thread = Process(target=self.run, args=[param, self.context, self.contextLock], daemon=True)
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()
                self.processed += 1
                self.opti.lab_opt_processed = f"{self.totalParam},{self.processed}"
                self.opti.save()

            ResourceGuard.cleanup_memory()

        self.opti.lab_opt_stop_time = int(time())
        self.opti.save()
        #delete temp folder if exist
        tempFolder = f"{WORK_DIR}/tmp/phoenix_opti_cache/tempFolder_{str(self.optiId)}_{str(self.account.lab_account_id)}"
        shutil.rmtree(tempFolder, True)
        Tele.send(f"{Tele.TELE_ICON_TAKEPROFIT} OPTIMIZATION [{self.opti.lab_opt_name}] Completed", Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()

        
    def run(self, params, context:dict={}, lock=None):
        
        optiResult = LabOptResultWrapper().new({ 
            LabOptResultWrapper.lab_opt_result_optimization: self.opti.lab_opt_id,
            LabOptResultWrapper.lab_opt_result_params: json.dumps(params),
            LabOptResultWrapper.lab_opt_result_done: 0,
        }) #type: LabOptResult
        try:
            
            startPoint = time()

            accountImp = AccountImp(self.account.lab_account_id, True)
            #update result status before running
            
            optiResult.lab_opt_result_log = "Running..."
            optiResult.save()
            #run account instance
            accountImp.run(params, context, lock, self.optiId, self.opti.lab_opt_data_leng)

            #update result status after running
            accountResult = LabOptimizationWrapper().toDict(accountImp.account)
            pendingEventResult = list(map(LabOptimizationWrapper().toDict, accountImp.pendingEvent))
            campaignResult = list(map(LabOptimizationWrapper().toDict, accountImp.campaigns))
            optiResult.lab_opt_result_account = json.dumps(accountResult)
            optiResult.lab_opt_result_event = json.dumps(pendingEventResult)
            optiResult.lab_opt_result_campaign = json.dumps(campaignResult)
            optiResult.lab_opt_result_balance = json.dumps(accountImp.balance)
            optiResult.lab_opt_result_strategy = json.dumps(accountImp.strategies)
            optiResult.lab_opt_result_margin_balance = accountImp.marginBalance
            optiResult.lab_opt_result_total_position = accountImp.totalPosition
            optiResult.lab_opt_result_invest_max = accountImp.maxInvest
            optiResult.lab_opt_result_unrelize_max = -accountImp.maxUnrealize
            optiResult.lab_opt_result_interval_avg = accountImp.avgInterval
            optiResult.lab_opt_result_interval_max = accountImp.maxInterval
            optiResult.lab_opt_result_total_long = accountImp.totalLong
            optiResult.lab_opt_result_total_short = accountImp.totalShort
            optiResult.lab_opt_result_total_stoploss = accountImp.totalStoploss
            optiResult.lab_opt_result_total_takeprofit = accountImp.totalTakeprofit
            optiResult.lab_opt_result_log = "Total Time: " + str(time() - startPoint) + " seconds"
            optiResult.lab_opt_result_done = 1
            try:
                optiResult.save()
            except Exception as e:
                sleep(3)
                print('==========================')
                print(LabOptimizationWrapper().toDict(optiResult))
                optiResult.save()


        except Exception as e:
            print(e)
            exInfo = exceptionInfo(e)
            ms = "Optimization [" + str(self.opti.lab_opt_name) + "] got the error. " + exInfo['message'] + ": " 
            ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
            Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
            optiResult.lab_opt_result_log = ms
            optiResult.save()
            print(ms)


                        


                



