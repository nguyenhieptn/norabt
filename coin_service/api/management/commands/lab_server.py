import os
import sys
from threading import Thread
from time import sleep, time
import orjson
import redis
from django.core.management.base import BaseCommand
from django.db import close_old_connections, connections

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
           
            # Bind localhost: lab_client chạy cùng máy, không cần mở ra Internet.
            # Đổi qua env nếu sau này có node từ xa.
            host = os.getenv("LAB_SERVER_HOST", "127.0.0.1")
            port = int(os.getenv("LAB_SERVER_PORT", "5000"))
            print(f"Lab server listening on {host}:{port}")
            eventlet.wsgi.server(eventlet.listen((host, port)), app)

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
            # Không báo Telegram cho node local (group chung là của hệ thống production)
            print(f"[LAB] Node {labNode.lab_node_name} disconnected")
        
    def onNewConnection(self, sid, environ, auth):
        try:
            print('connect ', sid)
            token = auth['token']
            payload = Jwtoken.getPayload(token)
            ip = environ['REMOTE_ADDR']
            port = environ['REMOTE_PORT']
            name = payload['name']
            
            print(f"[LAB] Node {name} connect from {ip}:{port}")

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
            # Dùng trạng thái riêng (mặc định LOCAL) để cron giám sát của hệ thống
            # production (dùng chung MySQL) không hỏi node này rồi báo lỗi Telegram.
            labNode.lab_node_status = os.getenv('LAB_NODE_STATUS', 'LOCAL')
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

    def timNode(self, server):
        """Tra cứu node, tự nối lại nếu kết nối MySQL đã chết.

        Tiến trình này chạy nhiều ngày liền và có thể nằm im rất lâu giữa hai
        lệnh; MySQL đóng kết nối nhàn rỗi từ phía nó mà Django không hay biết,
        nên truy vấn đầu tiên sau đó ném InterfaceError (0, '') và người dùng
        chỉ thấy đúng chuỗi đó thay vì lệnh được chạy.
        """
        close_old_connections()
        for lan in range(2):
            try:
                return LabNodeWrapper().filter({
                    LabNodeWrapper.lab_node_name: server
                })
            except Exception:
                if lan:
                    raise
                connections.close_all()   # bỏ kết nối hỏng rồi thử lại một lần

    def onRedisMessage(self, message):
        try:
            if(message['type'] == 'message'):
                data = message['data']
                data = orjson.loads(data)
                server = data['order_socket_server']
                labNode = self.timNode(server)
                if(len(labNode) > 0):
                    labNode = labNode[0] #type: LabNode
                else:
                    data['response'] = Reply.make(False, 'Can not find any server')
                    Redis().publish("lab_order_result", data)
                    return

                if(labNode.lab_node_status != os.getenv('LAB_NODE_STATUS', 'LOCAL')):
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


            
            
        
