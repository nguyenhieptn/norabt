import os
import sys
from threading import Thread
from time import sleep, time
import orjson
import redis
from django.core.management.base import BaseCommand

from api.Helper.Defaults import exceptionInfo
from api.Helper.Telegram import Tele
from api.Helper.Redis import Redis

import socket            

class Command(BaseCommand):
    help = 'Start a Lab Account'

    def add_arguments(self, parser):
        # parser.add_argument('id', nargs=1, type=int)
        # parser.add_argument('--minute', action='store_true', default=False)
        # parser.add_argument('--tail', action='store_true', default=True)
        pass

    def handle(self, *args, **options):
        
        
        # try:
            self.listConnection = []
            s = socket.socket()        
            print ("Socket successfully created")
            port = 12345   
            s.bind(('0.0.0.0', port))        
            print ("socket binded to %s" %(port))
            s.listen(5)    
            print ("socket is listening")  


            redisThread = Thread(target=self.subcribeRedis, args=[self.onMessage])
            redisThread.start()

            newConThread = Thread(target=self.processNewConnection, args=[s])
            newConThread.start()

            



        # except Exception as e:
        #     exInfo = exceptionInfo(e)
        #     ms = "Lab socket " + exInfo['message'] + ": " 
        #     ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
        #     Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
        #     print(ms)
    




    def processNewConnection(self, socket):
        while True:
            # Establish connection with client.
            c, addr = socket.accept()    
            
            print ('Got connection from', addr )
            
            # send a thank you message to the client. encoding to send byte type.
            c.send('Thank you for connecting'.encode())
            
            # Close the connection with the client
            self.listConnection.append({
                'addr': addr,
                'socket': c
            })
            print("Total connection: " + str(len(self.listConnection)))





    def subcribeRedis(self, callback):
        channelName = "lab_order"
        try:
            pubsub = Redis().pubsub()
            pubsub.subscribe(channelName)
            while True:
                sleep(1)
                ms = pubsub.get_message()
                if(ms is not None): 
                    callback(ms)
        except Exception as e:
            exInfo = exceptionInfo(e)
            ms = "Lab socket " + exInfo['message'] + ": " 
            ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
            # Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
            print(ms)



    def onMessage(self, message:str):
        # message = orjson.loads(message)
        print(message['data'])
        for conn in self.listConnection:
            c = conn['socket']
            c.send(str(message['data']).encode())
        
