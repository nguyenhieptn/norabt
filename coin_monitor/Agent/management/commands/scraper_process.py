import os
import re
from time import time
from django.core.management.base import BaseCommand
import psutil

from models.Wrappers.nora_monitor_wrapper import ScraperProcessWrapper
from models.nora_monitor import ScraperProcess
from dotenv import load_dotenv

load_dotenv()

class Command(BaseCommand):
    
    help = 'Scrape all processes in the scraper and the information about RAM, CPU, command,...'

    def add_arguments(self, parser):
        # parser.add_argument('id', nargs=1, type=int)
        # parser.add_argument('--minute', action='store_true', default=False)
        # parser.add_argument('--tail', action='store_true', default=True)
        pass

    def handle_python_process(self, proc:psutil.Process):
        pInfoDict = proc.as_dict(attrs=['username','pid','cpu_percent','memory_percent','create_time','cmdline','status'])
        pInfoDict['time'] = sum(proc.cpu_times()[:2])
        pInfoDict['check_time'] = self.ctime
        cmdline = pInfoDict['cmdline']
        if 'manage.py' in cmdline[1]: #django
            del cmdline[1]
        
        scriptpath = cmdline[1] #type: str
        paths = scriptpath.split('/')
        script = paths[-1]
        if '-' in script: return None
        if '.py' in script:
            script = script[0:-3]
        pInfoDict['script'] = script
        arguments = cmdline[2:]
        
        pInfoDict['arguments'] = arguments
        symbol = [x for x in arguments if 'USDT' in x]
        if len(symbol) > 0:
            symbol = symbol[0]
        else:
            symbol = None
        pInfoDict['symbol'] = symbol
        return pInfoDict
    
    def handle(self, *args, **options):
        scraper_name = os.getenv("NODE_NAME", 'changeme')
        if(scraper_name == 'changeme'): raise Exception("Please change the NODE_NAME in file .env")
        
        scraper = ScraperProcessWrapper().edit({
            ScraperProcessWrapper.scraper_process_name: scraper_name
        },{
            'scraper_process_status': 0
        })
        self.ctime = time()
        for proc in psutil.process_iter():
            name = proc.name()
            if name in ['python']:
                pInfo = self.handle_python_process(proc)
                if pInfo is None: continue
                scraper = ScraperProcessWrapper().filter({
                    ScraperProcessWrapper.scraper_process_name:scraper_name,
                    ScraperProcessWrapper.scraper_process_script: pInfo['script'],
                    ScraperProcessWrapper.scraper_process_arguments: pInfo['arguments']
                })
                if(len(scraper) > 0):
                    scraper = scraper[0] #type: ScraperProcess
                else:
                    scraper = ScraperProcessWrapper().new({
                    ScraperProcessWrapper.scraper_process_name:scraper_name,
                    ScraperProcessWrapper.scraper_process_script: pInfo['script'],
                    ScraperProcessWrapper.scraper_process_arguments: pInfo['arguments']
                    })
                scraper.scraper_process_user = pInfo['username']
                scraper.scraper_process_pid = pInfo['pid']
                scraper.scraper_process_cmdline = pInfo['cmdline']
                scraper.scraper_process_cpu = pInfo['cpu_percent']
                scraper.scraper_process_ram = pInfo['memory_percent']
                scraper.scraper_process_start = pInfo['create_time']
                scraper.scraper_process_time = pInfo['time']
                scraper.scraper_process_check_time = pInfo['check_time']
                scraper.scraper_process_stt = pInfo['status']
                scraper.scraper_process_symbol = pInfo['symbol']
                scraper.scraper_process_status = 1
                scraper.save()