
from models.Mongo.MongoModel import MongoModel

class KlineModel(MongoModel):
    def __init__(self, db='raw_data', coll=None) -> None:
        super().__init__(db, coll)
        