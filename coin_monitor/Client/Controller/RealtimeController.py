
# Create your views here.
from django.http import HttpResponse, JsonResponse
from helper.Validate import Validate

from models.Wrappers.testnet_wrapper import TestnetAccountWrapper, TestnetCampaignWrapper
from nora_monitor.settings import BASE_DIR
from ..Helper.Defaults import *
from ..Helper.Reply import Reply
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from datetime import datetime
import os

ACCOUNT = {
    6: {
        'chart': 1
    },
    7: {
        'chart': 1
    },
    10: {
        'chart': 2
    },
    11: {
        'chart': 2
    },
    12: {
        'chart': 3
    },
    13: {
        'chart': 3
    },
    14: {
        'chart': 3
    }
}


@login_required
def getListAccount(request):
    accounts = list(TestnetAccountWrapper().filter({TestnetAccountWrapper.testnet_account_id + "__in": ACCOUNT.keys()}).values(TestnetAccountWrapper.testnet_account_name, TestnetAccountWrapper.testnet_account_id))
    return JsonResponse(Reply.make(True, 'success', accounts))

@login_required
def getListSymbol(request):
    symbols = list(TestnetCampaignWrapper().filter({TestnetCampaignWrapper.testnet_account + "__in": ACCOUNT.keys()}).values(TestnetCampaignWrapper.testnet_symbol).distinct())
    return JsonResponse(Reply.make(True, 'success', symbols))

@login_required
def updateChart(request):
    account = input(request, 'account', None)
    Validate.check_raise(account, Validate.INT)
    date = input(request, 'date')
    Validate.check_raise(date, '^\d{4}_\d{2}_\d{2}$')
    symbol = input(request, 'symbol')
    Validate.check_raise(symbol, '^\w+$')
    cmd = f"python {BASE_DIR}/manage.py realtime_chart -a{account} -d{date} -s{symbol} -t{ACCOUNT[account]['chart']}"
    os.system(cmd)
    return JsonResponse(Reply.make(True, 'success', cmd))

