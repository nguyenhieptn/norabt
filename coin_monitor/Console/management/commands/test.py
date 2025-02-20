from datetime import datetime
from math import floor
import os

from django.core.management.base import BaseCommand
import requests
import json
from threading import Thread

from djongo import models

import eventlet
import socketio

from helper.Websocket import Websocket
from models.backtest_data import BacktestBusd
from models.Wrappers.backtestDataWrapper import BacktestBusdWrapper
from models.Mongo.AggTradeModel import AggTradeModel

class Command(BaseCommand):
    help = 'Crawl Kline data 1m'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
       

    def add_arguments(self, parser):
        # parser.add_argument("--symbols", nargs="*", default=None)
        pass

    
    def handle(self, *args, **options):
        data = AggTradeModel('raw_data').setCollection('2022_06_09_THETAUSDT_depth').collection.find({
                "s": "THETAUSDT", 
                "T":{
                    '$gte':1654707600077, 
                    '$lte':1654707600078
                }
            })
        print(list(data))
