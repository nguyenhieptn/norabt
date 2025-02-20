
# Create your views here.
from django.http import HttpResponse, JsonResponse
from helper.Validate import Validate

from models.Wrappers.backtest_wrapper import LabAccountWrapper, LabCampaignsWrapper
from nora_monitor.settings import BASE_DIR
from helper.Defaults import *
from helper.Reply import Reply
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from datetime import datetime
import os

ACCOUNT = {
    283: {
        'chart': 3
    },
    287: {
        'chart': 3
    },
    288: {
        'chart': 3
    },
    293: {
        'chart': 3
    },
    
}

USER = 13


def _getAccount():
    accounts = list(LabAccountWrapper().filter({LabAccountWrapper.lab_account_user: USER}).values(LabAccountWrapper.lab_account_id))
    
    returnAccount = {}
    for ac in accounts:
        returnAccount[ac['lab_account_id']] = {
            'chart': 3
        }
    
    returnAccount.update(ACCOUNT)
    return returnAccount

@login_required
def getListAccount(request):
    acc = _getAccount()
    accounts = list(LabAccountWrapper().filter({LabAccountWrapper.lab_account_id + "__in": acc.keys()}).values(LabAccountWrapper.lab_account_name, LabAccountWrapper.lab_account_id))
    return JsonResponse(Reply.make(True, 'success', accounts))

@login_required
def getListSymbol(request):
    acc = _getAccount()
    symbols = list(LabCampaignsWrapper().filter({LabCampaignsWrapper.lab_campaign_account + "__in": acc.keys()}).values(LabCampaignsWrapper.lab_campaign_symbol).distinct())
    return JsonResponse(Reply.make(True, 'success', symbols))

@login_required
def updateChart(request):
    account = input(request, 'account', None)
    Validate.check_raise(account, Validate.INT)
    date = input(request, 'date')
    Validate.check_raise(date, '^\d{4}_\d{2}_\d{2}$')
    symbol = input(request, 'symbol')
    Validate.check_raise(symbol, '^\w+$')
    acc = _getAccount()
    cmd = f"python {BASE_DIR}/manage.py backtest_chart -a{account} -d{date} -s{symbol} -t{acc[account]['chart']}"
    os.system(cmd)
    return JsonResponse(Reply.make(True, 'success', cmd))

@login_required
def getStatistic(request):
    account = input(request, 'account', None)
    Validate.check_raise(account, Validate.INT)
    symbol = input(request, 'symbol')
    Validate.check_raise(symbol, '^\w+$')
    cmd = f"python {BASE_DIR}/manage.py statistic_kline -a{account} -s{symbol}"
    os.system(cmd)
    return JsonResponse(Reply.make(True, 'success', f'statistic_{account}_{symbol}.csv'))

