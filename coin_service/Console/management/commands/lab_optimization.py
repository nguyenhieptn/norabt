import os
import sys
from time import time
from Console.Helper.Defaults import *
from django.core.management.base import BaseCommand
from Console.Helper.Telegram import Tele
from Console.Phoenix.Lab.Optimization import Optimization

class Command(BaseCommand):
    help = 'Start a Lab Optimization'

    def add_arguments(self, parser):
        parser.add_argument('id', nargs=1, type=int)
        parser.add_argument('--minute', action='store_true', default=False)
        parser.add_argument('--continue', action='store_true', default=False)
        parser.add_argument('--tail', action='store_true', default=True)

    def handle(self, *args, **options):
        id = options['id'][0]
        iscontinue = options['continue']
        
        try:
            optimization = Optimization(id, iscontinue)
            optimization.initial()
            optimization.start()

        except Exception as e:
            exInfo = exceptionInfo(e)
            ms = "Optimization [" + str(id) + "] got the error. " + exInfo['message'] + ": " 
            ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
            Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
            print(ms)
    