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
from api.Helper.Jwt import Jwtoken
from api.Helper.Reply import Reply
from api.Controller import *
from dotenv import load_dotenv

load_dotenv()

sio = socketio.Client()


class Command(BaseCommand):
    help = "Start a Lab Account"

    def add_arguments(self, parser):
        # parser.add_argument('id', nargs=1, type=int)
        # parser.add_argument('--minute', action='store_true', default=False)
        # parser.add_argument('--tail', action='store_true', default=True)
        pass

    def handle(self, *args, **options):

        try:

            nodeName = os.getenv("NODE_NAME", "changeme")
            labCenter = os.getenv("LAB_CENTER", "http://14.225.16.78:5000")
            if nodeName == "changeme":
                raise Exception("Please change the NODE_NAME in file .env")

            @sio.event
            def connect():
                print("connection established")

            @sio.event
            def disconnect():
                print("disconnected from server")

            sio.on("message", self.onMessage)

            def createAuth():
                return {"token": Jwtoken.getToken({"name": nodeName})}

            sio.connect(labCenter, auth=createAuth)
            sio.wait()

        except Exception as e:
            exInfo = exceptionInfo(e)
            ms = "Lab socket " + exInfo["message"] + ": "
            ms += (
                "\n- File: "
                + os.path.basename(exInfo["file"])
                + ":"
                + str(exInfo["line"])
            )
            # Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
            print(ms)

    def onMessage(self, data):

        try:
            # Node nằm im hàng ngày giữa hai lệnh; MySQL đóng kết nối nhàn rỗi
            # từ phía nó nên phải dọn kết nối cũ trước khi xử lý, tránh lỗi
            # InterfaceError (0, '') ở truy vấn đầu tiên.
            close_old_connections()
            data = Jwtoken.getPayload(data)
            controller = data["order_socket_controller"]
            method = "_" + data["order_socket_method"]
            if not controller in globals():
                raise Exception(f"Can not find controller {controller}")
            module = globals()[controller]
            if not hasattr(module, method):
                raise Exception(
                    f"Can not find any method {method} in {controller}"
                )
            data["response"] = getattr(module, method)(data)
            token = Jwtoken.getToken(data)
            sio.emit("message", token)
        except Exception as e:
            exInfo = exceptionInfo(e)
            ms = "Lab socket " + exInfo["message"] + ": "
            ms += (
                "\n- File: "
                + os.path.basename(exInfo["file"])
                + ":"
                + str(exInfo["line"])
            )
            if data is not None:
                data["response"] = Reply.make(False, ms)
                token = Jwtoken.getToken(data)
                sio.emit("message", token)
            else:

                Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT)
                print(ms)
