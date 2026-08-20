from random import randint
import os
import subprocess
import sys
from threading import Thread
from time import sleep

import psutil
from dateutil import tz

from django.core.management.base import BaseCommand
from helper.Defaults import *
from helper.Data import *

from helper.Defaults import *


VN_TZ = tz.gettz("Asia/Ho_Chi_Minh")

# Thư mục gốc coin_monitor (không hardcode path server cũ)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Guard tài nguyên: RAM khả dụng dưới ngưỡng thì tạm dừng nhận symbol mới
MIN_AVAILABLE_RAM_GB = 3.0


class Command(BaseCommand):
    help = "Crawl kline 1m"

    def __init__(
        self, stdout=None, stderr=None, no_color=False, force_color=False
    ):
        super().__init__(stdout, stderr, no_color, force_color)

    def add_arguments(self, parser):
        parser.add_argument("--exchange", nargs="?", default="future", type=str)
        parser.add_argument(
            "-e", "--except", nargs="*", dest="excepts", default=[]
        )
        # Mặc định chỉ crawl danh sách coin chiến lược (has_symbols).
        # --all: crawl toàn bộ cặp USDT trên Binance (nặng, chỉ khi chủ đích).
        # --symbols: chỉ định danh sách cụ thể.
        parser.add_argument("--all", action="store_true", dest="crawlAll", default=False)
        parser.add_argument("--symbols", nargs="*", dest="symbols", default=None)
        parser.add_argument("--from", dest="fromDay", nargs="?", default="2025_01_01", type=str)
        parser.add_argument("--to", dest="toDay", nargs="?", default=None, type=str)

    def handle(self, *args, **options):
        self.exchange = options.get("exchange", "future")
        self.excepts = options.get("excepts", [])
        self.fromDay = options.get("fromDay")
        self.toDay = options.get("toDay")
        has_symbols = [
            "BTCUSDT",
            "ZENUSDT",
            "INJUSDT",
            "CVCUSDT",
            "1000SHIBUSDT",
            "IMXUSDT",
            "ETHUSDT",
            "DYDXUSDT",
            "RENUSDT",
            "TONUSDT",
            "STORJUSDT",
            "ENJUSDT",
            "KAVAUSDT",
            "DOGEUSDT",
            "ONDOUSDT",
            "APEUSDT",
            "OPUSDT",
            "ZECUSDT",
            "TIAUSDT",
            "ORDIUSDT",
            "WAVESUSDT",
            "XMRUSDT",
            "TAOUSDT",
            "ENSUSDT",
            "OCEANUSDT",
            "QTUMUSDT",
            "JASMYUSDT",
            "DEFIUSDT",
            "AVAXUSDT",
            "WLDUSDT",
            "FTMUSDT",
            "KSMUSDT",
            "NEARUSDT",
            "STXUSDT",
            "HNTUSDT",
            "SUIUSDT",
            "SOLUSDT",
            "APTUSDT",
            "ARUSDT",
            "BALUSDT",
            "SEIUSDT",
            "KNCUSDT",
            "SXPUSDT",
            "ETCUSDT",
            "1INCHUSDT",
            "RUNEUSDT",
            "ARBUSDT",
            "ADAUSDT",
            "IOSTUSDT",
            "BCHUSDT",
            "GRTUSDT",
            "1000PEPEUSDT",
            "BLZUSDT",
            "1000BONKUSDT",
            "XRPUSDT",
            "XLMUSDT",
            "ZILUSDT",
            "COMPUSDT",
            "PYTHUSDT",
            "SKLUSDT",
            "FETUSDT",
            "STRKUSDT",
            "SRMUSDT",
            "LDOUSDT",
            "ONTUSDT",
            "LINKUSDT",
            "MINAUSDT",
            "ICXUSDT",
            "CTKUSDT",
            "MKRUSDT",
            "GALAUSDT",
            "SNXUSDT",
            "FILUSDT",
            "LTCUSDT",
            "AAVEUSDT",
            "ATOMUSDT",
            "BNBUSDT",
            "EOSUSDT",
            "THETAUSDT",
            "TRBUSDT",
            "UNIUSDT",
            "MANAUSDT",
            "DOTUSDT",
            "CHZUSDT",
            "CRVUSDT",
            "BATUSDT",
            "TRXUSDT",
            "FLMUSDT",
            "BELUSDT",
            "AXSUSDT",
            "RENDERUSDT",
            "NOTUSDT",
            "HBARUSDT",
            "LRCUSDT",
            "TOMOUSDT",
            "EGLDUSDT",
            "VETUSDT",
            "RLCUSDT",
        ]

        # Máy mới, Mongo local trống: crawl ĐÚNG danh sách coin chiến lược
        # (has_symbols). Logic cũ "tất cả trừ has_symbols" chỉ đúng trên server
        # cũ nơi các coin này đã có sẵn dữ liệu.
        if options.get("symbols"):
            symbols = options["symbols"]
        elif options.get("crawlAll"):
            symbols = self.getAllSymbols()
        else:
            symbols = has_symbols

        self.total = len(symbols)
        self.done = 0

        threads = list()
        max_threads = 3  # mỗi symbol tốn ~1000 weight mỗi phút
        for symbol in symbols:
            if symbol in self.excepts:
                continue
            thread = Thread(target=self.openProc, args=(symbol,))
            threads.append(thread)
        count = max_threads
        start = 0

        while count > 0:
            count = 0
            for index, _thread in enumerate(threads):
                _thread: Thread
                if _thread is not None and _thread.is_alive():
                    count += 1
                else:
                    if index < start:
                        threads[index] = None
                        continue
                    if count < max_threads:
                        # Guard tài nguyên: RAM thấp thì chờ, không nhận symbol mới
                        while psutil.virtual_memory().available < MIN_AVAILABLE_RAM_GB * 1024**3:
                            print(f"[ResourceGuard] RAM khả dụng < {MIN_AVAILABLE_RAM_GB}GB - tạm dừng 30s...")
                            sleep(30)
                        _thread.start()
                        start += 1
                        count += 1
            sleep(1)

        print(f"Crawl kline 1m {self.total} symbols were done.")

    def openProc(self, symbol):
        print(f"Crawl kline 1m {symbol}")
        logs_dir = os.path.join(BASE_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, f"crawler_kline1m_{symbol}.log")
        cmd = (
            f"{sys.executable} {os.path.join(BASE_DIR, 'manage.py')} crawl_kline_1m"
            f" -s {symbol} -e {self.exchange} --from {self.fromDay}"
        )
        if self.toDay:
            cmd += f" --to {self.toDay}"
        cmd += f" > {log_file} 2>&1"
        pro = subprocess.Popen(cmd, shell=True)
        pro.wait()
        self.done += 1
        print(f"Crawl kline 1m {symbol} done {self.done}/{self.total}")

    def getAllSymbols(self):
        if self.exchange == "future":
            url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        else:
            url = "https://api.binance.com/api/v3/exchangeInfo"
        request = requests.get(url)
        data = request.json()
        symbolData = data["symbols"]
        symbols = list()
        for symbolItem in symbolData:
            if symbolItem["quoteAsset"] == "USDT":
                symbols.append(symbolItem["symbol"])
        symbols.sort()
        return symbols
