import os
import shlex
import shutil
import subprocess
import sys

# Create your views here.
from django.http import JsonResponse
from api.Helper.Defaults import *
from api.Helper.Reply import Reply
from api.Helper.System import System

from crypto_lab.settings import WORK_DIR
from api.Helper.Jwt import Jwtoken
from api.Models.Wrappers.coin_lab import LabAccountWrapper
from api.Models.coin_lab import LabAccount


def resource_limited_prefix():
    cpuset = os.getenv("LAB_BACKTEST_CPUSET", "8-11").strip()
    nice = os.getenv("LAB_BACKTEST_NICE", "10").strip()
    parts = []
    if cpuset:
        parts.append(f"taskset -c {shlex.quote(cpuset)}")
    if nice:
        parts.append(f"nice -n {shlex.quote(nice)}")
    return " ".join(parts) + (" " if parts else "")

def start(request):
    token = request.GET["token"]
    payload = Jwtoken.getPayload(token)
    return JsonResponse(_start(payload))

    
def _start(payload):

    id = get(payload, "id", None)
    if id is None:
        return Reply.make(False, "ID is not existed")
    isContinue = get(payload, "continue", False)

    if(System.isComplied()):
        cmd = f"{WORK_DIR}/phoenix_optimization lab_account {id} --tail"
    else:
        # sys.executable: đúng Python đang chạy lab_client (đủ dependency),
        # thay cho "python" trần vốn trỏ sang interpreter khác trên máy.
        cmd = f"{sys.executable} {WORK_DIR}/manage.py lab_account {id} --tail"

    cmd = resource_limited_prefix() + cmd
    if isContinue:
        cmd += " --continue"
    os.makedirs(f"{WORK_DIR}/logs", exist_ok=True)
    cmd += f" > {WORK_DIR}/logs/py_lab_account_{id}.log 2>&1 &"

    os.system('pkill -f "lab_account ' + str(id) + ' "')
    os.system(cmd)
    return Reply.make(True, "Success")

def checkData(request):
    token = request.GET["token"]
    payload = Jwtoken.getPayload(token)
    return JsonResponse(_checkData(payload))

def _checkData(payload):
    # if(System.isComplied()):
    #     cmd = f"{WORK_DIR}/phoenix_optimization check_data"
    # else:
    print(payload)
    database = get(payload, "database", None)
    cmd = f"python /home/ubuntu/ftx/coin_crawler/manage.py check_data {database}"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result, err = process.communicate()
    # print(result.decode("utf-8"))
    return Reply.make(True, "Success", result.decode("utf-8").strip())

def stop(request):
    token = request.GET["token"]
    payload = Jwtoken.getPayload(token)
    return JsonResponse(_stop(payload))

def _stop(payload):

    id = get(payload, "id", None)
    if id is None:
        return Reply.make(False, "ID is not existed")
        
    account = LabAccountWrapper().get({LabAccountWrapper.lab_account_id: id})#type: LabAccount
    os.system('pkill -f "lab_account ' + str(id) + ' "')
    tempFolder = f"{WORK_DIR}/tmp/phoenix_opti_cache/tempFolder_0_{account.lab_account_id}"
    shutil.rmtree(tempFolder, True)
    return Reply.make(True, "Success")


def getStatus(request):
    token = request.GET["token"]
    payload = Jwtoken.getPayload(token)
    return JsonResponse(_getStatus(payload))

def _getStatus(payload):
    ids = get(payload, "ids", [])
    result = {}
    for id in ids:
        result[id] = System.isRunning("lab_account " + str(id) + " ")
    return Reply.make(True, "success", result)

def getLog(request):
    token = request.GET["token"]
    payload = Jwtoken.getPayload(token)
    return JsonResponse(_getLog(payload))
    

def _getLog(payload):
    id = get(payload, "id", None)
    if id is None:
        return Reply.make(False, "ID is not defined")
    fileName = f"{WORK_DIR}/logs/py_lab_account_{id}.log"
    if os.path.isfile(fileName):
        with open(fileName) as file:        
            log = file.read()
            return Reply.make(True, "success", log)
    else:
        return Reply.make(True, 'success', 'Log file does not exist')


