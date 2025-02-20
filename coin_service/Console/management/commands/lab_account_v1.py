import os
import shutil
import sys
from time import time

from django.core.management.base import BaseCommand
from Console.Helper.Telegram import Tele
from Console.Phoenix.Lab_v1.AccountImp import AccountImp
from Console.Models.Coin_lab import LabAccount
from Console.Models.Wrappers.Lab.Coin_lab import LabAccountWrapper
from Console.Helper.Defaults import exceptionInfo
from crypto_lab.settings import WORK_DIR
class Command(BaseCommand):
    help = 'Start a Lab Account'

    def add_arguments(self, parser):
        parser.add_argument('id', nargs=1, type=int)
        parser.add_argument('--minute', action='store_true', default=False)
        parser.add_argument('--tail', action='store_true', default=True)

    def handle(self, *args, **options):
        accountId = options['id'][0]

        tempFolder = f"{WORK_DIR}/tmp/phoenix_opti_cache/tempFolder_0_{str(accountId)}"
    
        startPoint = time()
        
        accountImp = AccountImp(accountId)
        print(accountImp.run())

        shutil.rmtree(tempFolder, True)
        print("Total Time: " + str(time() - startPoint) + " seconds")



        # except Exception as e:
        #     shutil.rmtree(tempFolder, True)
        #     exInfo = exceptionInfo(e)
        #     ms = "LAB [" + str(accountId) + "] got the error. " + exInfo['message'] + ": " 
        #     ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
        #     Tele.send(ms, Tele.TELE_SIMULATE, Tele.TELE_BOT_DEFAULT).join()
        #     print(ms)
    