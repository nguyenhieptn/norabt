from threading import Thread
from time import sleep
import requests

class _TeleThread (Thread):
    def __init__(self, mss, chatId, botId):
        Thread.__init__(self)
        self.mss = mss
        self.chatId = chatId
        self.botId = botId

    def run(self):
        if(self.chatId is None or self.botId is None or self.chatId == '' or self.botId == ''): return
        requests.get('https://api.telegram.org/bot'+str(self.botId)+'/sendMessage', params={'chat_id': str(self.chatId), 'text': str(self.mss)})

class Tele:

    TELE_ICON_LONG = '↗️'
    TELE_ICON_SHORT = '↘️'
    TELE_ICON_TAKEPROFIT = '✅'
    TELE_ICON_STOPLOSS = '⛔️'
    TELE_ICON_ERROR = '🆘'
    TELE_ICON_STOP = '⏹'
    TELE_ICON_CANCEL = '🚫'
    TELE_ICON_MATCHED = '🤝'
    TELE_ICON_WAITTING = '🕒'
    TELE_ICON_WARNING = '⚠️'
   
    TELE_BOT_DEFAULT = '1820957497:AAHiWTbuO-Kp80dFWB_7d74bfvHlOnBIJ08'

    TELE_TEST_ERROR= '-529215337'
    TELE_TEST= '-483692004'
    TELE_SIMULATE= '-546311985'
    TELE_SIMULATE_ERROR= '-529215337'
    TELE_REAL= '-627055162'
    TELE_REAL_ERROR= '-529215337'
    TELE_REAL_SUMMARY= '-627055162'

    @staticmethod
    def send (mss, chatId=None, botId=None):
        sender = _TeleThread(mss, chatId, botId)
        sender.start()
        return sender

        

