from datetime import datetime
from math import floor
import os

from django.core.management.base import BaseCommand
import requests
import json
from threading import Thread

from djongo import models

import eventlet
import socketio
from helper.Telegram import Telegram

from helper.Websocket import Websocket

class Command(BaseCommand):
    help = 'Crawl Kline data 1m'

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
       

    def add_arguments(self, parser):
        # parser.add_argument("--symbols", nargs="*", default=None)
        pass

    
    def handle(self, *args, **options):
        Telegram.send("test mention", Telegram.TELE_GROUP_DEFAULT, Telegram.TELE_BOT_DEFAULT, {693919513: "Mr LIN"})
