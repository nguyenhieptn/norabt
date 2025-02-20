
# This is an auto-generated model wrapper singleton develope by LIN.
# This wrapper allow you to:
# - Set defaul using
# - Auto-fill the field of the model
# - Define some SQL relation over Register (preDropRegister)
# Feel free to rename the models, but don't rename db_table values or field names. 

from models.Wrappers.Model import Model
from models.nora_monitor import *


class ScraperWrapper(Model):
    
    _id = '_id'
    scraper_name = 'scraper_name'
    scraper_ip = 'scraper_ip'
    scraper_cpu = 'scraper_cpu'
    scraper_cpu_total = 'scraper_cpu_total'
    scraper_ram = 'scraper_ram'
    scraper_ram_total = 'scraper_ram_total'
    scraper_disk = 'scraper_disk'
    scraper_disk_total = 'scraper_disk_total'
    scraper_status = 'scraper_status'
    scraper_port = 'scraper_port'
    scraper_sid = 'scraper_sid'
    scraper_note = 'scraper_note'
    
    def __init__(self):
        super().__init__(Scraper, 'nora_monitor')
        self.preDropRegister(ScraperSystemWrapper(), ScraperWrapper.scraper_name, ScraperSystemWrapper.scraper_sys_name, Model.CASCADE)


class ScraperSystemWrapper(Model):
    
    _id = '_id'
    scraper_sys_name = 'scraper_sys_name'
    scraper_sys_time = 'scraper_sys_time'
    scraper_sys_cpu = 'scraper_sys_cpu'
    scraper_sys_cpu_total = 'scraper_sys_cpu_total'
    scraper_sys_ram = 'scraper_sys_ram'
    scraper_sys_ram_total = 'scraper_sys_ram_total'
    scraper_sys_disk = 'scraper_sys_disk'
    scraper_sys_disk_total = 'scraper_sys_disk_total'
    
    def __init__(self):
        super().__init__(ScraperSystem, 'nora_monitor')

class ScraperProcessWrapper(Model):
    
    _id = '_id'    
    scraper_process_name = 'scraper_process_name'
    scraper_process_script = 'scraper_process_script'
    scraper_process_symbol = 'scraper_process_symbol'
    scraper_process_arguments = 'scraper_process_arguments'
    scraper_process_cmdline = 'scraper_process_cmdline'
    scraper_process_user = 'scraper_process_user'
    scraper_process_ram = 'scraper_process_ram'
    scraper_process_cpu = 'scraper_process_cpu'
    scraper_process_pid = 'scraper_process_pid'
    scraper_process_start = 'scraper_process_start'
    scraper_process_time = 'scraper_process_time'
    scraper_process_check_time = 'scraper_process_check_time'
    scraper_process_stt = 'scraper_process_stt'
    scraper_process_status = 'scraper_process_status'
    
    def __init__(self):
        super().__init__(ScraperProcess, 'nora_monitor')

class ScraperCoinWrapper(Model):
    
    _id = '_id'
    scraper_coin_name = 'scraper_coin_name'
    scraper_coin_type = 'scraper_coin_type'
    scraper_coin_symbol = 'scraper_coin_symbol'
    scraper_coin_time = 'scraper_coin_time'
    scraper_coin_status = 'scraper_coin_status'
    
    def __init__(self):
        super().__init__(ScraperCoin, 'nora_monitor')
