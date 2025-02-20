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
        
       
        try:
            # Create a socket object
            s = socket.socket()        
            # Define the port on which you want to connect
            port = 12345               
            # connect to the server on local computer
            s.connect(('127.0.0.1', port))
            # receive data from the server and decoding to get the string.
            while True:
                sleep(1)
                data = s.recv(1024)
                print(type(data))
                data = s.recv(1024).decode()
                print(type(data))
                if(not data is None): print(data)
            # close the connection
            s.close()    

        except Exception as e:
            exInfo = exceptionInfo(e)
            ms = "Lab socket " + exInfo['message'] + ": " 
            ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
            Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
            print(ms)
    



    
        
