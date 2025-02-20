
# Create your views here.
from django.http import HttpResponse, JsonResponse
from ..Helper.Defaults import *
from ..Helper.Reply import Reply
from django.contrib.auth.models import User


def getUser(request):
    user = request.user #type: User
    if(not user.is_authenticated): return JsonResponse(Reply.make(False, "User is not authenticated"))
    data = {
        'name': user.username,
        'email': user.email,
    }
    return JsonResponse(Reply.make(True, 'Authenticated', data))
