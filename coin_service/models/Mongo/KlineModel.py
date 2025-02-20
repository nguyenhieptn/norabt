
from models.Mongo.mongoModel import mongoModel

class KlineModel(mongoModel):
    def __init__(self, db='backtest_data', coll=None) -> None:
        super().__init__(db, coll)
        