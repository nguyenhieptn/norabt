from datetime import datetime
from dateutil import tz

from django.core.management.base import BaseCommand
from more_itertools import last
from helper.Defaults import *
from helper.Data import *

from helper.Redis import Redis
from helper.Defaults import *
import pandas as pd
from pymongo import DESCENDING, ASCENDING


import pandas as pd

from models.Mongo.CandleModel import Candle_Model
from models.Mongo.BusdModel import BusdModel
from models.Mongo.OrderbookModel import Order_bookModel


VN_TZ = tz.gettz("Asia/Ho_Chi_Minh")


class Command(BaseCommand):
    help = "Crawl kline 1m"

    def __init__(
        self, stdout=None, stderr=None, no_color=False, force_color=False
    ):
        super().__init__(stdout, stderr, no_color, force_color)

    def add_arguments(self, parser):
        parser.add_argument(
            "-e", "--exchange", nargs="?", default="future", type=str
        )
        parser.add_argument("-s", "--symbol", nargs="?", default=None, type=str)

    def handle(self, *args, **options):
        self.exchange = options.get("exchange", "future")
        self.symbol = options.get("symbol", None)

        if self.symbol is None:
            print("Please define symbol")
            return

        database = f"raw_kline1m_{self.exchange}"
        collection = f"{self.symbol}_kline_1m"

        self.candleModel = Candle_Model(database, collection)

        # Get start Time
        lastData = list(
            self.candleModel.collection.find()
            .sort("close_time", DESCENDING)
            .limit(1)
        )
        # print(lastData)
        if len(lastData) == 0:
            startTime = 1577836800000
        else:
            startTime = lastData[0]["open_time"]
            self.candleModel.collection.delete_many({"open_time": startTime})

        datas = getKlineBlock(
            self.symbol, "1m", startTime, 1735689600000, self.exchange
        )
        for block in datas:
            print(f"{self.symbol} insert {len(block)}")
            self.candleModel.collection.insert_many(block)

        self.candleModel.collection.create_index("close_time")
        self.candleModel.collection.create_index("open_time")

    def getStartTime(self):
        if startTime is None:
            if self.day is None:
                startTime = (
                    int(datetime.now().timestamp() * 1000) - 7 * 86400000
                )
                startTime = startTime // 86400000 * 86400000
                return startTime
            else:
                return int(
                    datetime.strptime(self.day, "%Y_%m_%d")
                    .replace(tzinfo=VN_TZ)
                    .timestamp()
                    * 1000
                )
        else:
            return startTime
