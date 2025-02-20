
# Create your views here.
from django.http import HttpResponse, JsonResponse
import psutil

from models.Wrappers.nora_monitor_wrapper import ScraperCoinWrapper
from models.nora_monitor import ScraperCoin
from ..Helper.Defaults import *
from ..Helper.Reply import Reply
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

@login_required
def add(request):
    data = input(request, 'data', None)
    if(data is None):return JsonResponse(Reply.make(False, "No data"))
    instance = ScraperCoinWrapper().new(data) #type: ScraperCoin
    instance.save()
    return JsonResponse(Reply.make(True, 'Successed', ScraperCoinWrapper().toDict(instance)),json_dumps_params={'default':str})

@login_required
def adds(request):
    data = input(request, 'data', None)
    if(data is None): return JsonResponse(Reply.make(False, "No data"))
    instances = []
    for addData in data:
        instances.append(ScraperCoinWrapper().new(addData))
    ScraperCoinWrapper().bulk_create(instances)
    return JsonResponse(Reply.make(True, 'Successed'))

@login_required
def update(request):
    key = input(request, 'key', None)
    if(key is None): return JsonResponse(Reply.make(False, "Please define Key"))
    value = input(request, 'value', None)
    if(key is None): Reply.make(False, "Please define value")
    result = ScraperCoinWrapper().edit(key, value)
    return JsonResponse(Reply.make(True, 'Successed', result),json_dumps_params={'default':str})

@login_required
def read(request):
    filter = input(request, 'filter', None)
    skip = Number(input(request, 'skip', 0))
    limit = Number(input(request, 'limit', 10000))
    if(limit > 10000): limit = 10000
    order_by = input(request, 'order_by', None)
    select = input(request, 'select', None)
    model = ScraperCoinWrapper().all()
    if(filter is not None):model = model.filter(**filter)
    if(order_by is not None):model = model.order_by(order_by)
    if(select is not None):
        result = model[skip:limit+skip].values(*select)
    else:
        result = model[skip:limit+skip].values()

    return JsonResponse(Reply.make(True, "success", list(result)),json_dumps_params={'default':str})


@login_required
def filter(request):
    filter = input(request, 'filter', None)
    exclude = input(request, 'exclude', None)
    skip = Number(input(request, 'skip', 0))
    limit = Number(input(request, 'limit', 10000))
    if(limit > 10000): limit = 10000
    order_by = input(request, 'order_by', None)
    select = input(request, 'select', None)
    model = ScraperCoinWrapper().all()
    if(filter is not None):model = model.filter(**filter)
    if(exclude is not None):model = model.exclude(**exclude)
    totalQty = model.count()
    if(order_by is not None):model = model.order_by(order_by)
    if(select is not None):
        result = model[skip:limit+skip].values(*select)
    else:
        result = model[skip:limit+skip].values()

    return JsonResponse(Reply.make(True, "success", {
        'data': list(result),
        'total': totalQty
    }),json_dumps_params={'default':str})


@login_required
def delete(request):
    
    pass

@login_required
def killprocess(request):
    
    pass


@login_required
def runprocess(request):
    pass