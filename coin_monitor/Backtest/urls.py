import os
from django.http import HttpResponse, JsonResponse
from django.urls import include, path
from .Controller import *
from helper.Defaults import exceptionInfo
from helper.Reply import Reply

def processRoute(request, controller, method):
    
    try:
        controller = controller.capitalize() + 'Controller'
        if not controller in globals(): raise Exception(f"Can not find controller {controller}")
        module = globals()[controller]
        if(method[0] == '_'): raise Exception(f"Can not find any method {method} in {controller}")
        if(not hasattr(module, method)): raise Exception(f"Can not find any method {method} in {controller}")
        return getattr(module, method)(request)
    except Exception as e:
        exInfo = exceptionInfo(e)
        ms = exInfo['message'] + ": " 
        file = "File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
        return JsonResponse(Reply.make(False, ms , file))

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('<str:controller>/<str:method>', processRoute)
]


