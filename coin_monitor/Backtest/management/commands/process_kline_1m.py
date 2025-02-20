from datetime import datetime
from dateutil import tz

from django.core.management.base import BaseCommand
from Backtest.Processors.klineProcessor import klineProcessor1m
from helper.Defaults import *
from helper.Data import *

from math import floor
from threading import Thread
from time import sleep, time
import orjson
from helper.Redis import Redis
from helper.Defaults import *
import pandas as pd


import pandas as pd


VN_TZ = tz.gettz("Asia/Ho_Chi_Minh")


class Command(BaseCommand):
    help = "python manage.py process_kline_1m -s BTCUSDT -d 2010_01_01 --reset "

    def __init__(
        self, stdout=None, stderr=None, no_color=False, force_color=False
    ):
        super().__init__(stdout, stderr, no_color, force_color)

    def add_arguments(self, parser):
        parser.add_argument(
            "-s", "--symbol", nargs="?", required=True, default=None, type=str
        )
        parser.add_argument("-d", "--day", nargs="?", default=None, type=str)
        parser.add_argument("--reset", action="store_true", default=False)
        parser.add_argument(
            "-e", "--exchange", nargs="?", default="future", type=str
        )

    def handle(self, *args, **options):
        self.symbol = options.get("symbol").upper()
        self.day = options.get("day", None)
        self.exchange = options.get("exchange", "future")
        db = "backtest_data_1m"
        if self.exchange == "spot":
            db = "backtest_data_1m_spot"
        self.processor = klineProcessor1m(
            self.symbol, f"raw_kline1m_{self.exchange}", db
        )
        self.reset = options.get("reset", True)
        if self.reset:
            print("Clean data")
            self.processor.cleanData()

        startTime = self.getStartTime() // 1000 * 1000
        stopTime = int(datetime.now().timestamp()) * 1000 - 1

        print(f"{self.symbol} Completed Calculating first block")

        processed = 0

        workingTime = startTime
        startPoint = datetime.now().timestamp()
        while workingTime < stopTime:
            newWorkingTime = workingTime + 15 * 24 * 60 * 60 * 1000 - 1
            datas = self.processor.getKlineData(workingTime, newWorkingTime)

            processed = 0
            for data in datas:
                # print(data)
                self.processor.processData(data)

                processed += 1
                if processed % 1000 == 0:
                    checkTimePoint = datetime.now().timestamp()
                    print(
                        f"\r{self.symbol} Speed {int(1000/(checkTimePoint - startPoint))} package/s processed:{processed}/{len(datas)}  ",
                        end="",
                    )
                    startPoint = checkTimePoint

            workingTime = newWorkingTime + 1

        self.processor.createIndex()

    def getStartTime(self):

        startTime = self.processor.getStartTime()
        if startTime is None:
            if self.day is None:
                startTime = 1262304000000
                # startTime = startTime//86400000 * 86400000
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
