
# This is an auto-generated model wrapper singleton develope by LIN.
# This wrapper allow you to:
# - Set defaul using
# - Auto-fill the field of the model
# - Define some SQL relation over Register (preDropRegister)
# Feel free to rename the models, but don't rename db_table values or field names. 

from api.Models.Wrappers.Model import Model
from api.Models.coin_lab import *


class LabNodeWrapper(Model):
    
    lab_node_id = 'lab_node_id'
    lab_node_name = 'lab_node_name'
    lab_node_ip = 'lab_node_ip'
    lab_node_port = 'lab_node_port'
    lab_node_sid = 'lab_node_sid'
    lab_node_status = 'lab_node_status'
    lab_node_ram = 'lab_node_ram'
    lab_node_ram_total = 'lab_node_ram_total'
    lab_node_cpu = 'lab_node_cpu'
    lab_node_cpu_core = 'lab_node_cpu_core'
    lab_node_disk = 'lab_node_disk'
    lab_node_disk_total = 'lab_node_disk_total'
    lab_node_note = 'lab_node_note'
    
    def __init__(self):
        super().__init__(LabNode, 'default')


class LabAccountWrapper(Model):

    lab_account_id = 'lab_account_id'
    lab_account_name = 'lab_account_name'
    lab_account_balance = 'lab_account_balance'
    lab_account_margin_balance = 'lab_account_margin_balance'
    lab_account_reserve = 'lab_account_reserve'
    lab_account_compound = 'lab_account_compound'
    lab_account_note = 'lab_account_note'
    lab_account_margin_type = 'lab_account_margin_type'
    lab_account_track_balance = 'lab_account_track_balance'
    lab_account_running = 'lab_account_running'
    lab_account_sync = 'lab_account_sync'
    lab_account_log = 'lab_account_log'
    lab_account_leap = 'lab_account_leap'
    lab_account_db = 'lab_account_db'
    lab_account_data_type = 'lab_account_data_type'
    lab_account_params = 'lab_account_params'
    lab_account_choice_strategy = 'lab_account_choice_strategy'
    lab_account_choice_period = 'lab_account_choice_period'
    lab_account_choice_result = 'lab_account_choice_result'

    def __init__(self):
        super().__init__(LabAccount, 'default')


class LabOptimizationWrapper(Model):
    
    lab_opt_id = 'lab_opt_id'
    lab_opt_name = 'lab_opt_name'
    lab_opt_account = 'lab_opt_account'
    lab_opt_params = 'lab_opt_params'
    lab_opt_thread = 'lab_opt_thread'
    lab_opt_note = 'lab_opt_note'
    lab_opt_log = 'lab_opt_log'
    lab_opt_start_time = 'lab_opt_start_time'
    lab_opt_stop_time = 'lab_opt_stop_time'
    lab_opt_processed = 'lab_opt_processed'
    lab_opt_data_leng = 'lab_opt_data_leng'
    lab_opt_server = 'lab_opt_server'
    
    def __init__(self):
        super().__init__(LabOptimization, 'default')

