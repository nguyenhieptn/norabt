import os
import sys
from threading import Thread
from time import sleep, time
import orjson
from django.core.management.base import BaseCommand

from helper.Defaults import exceptionInfo
# from helper.Telegram import Tele
from helper.Redis import Redis

from helper.Jwt import Jwtoken
from helper.Reply import Reply         
# from Controller import *
from dotenv import load_dotenv

load_dotenv()

import socketio

sio = socketio.Client()

class Command(BaseCommand):
    help = 'Connect to websocket server'

    def add_arguments(self, parser):
        # parser.add_argument('id', nargs=1, type=int)
        # parser.add_argument('--minute', action='store_true', default=False)
        # parser.add_argument('--tail', action='store_true', default=True)
        pass

    def handle(self, *args, **options):
        
        try:

            nodeName = os.getenv("NODE_NAME", 'changeme')
            labCenter = os.getenv("WEBSOCKET_SERVER", 'https://monitor.f5traders.com')
            if(nodeName == 'changeme'): raise Exception("Please change the NODE_NAME in file .env")
            @sio.event
            def connect():
                print('connection established')

            @sio.event
            def disconnect():
                print('disconnected from server')

            sio.on('message', self.onMessage)

            def createAuth():
                return {"token": Jwtoken.getToken({'name': nodeName})}
                

            sio.connect(labCenter, auth=createAuth)
            sio.wait()

        except Exception as e:
            exInfo = exceptionInfo(e)
            ms = "Lab socket " + exInfo['message'] + ": " 
            ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
            # Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
            print(ms)


    def onMessage(self, data):
        
        try:
            data = Jwtoken.getPayload(data)
            controller = data['order_socket_controller']
            method = '_' + data['order_socket_method']
            if not controller in globals(): raise Exception(f"Can not find controller {controller}")
            module = globals()[controller]
            if(not hasattr(module, method)): raise Exception(f"Can not find any method {method} in {controller}")
            data['response'] = getattr(module, method)(data)
            token = Jwtoken.getToken(data)
            sio.emit('message', token)
        except Exception as e:
            if(data is not None):
                data['response'] = Reply.make(False, str(e))
                token = Jwtoken.getToken(data)
                sio.emit('message', token)
            else:
                exInfo = exceptionInfo(e)
                ms = "Lab socket " + exInfo['message'] + ": " 
                ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
                # Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT)
                print(ms)
    



    
        
