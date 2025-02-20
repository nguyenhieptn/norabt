
# This is an auto-generated model for mongodb develope by LIN.
# This wrapper allow you to:
# - Set defaul using
# - Auto-fill the field of the model
# Feel free to rename the models, but don't rename db_table values or field names. 


from models.Mongo.MongoModel import MongoModel

class Order_bookModel(MongoModel):
    _id = "_id"
    symbol = "symbol"
    tran_time = "tran_time"
    event_time = "event_time"
    ready_time = "ready_time"
    stable_time = "stable_time"
    timestamp = "timestamp"
    best_ask = "best_ask"
    best_bid = "best_bid"
    mid_price = "mid_price"
    askV_1 = "askV_1"
    bidV_1 = "bidV_1"
    askV_0_1 = "askV_0_1"
    bidV_0_1 = "bidV_0_1"
    askV_2 = "askV_2"
    bidV_2 = "bidV_2"
    askV_1_2 = "askV_1_2"
    bidV_1_2 = "bidV_1_2"
    askV_5 = "askV_5"
    bidV_5 = "bidV_5"
    askV_2_5 = "askV_2_5"
    bidV_2_5 = "bidV_2_5"
    bidV_ma_5 = "bidV_ma_5"
    askV_ma_5 = "askV_ma_5"
    NetBA_5 = "NetBA_5"
    NetBA_std_5 = "NetBA_std_5"
    NetBA_mean_5 = "NetBA_mean_5"
    NetBA_BOLU_5 = "NetBA_BOLU_5"
    NetBA_BOLD_5 = "NetBA_BOLD_5"
    def __init__(self, db='backtest_data', coll='order_book') -> None:
        super().__init__(db, coll)            

