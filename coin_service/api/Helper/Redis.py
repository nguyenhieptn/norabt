import json
import orjson
import redis

from Console.Helper.Defaults import Singleton

class Redis(metaclass=Singleton):
    
    def __init__(self, host="127.0.0.1", port=6379, db=0, password=None) -> None:
        self.r = redis.Redis(
            host=host,
            port=port,
            db=db,
            password= password 
        )
    
    def set(self, key, value, timeout=None):
        return self.r.set(key, value, timeout)

    def get(self, key, default=None):
        value = self.r.get(key)
        if(value is None): return default
        return value

    def mget(self, keys):
        values = self.r.mget(keys)
        return values
    
    def pubsub(self):
        return self.r.pubsub()

    def publish(self, channel, value):
        if(type(value) is not str or type(value) is not bytes):
            value = orjson.dumps(value)
        self.r.publish(channel, value)
    

    def __getattr__(self, name):
        def function(*args, **options):
            fn = getattr(self.r, name, None)
            if(callable(fn)): 
                return fn(*args, **options)
        return function

    