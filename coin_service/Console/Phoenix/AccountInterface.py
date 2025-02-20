

from Console.Helper.Defaults import *
from Console.Helper.Control import *

class AccountInterface():

    campaignImps = {}

    def updateProfit(self, profit)->None:
        raise Exception('no implementation')

    def countPosition(self)->int:
        raise Exception('no implementation')

    def countSlot(self, strategyId)->int:
        raise Exception('no implementation')

    def getWattingPosition(self)->list:
        raise Exception('no implementation')

    def getWattingSlot(self, strategyId)->list:
        raise Exception('no implementation')
    