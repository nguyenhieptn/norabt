import os
import sys
from Console.Helper.Defaults import *
from django.core.management.base import BaseCommand
from Console.Phoenix.Testnet.AccountImp import AccountImp
from Console.Helper.Telegram import Tele

class Command(BaseCommand):
    help = 'Start a Testnet Account'

    def add_arguments(self, parser):
        parser.add_argument('id', nargs=1, type=int)

    def handle(self, *args, **options):
        accountId = options['id'][0]
        try:
           
            processor = AccountImp(accountId)
            processor.initial()
            result = processor.run()
            if(not result['result']):
                raise Exception(result['message'])

        except Exception as e:
            exInfo = exceptionInfo(e)
            ms = "Testnet [" + str(accountId) + "] Stopped. " + exInfo['message'] + ": " 
            ms += "\n- File: " + os.path.basename(exInfo['file']) + ":" + str(exInfo['line'])
            print(ms)
            Tele.send(ms, Tele.TELE_TEST_ERROR, Tele.TELE_BOT_DEFAULT).join()
            os.system('systemctl stop testnet_account@' + str(accountId))
    