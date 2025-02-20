from datetime import datetime
from dateutil import tz
import os
import re
from time import time
from django.core.management.base import BaseCommand
import psutil
from pymongo import MongoClient

from dotenv import load_dotenv
from models.Wrappers.nora_monitor_wrapper import ScraperCoinWrapper

from models.nora_monitor import ScraperCoin

load_dotenv()

class Command(BaseCommand):
    
    help = 'Monitoring data to check the scripts scraper data is working or stopped'

    def add_arguments(self, parser):
        # parser.add_argument('id', nargs=1, type=int)
        # parser.add_argument('--minute', action='store_true', default=False)
        # parser.add_argument('--tail', action='store_true', default=True)
        pass

    def handle_python_process(self, proc:psutil.Process):
        pass
    
    def handle(self, *args, **options):
        VN_TZ = tz.gettz('Asia/Ho_Chi_Minh')
        scraper_name = os.getenv("NODE_NAME", 'changeme')
        if(scraper_name == 'changeme'): raise Exception("Please change the NODE_NAME in file .env")
        host = os.getenv("DB_HOST", '127.0.0.1')
        port = int(os.getenv("DB_PORT", 27023))
        username = os.getenv("DB_USERNAME", None)
        password = os.getenv("DB_PASSWORD", None)
        authsource = os.getenv("DB_AUTHSOURCE", None)
        port = int(os.getenv("DB_PORT", 27023))
        db_name = os.getenv("DB_NAME", 'coin')
        today = datetime.now(VN_TZ)
        day = today.strftime("%Y_%m_%d")
        db = MongoClient(host=host, port=port, username=username, password=password, authSource=authsource)[db_name]
        print(f"Server name {scraper_name}")
        try:
            collections = db.list_collection_names(filter={"name": {"$regex": r"^"+day}})
            for collection in collections:
                regex = re.search(r'\d{4}_\d{2}_\d{2}_(?P<symbol>[^_]*)_(?P<type>[\w_]*)', collection)
                symbol = regex['symbol']
                type = regex['type']
                coll = db.get_collection(collection)
                last_record = coll.find_one({},{'_id':0,'E':1,'time':1},sort=[['_id',-1]])
                last_time = None
                status = 1
                if 'E' in last_record:
                    last_time = last_record['E']
                if 'time' in last_record:
                    last_time = round(last_record['time'] * 1000)

                if time() * 1000 - last_time > 3*60*1000:
                    status = 0
                
                scraper = ScraperCoinWrapper().filter({
                    ScraperCoinWrapper.scraper_coin_name:scraper_name,
                    ScraperCoinWrapper.scraper_coin_symbol: symbol,
                    ScraperCoinWrapper.scraper_coin_type: type
                })
                if(len(scraper) > 0):
                    scraper = scraper[0] #type: ScraperCoin
                else:
                    scraper = ScraperCoinWrapper().new({
                        ScraperCoinWrapper.scraper_coin_name:scraper_name,
                        ScraperCoinWrapper.scraper_coin_symbol: symbol,
                        ScraperCoinWrapper.scraper_coin_type: type
                    })
                scraper.scraper_coin_status = status
                scraper.scraper_coin_time = last_time
                scraper.save()
                # print(collections)
        except Exception as e:
            print(str(e))
            pass