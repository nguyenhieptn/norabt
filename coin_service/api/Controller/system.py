import os
import re
from django.http import JsonResponse
from api.Helper.Defaults import Number, Round
from api.Helper.Reply import Reply
import psutil

from api.Helper.Jwt import Jwtoken

def getInfo(request):

    token = request.GET['token']
    payload = Jwtoken.getPayload(token)
    return JsonResponse(_getInfo(payload))

    
def _getInfo(payload):
    hdd = psutil.disk_usage('/')
    memory = psutil.virtual_memory()
    swap_memory = psutil.swap_memory()
    swap_percent = 0
    disk_percent = 0
    if(swap_memory.total > 0): swap_percent = str(Round(swap_memory.used * 100 / swap_memory.total))
    if(hdd.total > 0): disk_percent =  str(Round(hdd.used * 100 / hdd.total))
    data = {
        'cpu': str(Round(psutil.cpu_percent(3))),
        'ram': str(memory[2]),
        'swap': swap_percent,
        'disk': disk_percent,
        'total_ram': Round(memory[0]),
        'total_swap': Round(swap_memory.total),
        'total_cpu': psutil.cpu_count(),
        'total_disk': Round(hdd.total),
        'version': '2.0.1'
    }
    return Reply.make(True, 'success', data)


