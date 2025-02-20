from threading import Thread
import requests

class _TeleThread (Thread):
    def __init__(self, mss, chatId, botId):
        Thread.__init__(self)
        self.mss = mss
        self.chatId = chatId
        self.botId = botId

    def run(self):
        requests.get('https://api.telegram.org/bot'+str(self.botId)+'/sendMessage', params={'chat_id': str(self.chatId), 'text': str(self.mss), 'parse_mode':"Markdown"})

class Telegram:

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
   
    TELE_BOT_DEFAULT = '5300881629:AAHc8x8IkK4hZlxbO1zBCJ9Ah1AdLfV7fhI'
    TELE_GROUP_DEFAULT = '-687731290'



    @staticmethod
    def send (mss, chatId=TELE_GROUP_DEFAULT, botId=TELE_BOT_DEFAULT, mention={}):
        if(chatId is None or botId is None or chatId == '' or botId == ''): return
        if(len(mention) > 0):
            mentionMs = []
            for uid in mention:
                mentionMs.append(f"[{mention[uid]}](tg://user?id={uid})")
            mss = " ".join(mentionMs) + " " + mss
        
        chatId = str(chatId)
        sender = _TeleThread(mss, chatId, botId)
        sender.start()
        return sender

        

