
# This is an auto-generated model for mongodb develope by LIN.
# This wrapper allow you to:
# - Set defaul using
# - Auto-fill the field of the model
# Feel free to rename the models, but don't rename db_table values or field names. 

from models.Mongo.MongoModel import MongoModel

class Candle_4hModel(MongoModel):
    _id = "_id"
    timestamp = "timestamp"
    symbol = "symbol"
    open_time = "open_time"
    close_time = "close_time"
    open = "open"
    high = "high"
    low = "low"
    close = "close"
    volume = "volume"
    quote = "quote"
    trades = "trades"
    bu_base = "bu_base"
    bu_quote = "bu_quote"
    sd_base = "sd_base"
    sd_quote = "sd_quote"
    is_close = "is_close"
    event_time = "event_time"
    rsi_close_14 = "rsi_close_14"
    avgU_close_14 = "avgU_close_14"
    avgD_close_14 = "avgD_close_14"
    def __init__(self, db='backtest_data', coll='candle_4h') -> None:
        super().__init__(db, coll)            

class Candle_1dModel(MongoModel):
    _id = "_id"
    timestamp = "timestamp"
    symbol = "symbol"
    open_time = "open_time"
    close_time = "close_time"
    open = "open"
    high = "high"
    low = "low"
    close = "close"
    volume = "volume"
    quote = "quote"
    trades = "trades"
    bu_base = "bu_base"
    bu_quote = "bu_quote"
    sd_base = "sd_base"
    sd_quote = "sd_quote"
    is_close = "is_close"
    event_time = "event_time"
    rsi_close_14 = "rsi_close_14"
    avgU_close_14 = "avgU_close_14"
    avgD_close_14 = "avgD_close_14"
    def __init__(self, db='backtest_data', coll='candle_1d') -> None:
        super().__init__(db, coll)            

class Candle_15mModel(MongoModel):
    _id = "_id"
    timestamp = "timestamp"
    symbol = "symbol"
    open_time = "open_time"
    close_time = "close_time"
    open = "open"
    high = "high"
    low = "low"
    close = "close"
    volume = "volume"
    quote = "quote"
    trades = "trades"
    bu_base = "bu_base"
    bu_quote = "bu_quote"
    sd_base = "sd_base"
    sd_quote = "sd_quote"
    is_close = "is_close"
    event_time = "event_time"
    rsi_close_14 = "rsi_close_14"
    avgU_close_14 = "avgU_close_14"
    avgD_close_14 = "avgD_close_14"
    def __init__(self, db='backtest_data', coll='candle_15m') -> None:
        super().__init__(db, coll)            

class Candle_1wModel(MongoModel):
    _id = "_id"
    symbol = "symbol"
    open_time = "open_time"
    close_time = "close_time"
    open = "open"
    high = "high"
    low = "low"
    close = "close"
    volume = "volume"
    quote = "quote"
    trades = "trades"
    bu_base = "bu_base"
    bu_quote = "bu_quote"
    sd_base = "sd_base"
    sd_quote = "sd_quote"
    is_close = "is_close"
    event_time = "event_time"
    rsi_close_14 = "rsi_close_14"
    avgU_close_14 = "avgU_close_14"
    avgD_close_14 = "avgD_close_14"
    wma_rsi_close_14_45 = "wma_rsi_close_14_45"
    timestamp = "timestamp"
    def __init__(self, db='backtest_data', coll='candle_1w') -> None:
        super().__init__(db, coll)            



class Candle_3mModel(MongoModel):
    _id = "_id"
    timestamp = "timestamp"
    symbol = "symbol"
    open_time = "open_time"
    close_time = "close_time"
    open = "open"
    high = "high"
    low = "low"
    close = "close"
    volume = "volume"
    quote = "quote"
    trades = "trades"
    bu_base = "bu_base"
    bu_quote = "bu_quote"
    sd_base = "sd_base"
    sd_quote = "sd_quote"
    is_close = "is_close"
    event_time = "event_time"
    rsi_close_14 = "rsi_close_14"
    avgU_close_14 = "avgU_close_14"
    avgD_close_14 = "avgD_close_14"
    def __init__(self, db='backtest_data', coll='candle_3m') -> None:
        super().__init__(db, coll)            

class Candle_1hModel(MongoModel):
    _id = "_id"
    timestamp = "timestamp"
    symbol = "symbol"
    open_time = "open_time"
    close_time = "close_time"
    open = "open"
    high = "high"
    low = "low"
    close = "close"
    volume = "volume"
    quote = "quote"
    trades = "trades"
    bu_base = "bu_base"
    bu_quote = "bu_quote"
    sd_base = "sd_base"
    sd_quote = "sd_quote"
    is_close = "is_close"
    event_time = "event_time"
    rsi_close_14 = "rsi_close_14"
    avgU_close_14 = "avgU_close_14"
    avgD_close_14 = "avgD_close_14"
    def __init__(self, db='backtest_data', coll='candle_1h') -> None:
        super().__init__(db, coll)            

class Candle_1mModel(MongoModel):
    _id = "_id"
    timestamp = "timestamp"
    symbol = "symbol"
    open_time = "open_time"
    close_time = "close_time"
    open = "open"
    high = "high"
    low = "low"
    close = "close"
    volume = "volume"
    quote = "quote"
    trades = "trades"
    bu_base = "bu_base"
    bu_quote = "bu_quote"
    sd_base = "sd_base"
    sd_quote = "sd_quote"
    is_close = "is_close"
    event_time = "event_time"
    rsi_close_14 = "rsi_close_14"
    avgU_close_14 = "avgU_close_14"
    avgD_close_14 = "avgD_close_14"
    def __init__(self, db='backtest_data', coll='candle_1m') -> None:
        super().__init__(db, coll)

class Candle_Model(MongoModel):
    _id = "_id"
    timestamp = "timestamp"
    symbol = "symbol"
    open_time = "open_time"
    close_time = "close_time"
    open = "open"
    high = "high"
    low = "low"
    close = "close"
    volume = "volume"
    quote = "quote"
    trades = "trades"
    bu_base = "bu_base"
    bu_quote = "bu_quote"
    sd_base = "sd_base"
    sd_quote = "sd_quote"
    is_close = "is_close"
    event_time = "event_time"
    rsi_close_14 = "rsi_close_14"
    avgU_close_14 = "avgU_close_14"
    avgD_close_14 = "avgD_close_14"
    def __init__(self, db='backtest_data', coll='candle_1m') -> None:
        super().__init__(db, coll)             

