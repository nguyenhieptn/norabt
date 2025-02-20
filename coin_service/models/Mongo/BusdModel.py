
from models.Mongo.mongoModel import mongoModel

class BusdModel(mongoModel):
    def __init__(self, db='backtest_data', coll='busd') -> None:
        super().__init__(db, coll)
        