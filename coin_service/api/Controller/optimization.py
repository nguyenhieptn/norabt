import os
import shutil

# Create your views here.
from django.http import JsonResponse
from api.Helper.Defaults import *
from api.Helper.Reply import Reply
from api.Helper.System import System

from crypto_lab.settings import WORK_DIR
from api.Helper.Jwt import Jwtoken
from api.Models.coin_lab import LabOptimization
from api.Models.Wrappers.coin_lab import LabOptimizationWrapper

def start(request):
    token = request.GET['token']
    payload = Jwtoken.getPayload(token)
    return JsonResponse(_start(payload))

def _start(payload):
    id = get(payload, 'id', None)
    if(id is None):
        return Reply.make(False, 'ID is not existed')
    isContinue = get(payload, 'continue', False)

    if(System.isComplied()):
        cmd = f"{WORK_DIR}/phoenix_optimization lab_optimization {id} --tail"
    else:
        cmd = f"python {WORK_DIR}/manage.py lab_optimization {id} --tail"

    if(isContinue):
        cmd += " --continue"
    cmd += f" > {WORK_DIR}/logs/py_lab_optimization_{id}.log 2>&1 &"
    os.system('pkill -f "lab_optimization '+str(id)+' "')
    os.system(cmd)
    return Reply.make(True, 'Success', cmd)


def stop(request):
    token = request.GET['token']
    payload = Jwtoken.getPayload(token)
    return JsonResponse(_stop(payload))

def _stop(payload):
    id = get(payload, 'id', None)
    if(id is None):
        return Reply.make(False, 'ID is not existed')
    opt = LabOptimizationWrapper().get({LabOptimizationWrapper.lab_opt_id: id}) #type: LabOptimization
    os.system('pkill -f "lab_optimization '+str(id)+' "')
    tempFolder = f"{WORK_DIR}/tmp/phoenix_opti_cache/tempFolder_{id}_{opt.lab_opt_account}"
    shutil.rmtree(tempFolder, True)
    return Reply.make(True, 'Success')

def getStatus(request):
    token = request.GET['token']
    payload = Jwtoken.getPayload(token)
    return JsonResponse(_getStatus(payload))

def _getStatus(payload):
    ids = get(payload, 'ids', [])
    result = {}
    for id in ids:
        result[id] = System.isRunning('lab_optimization '+str(id)+' ')
    return Reply.make(True, 'success', result)

def getLog(request):
    token = request.GET['token']
    payload = Jwtoken.getPayload(token)
    return JsonResponse(_getLog(payload))

def _getLog(payload):
    id = get(payload, 'id', None)
    if(id is None): return Reply.make(False, 'ID is not defined')
    fileName = f"{WORK_DIR}/logs/py_lab_optimization_{id}.log"
    if(os.path.isfile(fileName)):
        file = open(fileName, 'r')
        log = file.read()
        return Reply.make(True, 'success', log)
    else:
        return Reply.make(True, 'success', 'Log file does not exist')
