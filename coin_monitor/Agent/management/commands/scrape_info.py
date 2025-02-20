import os
import re
from time import time
from django.http import JsonResponse
from helper.Defaults import Number, Round
from helper.Reply import Reply
import psutil

from django.core.management.base import BaseCommand
from helper.Telegram import Telegram

from models.Wrappers.nora_monitor_wrapper import ScraperSystemWrapper, ScraperWrapper
from models.nora_monitor import Scraper
from dotenv import load_dotenv

load_dotenv()

class Command(BaseCommand):
    help = 'Scrape server RAM, CPU, DISK'
    diskPercent = 0
    cpuPercent = 0
    ramPercent = 0

    def add_arguments(self, parser):
        # parser.add_argument('id', nargs=1, type=int)
        # parser.add_argument('--minute', action='store_true', default=False)
        # parser.add_argument('--tail', action='store_true', default=True)
        pass

    def handle(self, *args, **options):
        scraper_name = os.getenv("NODE_NAME", 'changeme')
        if(scraper_name == 'changeme'): raise Exception("Please change the NODE_NAME in file .env")
        self.scraperName = scraper_name
        scraper = ScraperWrapper().filter({
            ScraperWrapper.scraper_name: scraper_name
        })
        if len(scraper) > 0:
            scraper = scraper[0]#type: Scraper
        else:
            scraper = ScraperWrapper().new({
                ScraperWrapper.scraper_name : scraper_name,
            })
        hdd = psutil.disk_usage('/')
        hdd2 = psutil.disk_usage('/data')
        memory = psutil.virtual_memory()

        diskPercent = 0
        if(hdd.total > 0): diskPercent =  hdd.percent
        self.diskPercent = diskPercent
        diskPercent2 = hdd2.percent
        self.diskPercent2 = diskPercent2
        self.cpuPercent = cpuPercent = Round(psutil.cpu_percent(), 2)
        self.ramPercent = ramPercent = Round(memory[2], 2)
        

        # Make alert
        if(diskPercent > 95): self.makeAlert(f"SSD đã sử dụng {diskPercent}%", 'danger')
        if(diskPercent2 > 95): self.makeAlert(f"HDD đã sử dụng {diskPercent}%", 'danger')
        if(ramPercent > 95): self.makeAlert(f"RAM đã sử dụng {ramPercent}%", 'danger')
        if(cpuPercent > 95): self.makeAlert(f"CPU đã sử dụng {cpuPercent}%", 'danger')
        diskDiff = Round(diskPercent - Number(scraper.scraper_disk), 2)
        if(diskDiff > 10): self.makeAlert(f"SSD tăng {diskDiff}%", 'warning')
        if(diskDiff < -10): self.makeAlert(f"SSD giảm {diskDiff}%", 'ok')
        cpuDiff = Round(cpuPercent - Number(scraper.scraper_cpu), 2)
        if(cpuDiff > 10): self.makeAlert(f"CPU tăng {cpuDiff}%", 'warning')
        if(cpuDiff < -10): self.makeAlert(f"CPU giảm {cpuDiff}%", 'ok')
        ramDiff = Round(ramPercent - Number(scraper.scraper_ram), 2)
        if(ramDiff > 10): self.makeAlert(f"RAM tăng {ramDiff}%", 'warning')
        if(ramDiff < -10): self.makeAlert(f"RAM giảm {ramDiff}%", 'ok')


        scraper.scraper_cpu = cpuPercent
        scraper.scraper_ram = ramPercent
        scraper.scraper_disk = diskPercent
        scraper.scraper_ram_total = Round(memory[0])
        scraper.scraper_cpu_total = psutil.cpu_count()
        scraper.scraper_disk_total = Round(hdd.total)
        scraper.save()
        scraper_system = ScraperSystemWrapper().new({
            ScraperSystemWrapper.scraper_sys_time : time(),
            ScraperSystemWrapper.scraper_sys_name : scraper_name,
            ScraperSystemWrapper.scraper_sys_cpu : scraper.scraper_cpu,
            ScraperSystemWrapper.scraper_sys_ram : scraper.scraper_ram,
            ScraperSystemWrapper.scraper_sys_disk : scraper.scraper_disk,
            ScraperSystemWrapper.scraper_sys_ram_total : scraper.scraper_ram_total,
            ScraperSystemWrapper.scraper_sys_cpu_total : scraper.scraper_cpu_total,
            ScraperSystemWrapper.scraper_sys_disk_total : scraper.scraper_disk_total,
        }) #type: ScraperWrapper
        scraper_system.save()
        # print(scraper_system.__dict__)

    def makeAlert(self, mss, level='warning'):
        icon = Telegram.TELE_ICON_WARNING
        if(level == 'danger'): icon = Telegram.TELE_ICON_ERROR
        if(level == 'ok'): icon = Telegram.TELE_ICON_TAKEPROFIT
        message = f'''{icon} {mss}
- Server Name : {self.scraperName}
- SSD: {self.diskPercent}%
- HDD: {self.diskPercent2}%
- RAM: {self.ramPercent}%
- CPU: {self.cpuPercent}%
'''
        Telegram.send(message, Telegram.TELE_GROUP_DEFAULT, Telegram.TELE_BOT_DEFAULT, {693919513: "LIN"})