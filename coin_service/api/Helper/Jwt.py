from datetime import datetime, timedelta, timezone
from django.conf import settings
from .Defaults import *
import jwt


class Jwtoken:
    @staticmethod
    def getPayload(token):
        key = getattr(settings, "SECRET_KEY", "None")
        payload = jwt.decode(token, key, audience="phoenix_center", algorithms=["HS256"])
        return payload

    @staticmethod
    def getToken(payload={}):
        if(not isset(payload, 'exp')): payload["exp"] = datetime.now(tz=timezone.utc) + timedelta(seconds=10)
        if(not isset(payload, 'nbf')): payload["nbf"] = datetime.now(tz=timezone.utc)
        if(not isset(payload, 'iat')): payload["iat"] = datetime.now(tz=timezone.utc)
        if(not isset(payload, 'aud')): payload["aud"] = 'phoenix_center'

        key = getattr(settings, "SECRET_KEY", "None")
        token = jwt.encode(payload, key)
        return token
    
