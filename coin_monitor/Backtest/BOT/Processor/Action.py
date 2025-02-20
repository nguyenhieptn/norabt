
import uuid

from Backtest.BOT.Processor.Order import Order

class Action():
    
    bot_act_id = None
    bot_act_campaign = None
    bot_act_status_enter = None
    bot_act_status_exit = None
    bot_act_status_pair = None
    bot_act_status_close = None
    bot_act_enter_data = None
    bot_act_exit_data = None
    bot_act_flow = None
    bot_act_enter_time = None
    bot_act_matched_time = None
    bot_act_exit_time = None
    bot_act_pending = None
    bot_act_enter_reason = None
    bot_act_exit_reason = None
    bot_act_log = None
    bot_act_pnl = None
    bot_act_real_pnl = None
    bot_act_commission = None
    bot_act_qty = None
    bot_act_symbol = None
    bot_act_symbol_pair = None
    bot_act_enter_gap = None
    bot_act_dayfee = None

    STATUS_ENTER_SENDING = 'ENTER_SENDING'
    STATUS_ENTER_PENDING = 'ENTER_PENDING'
    STATUS_ENTER_PART = 'ENTER_PART'
    STATUS_ENTER_FULL = 'ENTER_FULL'
    STATUS_ENTER_CANCEL = 'ENTER_CANCEL'

    STATUS_EXIT_SENDING = 'EXIT_SENDING'
    STATUS_EXIT_PENDING = 'EXIT_PENDING'
    STATUS_EXIT_PART = 'EXIT_PART'
    STATUS_EXIT_FULL = 'EXIT_FULL'
    STATUS_EXIT_CANCEL = 'EXIT_CANCEL'

    STATUS_CLOSE_PENDING = 'CLOSE_PENDING'
    STATUS_CLOSE_FORCE = 'CLOSE_FORCE'
    STATUS_CLOSE_DONE = 'CLOSE_DONE'

    PAIR_STATUS_PENDING = 'PAIR_PENDING'
    PAIR_STATUS_OK = 'PAIR_OK'

    columns = [
        'bot_act_id',
        'bot_act_campaign',
        'bot_act_status_enter',
        'bot_act_status_exit',
        'bot_act_status_pair',
        'bot_act_enter_data',
        'bot_act_exit_data',
        'bot_act_flow',
        'bot_act_enter_time',
        'bot_act_matched_time',
        'bot_act_exit_time',
        'bot_act_pending',
        'bot_act_enter_reason',
        'bot_act_exit_reason',
        'bot_act_log',
        'bot_act_pnl',
        'bot_act_real_pnl',
        'bot_act_commission',
        'bot_act_qty',
        'bot_act_status_close',
        'bot_act_symbol',
        'bot_act_symbol_pair',
        'bot_act_enter_gap',
        'bot_act_dayfee'
    ]
    
    def __init__(self, **args) -> None:
        self.bot_act_id = uuid.uuid4().hex
        self.orders:dict = {}
        self.tasks:dict = {}
        self.pending_orders:dict = {}

        for arg in args:
            setattr(self, arg, args[arg])

    
    def addOrder(self, order:Order):
        self.orders[order.bot_order_id] = order
        self.pending_orders[order.bot_order_id] = order
        if(order.bot_order_task is not None and order.bot_order_task in self.tasks):
            self.tasks[order.bot_order_task].addOrder(order)

    def getPendingOrder(self):
        return self.pending_orders
    
    def updateOrder(self, order:Order, datas):

        for key in datas:
            setattr(order, key, datas[key])

        if(order.bot_order_status in [Order.STATUS_CANCELED, Order.STATUS_ERROR, Order.STATUS_MATCHED_FULL]):
            if(order.bot_order_id in self.pending_orders):
                del self.pending_orders[order.bot_order_id]
    
    def toDict(self):
        returnData = {}
        for column in self.columns:
            returnData[column] = getattr(self, column)
        returnData['orders'] = {}
        for orderId in self.orders:
            returnData['orders'][orderId] = self.orders[orderId].toDict()
        return returnData
    
    

            
        