from datetime import datetime
from os import stat
import subprocess
import sys
from dateutil import tz

from django.core.management.base import BaseCommand
from Backtest.Processors.klineProcessor import klineProcessor
from helper.Defaults import *
from helper.Data import *

from math import floor
from threading import Thread
from time import sleep, time
import orjson
from helper.Redis import Redis
from helper.Defaults import *
import pandas as pd
from pymongo import DESCENDING, ASCENDING


import pandas as pd

from models.Mongo.CandleModel import Candle_Model
from models.Mongo.BusdModel import BusdModel
from models.Mongo.OrderbookModel import Order_bookModel
from models.Mongo.MongoModel import MongoModel


VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'Move data oder 30 days to HDD database'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        # parser.add_argument("-db","--database", nargs='?', default=None, type=str)
        # parser.add_argument("-t","--type", nargs='?', default='all', type=str)
        pass

    def handle(self, *args, **options):
        self.ssdMongo = MongoModel('realtime_data_ssd')
        self.hddMongo = MongoModel('realtime_data_hdd')

        collectionBySymbol = []
        collections = list(self.ssdMongo.database.list_collection_names())
        collections.sort()

        lastDay = datetime.fromtimestamp(time() - 30*86400, tz=VN_TZ).strftime('%Y_%m_%d')
        print(lastDay)

        for collection in collections:
            
            rg = r"(?P<date>\d{4}_\d{2}_\d{2})_(?P<symbol>[^_]+)_.*"
            match_object = re.match(rg, collection)
            if(match_object is None): continue
            symbol = match_object.group('symbol')
            date = match_object.group('date')
            if(date > lastDay): continue
            collectionBySymbol.append({
                'date': date,
                'collection': collection
            })

        for coll in collectionBySymbol:
            self.moveColl(self.ssdMongo, self.hddMongo, coll['collection'])


    def moveColl(self, srcDb:MongoModel, dstDb:MongoModel, coll):
        print(f"Move {coll}")
        srcDb.setCollection(coll)
        dstDb.setCollection(coll)
        all_records = srcDb.collection.find()
        dstDb.collection.insert_many(all_records)
        print(f"Delete {coll} from src db")
        srcDb.collection.drop()


        

    




        


    





        
        
        
        

    
        
        





        

        

        







        

        


    