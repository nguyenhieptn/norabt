# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from uuid import uuid4

class BotOrder():
    bot_order_id = 1
    bot_order_camp = None
    bot_order_action = None
    bot_order_gid = None
    bot_order_time = None
    bot_order_history = None
    bot_order_log = None
    bot_order_symbol = None
    bot_order_symbol_pair = None
    bot_order_status = None
    bot_order_remote_status = None
    bot_order_price = None
    bot_order_qty = None
    bot_order_matched_qty = None
    bot_order_matched_price = None
    bot_order_matched_time = None
    bot_order_unmatched_qty = None
    bot_order_commission = None
    bot_order_act_type = None
    bot_order_type = None
    bot_order_side = None
    bot_order_exchange = None
    bot_order_marketid = None
    bot_order_validity = None
    bot_order_number = None
    
    bot_order_bill = None
    bot_order_phase = None
    
    columns = [
        'bot_order_id',
        'bot_order_camp',
        'bot_order_action',
        'bot_order_gid',
        'bot_order_time',
        'bot_order_history',
        'bot_order_log',
        'bot_order_symbol',
        'bot_order_symbol_pair',
        'bot_order_status',
        'bot_order_remote_status',
        'bot_order_price',
        'bot_order_qty',
        'bot_order_matched_qty',
        'bot_order_matched_price',
        'bot_order_matched_time',
        'bot_order_unmatched_qty',
        'bot_order_commission',
        'bot_order_act_type',
        'bot_order_type',
        'bot_order_side',
        'bot_order_exchange',
        'bot_order_marketid',
        'bot_order_validity',
        'bot_order_number',
        'bot_order_bill',
        'bot_order_phase',
    ]
    
    def __init__(self, *args: any, **kwargs: any) -> None:
        
        for col in self.columns:
            setattr(self, col, kwargs.get(col))
        self.bot_order_id = str(uuid4())
        self.orders = {} 
        
    def toDict(self):
        returnData = {}
        for column in self.columns:
            returnData[column] = getattr(self, column)
        return returnData
        

    
    