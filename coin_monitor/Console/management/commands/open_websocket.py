import os
import sys
from threading import Thread
from time import sleep, time
import orjson
# import redis
import socketio     
import eventlet

from django.core.management.base import BaseCommand

from helper.Defaults import exceptionInfo
# from helper.Telegram import Tele
from helper.Redis import Redis
from helper.Jwt import Jwtoken
from helper.Reply import Reply

from models.Wrappers.nora_monitor_wrapper import ScraperWrapper
from models.nora_monitor import Scraper

sio = socketio.Server()

class Command(BaseCommand):
    help = 'Start opening a websocket server'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        
        try:

            app = socketio.WSGIApp(sio)

            sio.on('connect', self.onNewConnection)
            sio.on('disconnect', self.onDisconnect)
            sio.on('message', self.onMessage)
            sio.on('*', self.onAllEvent)
                
            sio.start_background_task(self.subcribeRedis)
            # os.environ['SIO'] = sio
            eventlet.wsgi.server(eventlet.listen(('', 5000)), app)

        except Exception as e:
            exInfo = exceptionInfo(e)
            # ms = "Lab socket " + exInfo['message'] + ": " 
            # ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
            # Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
            print(exInfo['message'])
    
    def onDisconnect(self, sid):
        scraper = ScraperWrapper().filter({
            ScraperWrapper.scraper_sid: sid
        })
        if(len(scraper) > 0):
            scraper = scraper[0] #type: Scraper
            scraper.scraper_status = 'DISCONNECTED'
            scraper.save()
            # Tele.send(f"{Tele.TELE_ICON_WARNING} [LAB] Node {scraper.scraper_name} disconnected", Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT)
            ms = f'[LAB] Node {scraper.scraper_name} disconnected'
            print(ms)
        
    def onNewConnection(self, sid, environ, auth):
        try:
            print('connect ', sid)
            print(environ)
            token = auth['token']
            payload = Jwtoken.getPayload(token)
            ip = environ['REMOTE_ADDR']
            if 'HTTP_CF_CONNECTING_IP' in environ:
                ip = environ['HTTP_CF_CONNECTING_IP']
            port = environ['REMOTE_PORT']
            name = payload['name']
            
            # Tele.send(f"{Tele.TELE_ICON_WARNING} [LAB] Node {name} connect from {ip}:{port}", Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT)

            scraper = ScraperWrapper().filter({
                ScraperWrapper.scraper_name: name
            })
            if(len(scraper) > 0):
                scraper = scraper[0] #type: Scraper
            else:
                scraper = ScraperWrapper().new({
                    ScraperWrapper.scraper_name : name,
                })
            print(scraper)
            scraper.scraper_ip = ip
            scraper.scraper_port = port
            scraper.scraper_sid = sid
            scraper.scraper_status = 'CONNECTED'     
            scraper.save()

        except Exception as e:
            exInfo = exceptionInfo(e)
            ms = "Lab socket " + exInfo['message'] + ": " 
            ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
            # Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
            print(ms)
            raise ConnectionRefusedError('Connection faild. ' + str(e))

    def onMessage(self, sid, data):
        try:
            data = Jwtoken.getPayload(data)
            Redis().publish("lab_order_result", data)
        except Exception as e:
            pass
    
    def onAllEvent(self, sid, data):
        try:
            data = Jwtoken.getPayload(data)
            print(data)
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
            print(message)
            if(message['type'] == 'message'):
                data = message['data']
                data = orjson.loads(data)
                server = data['socket_server']
                scraper = ScraperWrapper().filter({
                    ScraperWrapper.scraper_name: server
                })
                if(len(scraper) > 0):
                    scraper = scraper[0] #type: Scraper
                else:
                    data['response'] = Reply.make(False, 'Can not find any server')
                    Redis().publish("websocket_result", data)
                    return

                if(scraper.scraper_status != 'CONNECTED'):
                    data['response'] = Reply.make(False, 'Server is disconnected')
                    Redis().publish("websocket_result", data)
                    return
                
                sid = scraper.scraper_sid
                token = Jwtoken.getToken(data)
                sio.emit('message', token, sid)

        except Exception as e:
            if(data is not None):
                data['response'] = Reply.make(False, str(e))
                Redis().publish("websocket_result", data)
            else:
                ms = "Can not sent order to node. " + str(e)
                print(ms)
                # Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()


            
            
        
