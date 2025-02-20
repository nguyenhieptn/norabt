
# This is an auto-generated model wrapper singleton develope by LIN.
# This wrapper allow you to:
# - Set defaul using
# - Auto-fill the field of the model
# - Define some SQL relation over Register (preDropRegister)
# Feel free to rename the models, but don't rename db_table values or field names. 

from Console.Models.Wrappers.Model import Model
from Console.Models.Test import *


class Table1Wrapper(Model):
    
    id1 = 'id1'
    name1 = 'name1'
    
    def __init__(self):
        super().__init__(Table1, 'test')


class Table2Wrapper(Model):
    
    id2 = 'id2'
    name2 = 'name2'
    
    def __init__(self):
        super().__init__(Table2, 'test')

