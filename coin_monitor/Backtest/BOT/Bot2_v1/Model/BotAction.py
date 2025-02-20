# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange None
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the None
from .BotBill import BotBill
from .BotOrder import BotOrder
from .Constant import *
from uuid import uuid4


class BotAction():
    bot_act_id = 1
    bot_act_campaign = None
    bot_act_status_enter = None
    bot_act_status_matched = None
    bot_act_status_exit = None
    bot_act_status_pair = None
    bot_act_status_close = None
    bot_act_status_maturity = None
    bot_act_enter_data = None
    bot_act_exit_data = None
    bot_act_enter_reason = None
    bot_act_exit_reason = None
    bot_act_position = None
    bot_act_log = None
    bot_act_flow = None
    bot_act_enter_time = None
    bot_act_matched_time = None
    bot_act_matched_qty = None
    bot_act_matched_price = None
    bot_act_exit_time = None
    bot_act_exit_price = None
    bot_act_pending = None
    bot_act_pnl = None
    bot_act_profit = None
    bot_act_commission = None
    bot_act_dayfee = None
    bot_act_dayfee_time = None
    bot_act_real_pnl = None
    bot_act_symbol_pair = None
    bot_act_symbol = None
    bot_act_side = None
    
    bot_act_exit_phase = None
    bot_act_exit_bill = None
    bot_act_enter_phase = None
    bot_act_enter_bill = None
    bot_act_bot_type = None
    bot_act_maturity_bill = None
    bot_act_close_bill = None
    
    
    columns = [
        'bot_act_id',
        'bot_act_campaign',
        'bot_act_status_enter',
        'bot_act_status_matched',
        'bot_act_status_exit',
        'bot_act_status_pair',
        'bot_act_status_close',
        'bot_act_status_maturity',
        'bot_act_enter_data',
        'bot_act_exit_data',
        'bot_act_enter_reason',
        'bot_act_exit_reason',
        'bot_act_position',
        'bot_act_log',
        'bot_act_flow',
        'bot_act_enter_time',
        'bot_act_matched_time',
        'bot_act_matched_qty',
        'bot_act_matched_price',
        'bot_act_exit_time',
        'bot_act_exit_price',
        'bot_act_pending',
        'bot_act_pnl',
        'bot_act_profit',
        'bot_act_commission',
        'bot_act_dayfee',
        'bot_act_dayfee_time',
        'bot_act_real_pnl',
        'bot_act_symbol_pair',
        'bot_act_symbol',
        'bot_act_side',
        'bot_act_exit_phase',
        'bot_act_exit_bill',
        'bot_act_enter_phase',
        'bot_act_enter_bill',
        'bot_act_bot_type',
        'bot_act_maturity_bill',
        'bot_act_close_bill',
    ]
    
    
   
    def __init__(self, *args: any, **kwargs: any) -> None:
        
        for col in self.columns:
            setattr(self, col, kwargs.get(col))
        self.bot_act_id = str(uuid4())
        self.bills = {}
        self.orders = {}
        self.pending_orders:dict = {}
                
    def addBill(self, bill:BotBill):
        self.bills[bill.bot_bill_id] = bill
    
    def addOrder(self, order:BotOrder, billId):
        self.orders[order.bot_order_id] = order
        self.pending_orders[order.bot_order_id] = order
        if(billId in self.bills):
            bill:BotBill = self.bills[billId]
            bill.addOrder(order)

    def getPositionSymbol(self):
        '''
        Return position of action by symbol
            {
                VN30F2210: {matched: 5, waiting: 5}
                VN30F2211: {matched: 5, waiting: 5}
            }
        '''
        returnData = {}
        orderIds = list(self.orders.keys())
        for orderId in orderIds:
            order:BotOrder = self.orders[orderId]
            if(order.bot_order_status in [OrderStatus.STATUS_ERROR]): continue

            symbol = order.bot_order_symbol
            if(symbol not in returnData):
                returnData[symbol] = {
                    'matched': 0,
                    'waiting': 0,
                    'exchange': order.bot_order_exchange
                }

            if(order.bot_order_side == OrderSide.SIDE_BUY):
                returnData[symbol]['matched'] += order.bot_order_matched_qty
            else:
                returnData[symbol]['matched'] -= order.bot_order_matched_qty

            if(order.bot_order_status not in [OrderStatus.STATUS_CANCELED, OrderStatus.STATUS_MATCHED_FULL]):
                if(order.bot_order_side == OrderSide.SIDE_BUY):
                    returnData[symbol]['waiting'] += order.bot_order_unmatched_qty
                else:
                    returnData[symbol]['waiting'] -= order.bot_order_unmatched_qty
        return returnData
    
    def getPendingOrder(self):
        return self.pending_orders
    
    def updateOrder(self, order:BotOrder, datas):

        for key in datas:
            setattr(order, key, datas[key])

        if(order.bot_order_status in [OrderStatus.STATUS_CANCELED, OrderStatus.STATUS_ERROR, OrderStatus.STATUS_MATCHED_FULL]):
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
    
    def updateMatchedStatus(self):
        status = ActionMatchedStatus.STATUS_EMPTY
        orderIds = list(self.orders.keys())
        matchedQty = 0
        matchedMoney = 0
        exitQty = 0
        exitMoney = 0
        symbol = None
        for orderId in orderIds:
            order:BotOrder = self.orders[orderId]
            if(order.bot_order_status in [OrderStatus.STATUS_ERROR]): continue
            if(order.bot_order_matched_qty > 0):
                status = ActionMatchedStatus.STATUS_MATCHED
                #calculate matched and avg price
                if(order.bot_order_act_type == BillActType.ACT_TYPE_MAKE_ORDER):
                    if(symbol is None): symbol = order.bot_order_symbol
                    if(order.bot_order_symbol == symbol):
                        if(order.bot_order_side == OrderSide.SIDE_BUY):
                            matchedQty += order.bot_order_matched_qty
                            matchedMoney += order.bot_order_matched_qty * order.bot_order_matched_price
                        else:
                            matchedQty -= order.bot_order_matched_qty
                            matchedMoney -= order.bot_order_matched_qty * order.bot_order_matched_price
                if(order.bot_order_act_type in [BillActType.ACT_TYPE_CLOSE_ORDER, BillActType.ACT_TYPE_EXIT_ORDER]):
                    if(symbol is None): symbol = order.bot_order_symbol
                    if(order.bot_order_symbol == symbol):
                        if(order.bot_order_side == OrderSide.SIDE_BUY):
                            exitQty += order.bot_order_matched_qty
                            exitMoney += order.bot_order_matched_qty * order.bot_order_matched_price
                        else:
                            exitQty -= order.bot_order_matched_qty
                            exitMoney -= order.bot_order_matched_qty * order.bot_order_matched_price
                    
        self.bot_act_matched_qty = matchedQty
        self.bot_act_symbol = symbol
        if(matchedQty != 0):
            self.bot_act_matched_price = matchedMoney/matchedQty
        if(exitQty != 0):
            self.bot_act_exit_price = exitMoney/exitQty
                
        if(status != self.bot_act_status_matched):
            self.bot_act_status_matched = status
    
    

