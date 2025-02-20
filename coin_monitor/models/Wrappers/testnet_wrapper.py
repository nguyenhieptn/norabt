
# This is an auto-generated model wrapper singleton develope by LIN.
# This wrapper allow you to:
# - Set defaul using
# - Auto-fill the field of the model
# - Define some SQL relation over Register (preDropRegister)
# Feel free to rename the models, but don't rename db_table values or field names. 

from models.Wrappers.Model import Model
from models.testnet import *


class TestnetOrderWrapper(Model):
    
    testnet_order_id = 'testnet_order_id'
    testnet_order_time = 'testnet_order_time'
    testnet_order_account = 'testnet_order_account'
    testnet_order_action = 'testnet_order_action'
    testnet_order_symbol = 'testnet_order_symbol'
    testnet_order_qty = 'testnet_order_qty'
    testnet_order_price = 'testnet_order_price'
    testnet_order_commit = 'testnet_order_commit'
    testnet_order_pnl = 'testnet_order_pnl'
    testnet_order_baseon = 'testnet_order_baseon'
    testnet_order_type = 'testnet_order_type'
    testnet_order_phase = 'testnet_order_phase'
    
    def __init__(self):
        super().__init__(TestnetOrder, 'testnet')


class TestnetResultsWrapper(Model):
    
    testnet_result_id = 'testnet_result_id'
    testnet_result_campaign = 'testnet_result_campaign'
    testnet_result_strategy = 'testnet_result_strategy'
    testnet_result_group = 'testnet_result_group'
    testnet_result_container = 'testnet_result_container'
    testnet_result_symbol = 'testnet_result_symbol'
    testnet_result_chart = 'testnet_result_chart'
    testnet_result_enter_time = 'testnet_result_enter_time'
    testnet_result_enter_price = 'testnet_result_enter_price'
    testnet_result_order_time = 'testnet_result_order_time'
    testnet_result_order_price = 'testnet_result_order_price'
    testnet_result_order_qty = 'testnet_result_order_qty'
    testnet_result_order_phase = 'testnet_result_order_phase'
    testnet_result_order_release = 'testnet_result_order_release'
    testnet_result_high = 'testnet_result_high'
    testnet_result_low = 'testnet_result_low'
    testnet_result_type = 'testnet_result_type'
    testnet_result_base = 'testnet_result_base'
    testnet_result_params = 'testnet_result_params'
    testnet_result_start_reason = 'testnet_result_start_reason'
    testnet_result_status = 'testnet_result_status'
    testnet_result_matched_ema5 = 'testnet_result_matched_ema5'
    testnet_result_matched_price = 'testnet_result_matched_price'
    testnet_result_first_price = 'testnet_result_first_price'
    testnet_result_matched_time = 'testnet_result_matched_time'
    testnet_result_matched_qty = 'testnet_result_matched_qty'
    testnet_result_last_price = 'testnet_result_last_price'
    testnet_result_sell_price = 'testnet_result_sell_price'
    testnet_result_sell_time = 'testnet_result_sell_time'
    testnet_result_profit = 'testnet_result_profit'
    testnet_result_commit = 'testnet_result_commit'
    testnet_result_eventprofit = 'testnet_result_eventprofit'
    testnet_result_realprofit = 'testnet_result_realprofit'
    testnet_result_realpnl = 'testnet_result_realpnl'
    testnet_result_baseprofit = 'testnet_result_baseprofit'
    testnet_result_pending = 'testnet_result_pending'
    testnet_result_phase = 'testnet_result_phase'
    testnet_result_budget = 'testnet_result_budget'
    testnet_result_nextphase_note = 'testnet_result_nextphase_note'
    testnet_result_phase_note = 'testnet_result_phase_note'
    testnet_result_flow = 'testnet_result_flow'
    testnet_result_interval = 'testnet_result_interval'
    testnet_result_margin = 'testnet_result_margin'
    testnet_result_account = 'testnet_result_account'
    testnet_result_chart_price = 'testnet_result_chart_price'
    testnet_result_close_time = 'testnet_result_close_time'
    
    def __init__(self):
        super().__init__(TestnetResults, 'testnet')


class TestnetCampaignWrapper(Model):
    
    testnet_id = 'testnet_id'
    testnet_name = 'testnet_name'
    testnet_symbol = 'testnet_symbol'
    testnet_param = 'testnet_param'
    testnet_side = 'testnet_side'
    testnet_strategy = 'testnet_strategy'
    testnet_start_time = 'testnet_start_time'
    testnet_stop_time = 'testnet_stop_time'
    testnet_note = 'testnet_note'
    testnet_budget = 'testnet_budget'
    testnet_reserve = 'testnet_reserve'
    testnet_money = 'testnet_money'
    testnet_compound = 'testnet_compound'
    testnet_profit = 'testnet_profit'
    testnet_tele_bot = 'testnet_tele_bot'
    testnet_tele_gr_notice = 'testnet_tele_gr_notice'
    testnet_tele_gr_error = 'testnet_tele_gr_error'
    testnet_tele_gr_summary = 'testnet_tele_gr_summary'
    testnet_group = 'testnet_group'
    testnet_priority = 'testnet_priority'
    testnet_account = 'testnet_account'
    testnet_active_budget = 'testnet_active_budget'
    testnet_active = 'testnet_active'
    
    def __init__(self):
        super().__init__(TestnetCampaign, 'testnet')




class TestnetAccountWrapper(Model):
    
    testnet_account_id = 'testnet_account_id'
    testnet_account_name = 'testnet_account_name'
    testnet_account_balance = 'testnet_account_balance'
    testnet_account_reserve = 'testnet_account_reserve'
    testnet_account_compound = 'testnet_account_compound'
    testnet_account_note = 'testnet_account_note'
    testnet_account_margin_type = 'testnet_account_margin_type'
    testnet_account_runtime = 'testnet_account_runtime'
    
    def __init__(self):
        super().__init__(TestnetAccount, 'testnet')