from pymongo import MongoClient
from crypto_lab.settings import DATABASES
from helper.Defaults import *

class mongoModel():
    connection = None
    collection = None
    database = None

    # 'ENGINE': 'djongo',
    #     'NAME': 'raw',
    #     'ENFORCE_SCHEMA': False,
    #     'CLIENT': {
    #         'host': '127.0.0.1',
    #         'port': 27017,
    #         'username': 'crawler',
    #         'password': 'crawler@1235',
    #         'authSource': 'raw',
    #         'authMechanism': 'SCRAM-SHA-1'
    #     }  
    
    def __init__(self, db='default', coll = None):
        self.db = db
        self.config = DATABASES[db]['CLIENT']
        self.connect()
        if(self.connection and not coll is None):
            self.setCollection(coll)


    def connect(self):
        params = {}
        params['host'] = self.config['host']
        params['port'] = get(self.config, 'port', 27017)

        if(isset(self.config, 'username')): params['username'] = self.config['username']
        if(isset(self.config, 'password')): params['password'] = self.config['password']
        if(isset(self.config, 'authSource')): params['authSource'] = self.config['authSource']
        if(isset(self.config, 'authMechanism')): params['authMechanism'] = self.config['authMechanism']

        database = DATABASES[self.db]['NAME']

        self.connection = MongoClient(**params)
        self.database = self.connection[database]

    def setCollection(self, coll):
        self.coll_name = coll
        self.collection = self.database[self.coll_name]
        return self


    def __getattr__(self, name):
        def function(*args, **options):
            fn = getattr(self.collection, name, None)
            if(callable(fn)): 
                return fn(*args, **options)
        return function