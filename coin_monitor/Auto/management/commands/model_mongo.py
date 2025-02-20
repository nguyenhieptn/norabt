import inspect
from django.core.management.base import BaseCommand
from models.Mongo.MongoModel import MongoModel
class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('--using',nargs='?', action='store', default='default')
        parser.add_argument('--coll',nargs='?', action='append')

    def handle(self, *args, **options):
        # try:

            using = options['using']
            selectColl = options['coll']
            
            self.mgModel = MongoModel(using)
            if(selectColl is None):
                selectColl = [x['name'] for x in list(self.mgModel.database.list_collections())]
                

            
            output = """
# This is an auto-generated model for mongodb develope by LIN.
# This wrapper allow you to:
# - Set defaul using
# - Auto-fill the field of the model
# Feel free to rename the models, but don't rename db_table values or field names. 

from models.Mongo.MongoModel import MongoModel
"""

            for coll in selectColl:
                tem = f'''
class {coll.capitalize()}Model(MongoModel):
    ##attributes##
    def __init__(self, db='{using}', coll='{coll}') -> None:
        super().__init__(db, coll)            
'''
                fields = self.mgModel.setCollection(coll).find().sort("_id", -1).limit(10)
                columns = []
                processedCol = {}
                for row in fields:
                    for (key, value) in row.items():
                        if(key in processedCol): continue
                        processedCol[key] = True
                        columns.append(f"{key} = \"{key}\"")
                tem = tem.replace("##attributes##", '\n    '.join(columns))
                output += tem



           
           

            print(output)
                
        # except Exception as e:
        #     print(e)
    