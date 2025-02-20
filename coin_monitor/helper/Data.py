from email import header
from time import sleep
import pandas as pd
from datetime import datetime
from dateutil import tz
import requests

from helper.Defaults import Number, exceptionInfo, get
from models.Mongo.MongoModel import MongoModel

VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

def splitCollName(startTime, stopTime, symbol, tail):
    '''
    return list of day and start/stop time
    [{
        date: '2022_06_01',
        collection: '2022_06_01_BTCUSDT_tail',
        startTime: 1654072377214
        stopTime: 1653695999999
        model: 
    }]
    '''

    hddModel = MongoModel('raw_data_01')
    ssdModel = MongoModel('raw_data')
    hddCollections = list(hddModel.database.list_collection_names())
    ssdCollections = list(ssdModel.database.list_collection_names())
    collMapDb = {}
    for coll in hddCollections: collMapDb[coll] = hddModel
    for coll in ssdCollections: collMapDb[coll] = ssdModel

    if(startTime >= stopTime): return []
    
    hs = 60*60*1000

    hourRange = range(startTime, stopTime + hs, hs)

    data = pd.DataFrame({"time": hourRange})
    data.loc[data['time'] > stopTime, 'time'] = stopTime
    
    data['startTime'] = data['time']//hs * hs
    data['stopTime'] = (data['time']//hs + 1) * hs - 1
    data.loc[data['stopTime'] > stopTime, 'stopTime'] = stopTime
    data.loc[data['startTime'] < startTime, 'startTime'] = startTime
    
    data['date'] = data['time'].apply(lambda x: datetime.fromtimestamp(x/1000, tz=VN_TZ).strftime('%Y_%m_%d'))
    
    data = data.groupby(['date']).agg({
        'date': 'last',
        'startTime': 'first',
        'stopTime': 'last'
    })

    data['collection'] = data['date'] + f"_{symbol}_{tail}"
    
    returnData = data.to_dict(orient="records")
    for dt in returnData: dt['model'] = get(collMapDb, dt['collection'], None)

    return returnData



def getKline(symbol, frame, startTime, endTime=None):
        if(endTime is None): endTime = int(datetime.now().timestamp()*1000)
        data = []
        
        while True:
            try:
                queryTime = int(datetime.now().timestamp() * 1000)
                print(f"Get history data from {datetime.fromtimestamp(startTime/1000, tz=VN_TZ)} to {datetime.fromtimestamp(endTime/1000, tz=VN_TZ)}")
                block = requests.get(f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={frame}&startTime={startTime}&limit=1000')
                block = block.json()
                
                if(len(block) == 0): break
                for dt in block:
                    closeTime = Number(dt[6])
                    
                    data.append({
                        'symbol': symbol,
                        'open_time': Number(dt[0]),
                        'close_time': closeTime,
                        'open': Number(dt[1]),
                        'high': Number(dt[2]),
                        'low': Number(dt[3]),
                        'close': Number(dt[4]),
                        'volume': Number(dt[5]),
                        'quote': Number(dt[7]),
                        'trades' : Number(dt[8]),
                        'bu_base' : Number(dt[9]),
                        'bu_quote' : Number(dt[10]),
                        'sd_base' : Number(dt[5]) - Number(dt[9]),
                        'sd_quote' : Number(dt[7]) - Number(dt[10]),
                        'is_close': 1,
                        'event_time': Number(dt[6]) if Number(dt[6]) < queryTime else queryTime,
                    })

                    if(closeTime > endTime): break
                    
                startTime = Number(data[-1]['event_time']) + 1
                if(startTime >= endTime): break

            except Exception as e:
                break

        return data

def getKlineBlock(symbol, frame, startTime, endTime=None, exchange='future'):
        if(endTime is None): endTime = int(datetime.now().timestamp()*1000)
        _symbol = symbol
        if symbol == 'BTCUSDT':
            exchange = 'spot'
        if symbol == 'BTCUSDT_PERP':
            exchange = 'future'
            symbol = 'BTCUSDT'
        while True:
            try:
                data = []
                queryTime = int(datetime.now().timestamp() * 1000)
                print(f"Get history data {_symbol} {frame} from {datetime.fromtimestamp(startTime/1000, tz=VN_TZ)} to {datetime.fromtimestamp(endTime/1000, tz=VN_TZ)}")
                if(exchange == 'future'):
                    url = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={frame}&startTime={startTime}&limit=1000'
                else:
                    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={frame}&startTime={startTime}&limit=1000'
                # print(url)
                block = requests.get(url)
                # print(block.headers)
                used_weight = Number(block.headers['X-MBX-USED-WEIGHT-1M'])
                max_weight = 2400
                block = block.json()
                if(len(block) == 0): break
                for dt in block:
                    # print(dt)
                    closeTime = Number(dt[6])
                    
                    data.append({
                        'symbol': _symbol,
                        'open_time': Number(dt[0]),
                        'close_time': closeTime,
                        'open': Number(dt[1]),
                        'high': Number(dt[2]),
                        'low': Number(dt[3]),
                        'close': Number(dt[4]),
                        'volume': Number(dt[5]),
                        'quote': Number(dt[7]),
                        'trades' : Number(dt[8]),
                        'bu_base' : Number(dt[9]),
                        'bu_quote' : Number(dt[10]),
                        'sd_base' : Number(dt[5]) - Number(dt[9]),
                        'sd_quote' : Number(dt[7]) - Number(dt[10]),
                        'is_close': 1,
                        'event_time': Number(dt[6]) if Number(dt[6]) < queryTime else queryTime,
                    })

                    if(closeTime >= endTime): break
                
                yield data
                    
                startTime = Number(data[-1]['event_time']) + 1
                if(startTime >= endTime): break
                # Nếu used weight hơn 95% thì chờ 1 phút
                if used_weight >= max_weight * 95/100:
                    sleep(60)
            except Exception as e:
                print(exceptionInfo(e))
                break



class DataTaker:
    
    def __init__(self) -> None:
        
        self.dbSSDRaw = MongoModel('raw_data')
        self.dbHDDRaw = MongoModel('raw_data_01')
        self.dbSSDRealtimeData = MongoModel('raw_data_coinm')
        self.collections = {}
        self.listOfDays = []
        self.loadCollections()
        
    def loadCollections(self):
        
        collections:dict = self.dbHDDRaw.database.collection_names()
        for collection in collections:
            self.collections[collection] = self.dbHDDRaw
            
        collections = self.dbSSDRaw.database.collection_names()
        for collection in collections:
            self.collections[collection] = self.dbSSDRaw
            
        collections = self.dbSSDRealtimeData.database.collection_names()
        for collection in collections:
            self.collections[collection] = self.dbSSDRealtimeData
        
        self.listOfDays = list(set([x[:10] for x in list(self.collections.keys())]).union())
        
        
    def getData(self, day, symbol, dataType, columns = None):
       
        if(dataType == 'depth20'):
            if(symbol[-5:] == '_PERP'):
                symbol = symbol[:-5]
            
        collection = f"{day}_{symbol}_{dataType}"
        print(f"Get data collection {collection}")
        db:MongoModel = self.collections.get(collection, None)
        if(db is None): return []
        if(columns is None):
            return db.setCollection(collection).collection.find({}).sort('_id', 1)
        else:
            return db.setCollection(collection).collection.find({}, columns).sort('_id', 1)
            
        
            
        
        
        
