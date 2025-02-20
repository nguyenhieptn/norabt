from datetime import datetime
from math import floor
from threading import Thread
from time import time
from django.core.management.base import BaseCommand
from Client.Helper.Defaults import Number, Round, isset
from Console.management.commands.crawl_1m import Future, Spot

from Models.data_binance import SpotCandle1M, FutureCandle1M
from Models.Wrappers.data_binance_warpper import FutureCandle1MWrapper, SpotCandle1MWrapper
from Models.Wrappers.nora_analysis_warpper import FutureSpotDiffWrapper, FutureSpotSummaryWrapper
from Models.nora_analysis import FutureSpotDiff, FutureSpotSummary


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self.limit = 1000
        self.spot = Spot()
        self.future = Future()
        self.thread = 10
        self.specialPair = {
            '1000SHIBUSDT': 'SHIBUSDT',
            '1000XECUSDT': 'XECUSDT'
        }

    def add_arguments(self, parser):
        parser.add_argument("--symbols", nargs="*", default=None)

    def spot_symbols(self):
        data = self.spot.exchangeInfo()
        symbols = []
        if data["status"]:
            data = data['data']
            # print(data)
            print('symbols' in data)
            if 'symbols' in data:
                for symbol in data['symbols']:
                    if 'symbol' in symbol:
                        symbols.append(symbol['symbol'])
        symbols = list(filter(lambda x: 'USDT' in x, symbols))
        return symbols

    def future_symbols(self):
        data = self.future.exchangeInfo()
        symbols = []
        if data["status"]:
            data = data['data']
            if 'symbols' in data:
                for symbol in data['symbols']:
                    if 'symbol' in symbol:
                        symbols.append(symbol['symbol'])
        symbols = list(filter(lambda x: 'USDT' in x, symbols))
        return symbols

    def handle(self, *args, **options):

        symbols = options['symbols']

        spot_symbols = self.spot_symbols()
        if(symbols is None):
            future_symbols = self.future_symbols()
        else:
            future_symbols = symbols  # type: list

        

        threads = []
        for futureSymbol in future_symbols:
            futureSymbol = futureSymbol.upper()
            
            spotSymbol = None
            if(isset(self.specialPair, futureSymbol)):
                spotSymbol = self.specialPair[futureSymbol]
            else:
                if(futureSymbol in spot_symbols):
                    spotSymbol = futureSymbol
            if(spotSymbol is not None):
                th = Thread(target=self.cal_diff, args=[futureSymbol, spotSymbol])
                th.start()
                threads.append(th)
                if(len(threads) > self.thread):
                    for thread in threads:
                        thread.join()
                    threads = []

    def cal_diff(self, futureSym, spotSym):
        
        print(f"Calculate Diff {futureSym}-{spotSym}")
        try:
            result = FutureSpotDiffWrapper().raw(
                f"ALTER TABLE future_spot_diff ADD PARTITION (PARTITION p{futureSym} VALUES IN ('{futureSym}'))")
            list(result)
        except:
            pass
        closeTime = None
        startTime = None
        

        while True:
            startTimeMor = time()
            if startTime is None:
                last_diff = FutureSpotDiffWrapper().filter({FutureSpotDiffWrapper.diff_symbol_future: futureSym}).order_by('-diff_time').first()  # type: FutureSpotDiff
                if last_diff is not None and last_diff.diff_time is not None:
                    startTime = last_diff.diff_time
                    fCandles = list(FutureCandle1MWrapper().filter({
                        FutureCandle1MWrapper.future_1m_symbol: futureSym,
                        FutureCandle1MWrapper.future_1m_close_time + '__gt': startTime,
                        FutureCandle1MWrapper.future_1m_close_time + '__lte': startTime + 86400000,
                    }).order_by(FutureCandle1MWrapper.future_1m_close_time))
                else:
                    startTime = 958113480000  # first time
                    fCandles = list(FutureCandle1MWrapper().filter({
                        FutureCandle1MWrapper.future_1m_symbol: futureSym,
                        FutureCandle1MWrapper.future_1m_close_time + '__gt': startTime,
                    }).order_by(FutureCandle1MWrapper.future_1m_close_time)[:self.limit])
            else:
                fCandles = list(FutureCandle1MWrapper().filter({
                    FutureCandle1MWrapper.future_1m_symbol: futureSym,
                    FutureCandle1MWrapper.future_1m_close_time + '__gt': startTime,
                    FutureCandle1MWrapper.future_1m_close_time + '__lte': startTime + 86400000,
                }).order_by(FutureCandle1MWrapper.future_1m_close_time))

            if(len(fCandles) == 0):
                break

            fCandlesIndex = {}
            fcandle: FutureCandle1M
            for fcandle in fCandles:
                fCandlesIndex[fcandle.future_1m_close_time] = fcandle.future_1m_close
                closeTime = fcandle.future_1m_close_time


            sCandles = list(SpotCandle1MWrapper().filter({
                SpotCandle1MWrapper.spot_1m_symbol: spotSym,
                SpotCandle1MWrapper.spot_1m_close_time + '__gt': startTime,
                SpotCandle1MWrapper.spot_1m_close_time + '__lte': closeTime,
            }))

            sCandlesIndex = {}
            scandle: SpotCandle1M
            for scandle in sCandles:
                sCandlesIndex[scandle.spot_1m_close_time] = scandle.spot_1m_close


            addData = []
            for diffTime in fCandlesIndex:
                
                if(not isset(sCandlesIndex, diffTime)):
                    continue
                fclosePrice = Number(fCandlesIndex[diffTime])
                if(isset(self.specialPair, futureSym)):
                    sclosePrice = Number(sCandlesIndex[diffTime]) * 1000
                else:
                    sclosePrice = Number(sCandlesIndex[diffTime])
                diffValue = Round((fclosePrice - sclosePrice)*100/sclosePrice, 5)
                fundingFree = 1 if ((diffTime + 1) % (8*60*60*1000) == 0) else 0
                addData.append(FutureSpotDiffWrapper().new({
                    FutureSpotDiffWrapper.diff_symbol_future: futureSym,
                    FutureSpotDiffWrapper.diff_symbol_spot: spotSym,
                    FutureSpotDiffWrapper.diff_time: diffTime,
                    FutureSpotDiffWrapper.diff_value: diffValue,
                    FutureSpotDiffWrapper.diff_event: fundingFree
                }))
            
            FutureSpotDiffWrapper().bulk_create(addData, 500)
            
            startTime = closeTime
            print(f"Add Diff Data {futureSym}-{spotSym} to time {datetime.fromtimestamp(floor(closeTime/1000))}")

        #cal summary
        print(f"Crawl summary diff {futureSym}")
        summaryDiff = FutureSpotSummaryWrapper().filter({
            FutureSpotSummaryWrapper.summary_future_symbol: futureSym
        }).first()# type: FutureSpotSummary
        if(summaryDiff is None):
            summaryDiff = FutureSpotSummaryWrapper().new({
                FutureSpotSummaryWrapper.summary_future_symbol: futureSym,
                FutureSpotSummaryWrapper.summary_spot_symbol: spotSym,
                FutureSpotSummaryWrapper.summary_max_diff: 0,
                FutureSpotSummaryWrapper.summary_max_diff_time: None,
                FutureSpotSummaryWrapper.summary_min_diff: 0,
                FutureSpotSummaryWrapper.summary_min_diff_time: None,
            })  # type: FutureSpotSummary

        maxDiff = FutureSpotDiffWrapper().filter({FutureSpotDiffWrapper.diff_symbol_future: futureSym}).order_by("-"+FutureSpotDiffWrapper.diff_value).first()  # type: FutureSpotDiff
        if(maxDiff is not None):
            summaryDiff.summary_max_diff = maxDiff.diff_value
            summaryDiff.summary_max_diff_time = maxDiff.diff_time
        minDiff = FutureSpotDiffWrapper().filter({FutureSpotDiffWrapper.diff_symbol_future: futureSym}).order_by(FutureSpotDiffWrapper.diff_value).first()  # type: FutureSpotDiff
        if(minDiff is not None):
            summaryDiff.summary_min_diff = minDiff.diff_value
            summaryDiff.summary_min_diff_time = minDiff.diff_time
        summaryDiff.save()
