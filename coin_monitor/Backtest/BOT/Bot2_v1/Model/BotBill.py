# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from .BotOrder import BotOrder
from .Constant import *
import json
from uuid import uuid4


class BotBill():
    bot_bill_id = 1
    bot_bill_action = None
    bot_bill_act_type = None
    bot_bill_phase = None
    bot_bill_status = None
    bot_bill_ignore = None
    bot_bill_position = None
    bot_bill_reason = None

    columns = [
        'bot_bill_id',
        'bot_bill_action',
        'bot_bill_act_type',
        'bot_bill_phase',
        'bot_bill_status',
        'bot_bill_ignore',
        'bot_bill_position',
        'bot_bill_reason',
    ]
    
    def __init__(self, *args: any, **kwargs: any) -> None:
        
        for col in self.columns:
            setattr(self, col, kwargs.get(col))
        self.bot_bill_id = str(uuid4())
        self.orders = {}
        self.expectPosition = None
        self.sending = False
    
    #extra functions
    
    def setExpectPosition(self, expectPosition):
        self.expectPosition = expectPosition
        self.bot_bill_position = json.dumps(expectPosition)
    
    def getOrdersFromDb(self):
        orders = BotOrder.getObjects().filter(bot_order_bill=self.bot_bill_id)
        for order in orders:
            order:BotOrder
            self.orders[order.bot_order_id] = order
        return self.orders
            
    def addOrder(self, order:BotOrder):
        self.orders[order.bot_order_id] = order
        
    def getPosition(self):
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
    
    def updateStatus(self):
        status = BillStatus.STATUS_COMPLETED
        
        if(self.sending):
            status = BillStatus.STATUS_WAITTING
        
        if(status == BillStatus.STATUS_COMPLETED):
            currentPosition = self.getPosition()
            for symbol in currentPosition:
                data = currentPosition[symbol]
                if(data['waiting'] != 0):
                    status = BillStatus.STATUS_WAITTING
                    break
                
        if(status == BillStatus.STATUS_COMPLETED):
            if(self.bot_bill_act_type == BillActType.ACT_TYPE_MAKE_ORDER):   
                for symbol in self.expectPosition:
                    qty = self.expectPosition[symbol]
                    if(symbol not in currentPosition or qty != currentPosition[symbol]['matched']):
                        status = BillStatus.STATUS_UNCOMPLETED
                        break
        
        if(status != self.bot_bill_status):
            self.bot_bill_status = status
            
            #Update position if not
            if(status == BillStatus.STATUS_COMPLETED and self.expectPosition is None):
                self.expectPosition = {}
                for symbol in currentPosition:
                    self.expectPosition[symbol] = currentPosition[symbol]['matched']
                self.bot_bill_position = json.dumps(self.expectPosition)
                
        
    