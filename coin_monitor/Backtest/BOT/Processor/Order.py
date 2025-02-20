
import uuid

class Order():
    
    bot_order_id = None
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
    bot_order_act_type = None
    bot_order_type = None
    bot_order_side = None
    bot_order_commission = None
    bot_order_task = None

    SIDE_BUY = 'BUY'
    SIDE_SELL = 'SELL'

    TYPE_LO = "LO"
    TYPE_ATC = "ATC"
    TYPE_ATO = "ATO"
    TYPE_MP = 'MAK'

    STATUS_SENDING = 'SENDING'
    STATUS_SENT = 'SENT'
    STATUS_MATCHED_PART = 'MATCHED_PART'
    STATUS_MATCHED_FULL = 'MATCHED_FULL'
    STATUS_CANCELED = 'CANCELED'
    STATUS_ERROR = 'ERROR'

    ACT_TYPE_MAKE_ORDER = 'make_order'
    ACT_TYPE_CLOSE_ORDER = 'close_order'
    ACT_TYPE_PAIR_ORDER = 'pair_order'

    columns = [
        'bot_order_id',
        'bot_order_camp',
        'bot_order_action',
        'bot_order_gid',
        'bot_order_time',
        'bot_order_log',
        'bot_order_symbol',
        'bot_order_status',
        'bot_order_remote_status',
        'bot_order_price',
        'bot_order_qty',
        'bot_order_matched_qty',
        'bot_order_matched_price',
        'bot_order_matched_time',
        'bot_order_unmatched_qty',
        'bot_order_act_type',
        'bot_order_type',
        'bot_order_side',
        'bot_order_commission',
        'bot_order_task'
    ]
    
    def __init__(self, **args) -> None:
        self.bot_order_id = uuid.uuid4().hex
        for arg in args:
            setattr(self, arg, args[arg])
    
    def toDict(self):
        returnData = {}
        for column in self.columns:
            returnData[column] = getattr(self, column)
        return returnData
    
            
        