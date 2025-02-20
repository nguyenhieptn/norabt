
from models.Mongo.mongoModel import mongoModel

class OrderbookModel(mongoModel):
    def __init__(self, db='backtest_data', coll='order_book') -> None:
        super().__init__(db, coll)
        