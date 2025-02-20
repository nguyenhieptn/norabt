from datetime import datetime
from dateutil import tz

from django.core.management.base import BaseCommand
from helper.Defaults import *
from helper.Data import *

import subprocess


VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')

class Command(BaseCommand):
    help = 'Run multi campaign'
    
    #python manage.py bot_campaign -s pair_trading_band -c pair_trading_band > ./Backtest/BOT/Logs/pair_trading_band.log

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        listOfCamp = [
            # 'pair13_trading_band_5m_3std',
            # 'pair13_trading_band_10m_3std',
            # 'pair13_trading_band_30m_3std',
            # 'pair13_trading_band_45m_3std',
            # 'pair13_trading_band_60m_3std',
            # 'pair_trading_band_30m_3std_50',
            # 'pair_trading_band_30m_3std_unlimit',
            # 'pair_trading_band_30m_3std_100'
            # 'pair_trading_band_10m_1.5std_3std',
            # 'pair_trading_band_20m_1.5std_3std',
            # 'pair_trading_band_40m_1.5std_3std',
            # 'pair_trading_band_60m_1.5std_3std',
            # 'pair_trading_stat_1',
            # 'pair_trading_stat_2',
            # 'pair_trading_band_10m_mid',
            # 'pair_trading_band_10m_upper',
            # 'pair_trading_band_10m_lower',
            # 'pair_trading_band_40m_mid',
            # 'pair_trading_band_40m_upper',
            # 'pair_trading_band_40m_upper_best2',
            # 'pair_trading_band_40m_mid',
            # 'pair_trading_band_40m_mid_best2',
            # 'pair_trading_band_40m_lower',
            # 'pair_trading_band_40m_lower_best2',
            # 'pair_trading_band_40m_lower',
            # 'pair_trading_band_10m_mid_1',
            # 'pair_trading_band_10m_upper_1',
            # 'pair_trading_band_10m_lower_1',
            # 'pair_trading_band_40m_mid_1',
            # 'pair_trading_band_40m_upper_1',
            # 'pair_trading_band_40m_lower_1',
            # 'pair_trading_band_40m_upper_2',
            # 'pair_trading_band_40m_lower_2',
            # 'pair_trading_band_40m_upper',
            # 'pair_trading_band_40m_upper_slip',
            # 'pairlong_trading_band_120m_upper',
            # 'pairlong_trading_band_120m_lower',
            # 'pairlong_trading_band_180m_upper',
            # 'pairlong_trading_band_180m_lower',
            # 'pairlong_trading_band_240m_upper',
            # 'pairlong_trading_band_240m_lower',
            'pair_trading_band_60m_fishing_invert',
            'pair_trading_band_60m_fishing_normal'
        ]
        
        proes = []
        for camp in listOfCamp:
            cmd = f"python /home/ubuntu/linhvhv/coin_monitor/manage.py bot_campaign -c {camp} > /home/ubuntu/linhvhv/coin_monitor/Backtest/BOT/Logs/{camp}.log"
            pro = subprocess.Popen(cmd, shell=True)
            proes.append(pro)
        
        for pro in proes:
            pro.wait()
            
       

           
    
        





        
        
        
        

    
        
        





        

        

        







        

        


    