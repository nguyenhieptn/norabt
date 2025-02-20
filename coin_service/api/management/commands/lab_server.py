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

import socketio     
import eventlet

from api.Helper.Jwt import Jwtoken
from api.Models.Wrappers.coin_lab import LabNodeWrapper
from api.Models.coin_lab import LabNode
from api.Helper.Reply import Reply


sio = socketio.Server(max_http_buffer_size=10000000)

class Command(BaseCommand):
    help = 'Start a Lab Account'

    def add_arguments(self, parser):
        # parser.add_argument('id', nargs=1, type=int)
        # parser.add_argument('--minute', action='store_true', default=False)
        # parser.add_argument('--tail', action='store_true', default=True)
        pass

    def handle(self, *args, **options):
        
        try:

            app = socketio.WSGIApp(sio)

            sio.on('connect', self.onNewConnection)
            sio.on('disconnect', self.onDisconnect)
            sio.on('message', self.onMessage)
                
            sio.start_background_task(self.subcribeRedis)
           
            eventlet.wsgi.server(eventlet.listen(('', 5000)), app)

        except Exception as e:
            exInfo = exceptionInfo(e)
            ms = "Lab socket " + exInfo['message'] + ": " 
            ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
            Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
            print(ms)
    
    def onDisconnect(self, sid):
        labNode = LabNodeWrapper().filter({
            LabNodeWrapper.lab_node_sid: sid
        })
        if(len(labNode) > 0):
            labNode = labNode[0] #type: LabNode
            labNode.lab_node_status = 'DISCONNECTED'
            labNode.save()
            Tele.send(f"{Tele.TELE_ICON_WARNING} [LAB] Node {labNode.lab_node_name} disconnected", Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT)
        
    def onNewConnection(self, sid, environ, auth):
        try:
            print('connect ', sid)
            token = auth['token']
            payload = Jwtoken.getPayload(token)
            ip = environ['REMOTE_ADDR']
            port = environ['REMOTE_PORT']
            name = payload['name']
            
            Tele.send(f"{Tele.TELE_ICON_WARNING} [LAB] Node {name} connect from {ip}:{port}", Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT)

            labNode = LabNodeWrapper().filter({
                LabNodeWrapper.lab_node_name: name
            })
            if(len(labNode) > 0):
                labNode = labNode[0] #type: LabNode
            else:
                labNode = LabNodeWrapper().new({
                    LabNodeWrapper.lab_node_name : name,
                })
            labNode.lab_node_ip = ip
            labNode.lab_node_port = port
            labNode.lab_node_sid = sid
            labNode.lab_node_status = 'CONNECTED'
            labNode.save()

        except Exception as e:
            raise ConnectionRefusedError('Connection faild. ' + str(e))

    def onMessage(self, sid, data):

        try:
            data = Jwtoken.getPayload(data)
            Redis().publish("lab_order_result", data)
        except Exception as e:
            pass
    
    #Redis thead
    def subcribeRedis(self):
        channelName = "lab_order"
        try:
            pubsub = Redis().pubsub()
            pubsub.subscribe(channelName)
            while True:
                sio.sleep(0.01)
                message = pubsub.get_message()
                if(message is not None): 
                    self.onRedisMessage(message)
            # for message in pubsub.listen():
            #     if(message is not None): 
            #         self.onRedisMessage(message)
        except Exception as e:
            exInfo = exceptionInfo(e)
            ms = "Lab socket " + exInfo['message'] + ": " 
            ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
            # Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
            print(ms)

    def onRedisMessage(self, message):
        try:
            if(message['type'] == 'message'):
                data = message['data']
                data = orjson.loads(data)
                server = data['order_socket_server']
                labNode = LabNodeWrapper().filter({
                    LabNodeWrapper.lab_node_name: server
                })
                if(len(labNode) > 0):
                    labNode = labNode[0] #type: LabNode
                else:
                    data['response'] = Reply.make(False, 'Can not find any server')
                    Redis().publish("lab_order_result", data)
                    return

                if(labNode.lab_node_status != 'CONNECTED'):
                    data['response'] = Reply.make(False, 'Server is disconnected')
                    Redis().publish("lab_order_result", data)
                    return
                
                sid = labNode.lab_node_sid
                token = Jwtoken.getToken(data)
                sio.emit('message', token, sid)

        except Exception as e:
            if(data is not None):
                data['response'] = Reply.make(False, str(e))
                Redis().publish("lab_order_result", data)
            else:
                ms = "Can not sent order to node. " + str(e)
                Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()


            
            
        
