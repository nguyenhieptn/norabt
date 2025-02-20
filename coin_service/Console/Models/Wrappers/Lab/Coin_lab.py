
# This is an auto-generated model wrapper develope by LIN.
# This wrapper allow you to:
# - Set defaul using
# - Auto-fill the field of the model
# - Define some SQL relation over Register (preDropRegister)
# Feel free to rename the models, but don't rename db_table values or field names.

from Console.Models.Wrappers.Model import Model
from Console.Models.Coin_lab import *


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
    lab_account_data_length = 'lab_account_data_length'
    lab_account_params = 'lab_account_params'
    lab_account_choice_strategy = 'lab_account_choice_strategy'
    lab_account_choice_period = 'lab_account_choice_period'
    lab_account_choice_result = 'lab_account_choice_result'

    def __init__(self):
        super().__init__(LabAccount, 'default')


class LabCampaignsWrapper(Model):

    lab_campaign_id = 'lab_campaign_id'
    lab_campaign_name = 'lab_campaign_name'
    lab_campaign_symbol = 'lab_campaign_symbol'
    lab_campaign_start = 'lab_campaign_start'
    lab_campaign_stop = 'lab_campaign_stop'
    lab_campaign_params = 'lab_campaign_params'
    lab_campaign_side = 'lab_campaign_side'
    lab_campaign_strategy = 'lab_campaign_strategy'
    lab_campaign_status = 'lab_campaign_status'
    lab_campaign_running = 'lab_campaign_running'
    lab_campaign_last = 'lab_campaign_last'
    lab_campaign_budget = 'lab_campaign_budget'
    lab_campaign_reserve = 'lab_campaign_reserve'
    lab_campaign_compound = 'lab_campaign_compound'
    lab_campaign_profit = 'lab_campaign_profit'
    lab_campaign_account = 'lab_campaign_account'
    lab_campaign_money = 'lab_campaign_money'
    lab_campaign_active_budget = 'lab_campaign_active_budget'
    lab_campaign_priority = 'lab_campaign_priority'
    lab_campaign_runtime = 'lab_campaign_runtime'
    lab_campaign_log = 'lab_campaign_log'

    LAB_CAMPAIGN_PARAMS_LOG = 'lab_campaign_params_log'
    LAB_CAMPAIGN_PARAMS_LOG_ORDER = 'lab_campaign_params_log_order'
    LAB_CAMPAIGN_PARAMS_LOG_RSI = 'lab_campaign_params_log_rsi'

    TELE_SIMULATE = '546311985'
    TELE_SIMULATE_ERROR = '529215337'
    TELE_BOT_DEFAULT = '1820957497:AAHiWTbuO-Kp80dFWB_7d74bfvHlOnBIJ08'


    def __init__(self):
        super().__init__(LabCampaigns, 'default')


class LabEventLogsWrapper(Model):

   
    lab_elog_id = 'lab_elog_id'
    lab_elog_campaign = 'lab_elog_campaign'
    lab_elog_symbol = 'lab_elog_symbol'
    lab_elog_time = 'lab_elog_time'
    lab_elog_chart = 'lab_elog_chart'
    lab_elog_result = 'lab_elog_result'
    lab_elog_maxprofit = 'lab_elog_maxprofit'
    lab_elog_minprofit = 'lab_elog_minprofit'
    lab_elog_profit = 'lab_elog_profit'
    lab_elog_baseprofit = 'lab_elog_baseprofit'
    lab_elog_status = 'lab_elog_status'
    lab_elog_matched = 'lab_elog_matched'
    lab_elog_base = 'lab_elog_base'

    def __init__(self):
        super().__init__(LabEventLogs, 'default')


class LabOrderWrapper(Model):

   
    lab_order_id = 'lab_order_id'
    lab_order_time = 'lab_order_time'
    lab_order_action = 'lab_order_action'
    lab_order_symbol = 'lab_order_symbol'
    lab_order_qty = 'lab_order_qty'
    lab_order_price = 'lab_order_price'
    lab_order_commit = 'lab_order_commit'
    lab_order_pnl = 'lab_order_pnl'
    lab_order_baseon = 'lab_order_baseon'
    lab_order_type = 'lab_order_type'
    lab_order_phase = 'lab_order_phase'
    lab_order_account = 'lab_order_account'

    def __init__(self):
        super().__init__(LabOrder, 'default')


class LabResultsWrapper(Model):

    
    lab_result_id = 'lab_result_id'
    lab_result_campaign = 'lab_result_campaign'
    lab_result_strategy = 'lab_result_strategy'
    lab_result_symbol = 'lab_result_symbol'
    lab_result_chart = 'lab_result_chart'
    lab_result_chart_price = 'lab_result_chart_price'
    lab_result_enter_time = 'lab_result_enter_time'
    lab_result_enter_price = 'lab_result_enter_price'
    lab_result_order_time = 'lab_result_order_time'
    lab_result_order_price = 'lab_result_order_price'
    lab_result_order_qty = 'lab_result_order_qty'
    lab_result_order_phase = 'lab_result_order_phase'
    lab_result_order_release = 'lab_result_order_release'
    lab_result_high = 'lab_result_high'
    lab_result_low = 'lab_result_low'
    lab_result_type = 'lab_result_type'
    lab_result_base = 'lab_result_base'
    lab_result_params = 'lab_result_params'
    lab_result_start_reason = 'lab_result_start_reason'
    lab_result_status = 'lab_result_status'
    lab_result_matched_price = 'lab_result_matched_price'
    lab_result_first_price = 'lab_result_first_price'
    lab_result_matched_time = 'lab_result_matched_time'
    lab_result_matched_qty = 'lab_result_matched_qty'
    lab_result_last_price = 'lab_result_last_price'
    lab_result_matched_ema5 = 'lab_result_matched_ema5'
    lab_result_sell_price = 'lab_result_sell_price'
    lab_result_sell_time = 'lab_result_sell_time'
    lab_result_profit = 'lab_result_profit'
    lab_result_commit = 'lab_result_commit'
    lab_result_eventprofit = 'lab_result_eventprofit'
    lab_result_realprofit = 'lab_result_realprofit'
    lab_result_realpnl = 'lab_result_realpnl'
    lab_result_baseprofit = 'lab_result_baseprofit'
    lab_result_pending = 'lab_result_pending'
    lab_result_phase = 'lab_result_phase'
    lab_result_budget = 'lab_result_budget'
    lab_result_flow = 'lab_result_flow'
    lab_result_log = 'lab_result_log'
    lab_result_interval = 'lab_result_interval'
    lab_result_btc_wma45_1d = 'lab_result_btc_wma45_1d'
    lab_result_btc_wma45_1w = 'lab_result_btc_wma45_1w'
    lab_result_container = 'lab_result_container'
    lab_result_account = 'lab_result_account'
    lab_result_margin = 'lab_result_margin'
    lab_result_close_time = 'lab_result_close_time'

    LAB_RESULT_TYPE_LONG = 1
    LAB_RESULT_TYPE_SHORT = 2

    LAB_RESULT_STATUS_PENDING = 0
    LAB_RESULT_STATUS_MATCHED = 1
    LAB_RESULT_STATUS_TAKEPROFIT = 2
    LAB_RESULT_STATUS_STOPLOSS = 3
    LAB_RESULT_STATUS_CANCLE = 4
    LAB_RESULT_STATUS_STOP_PENDING = 5
    LAB_RESULT_STATUS_ENTER_WAITTING = 6
    LAB_RESULT_STATUS_MATCHED_PART = 7
    LAB_RESULT_STATUS_PHASE_PENDING = 8
    LAB_RESULT_STATUS_RELEASE_WAITTING = 9
    LAB_RESULT_STATUS_RELEASE_PENDING = 10

    def __init__(self):
        super().__init__(LabResults, 'default')
        self.preDropRegister(LabOrderWrapper(), 'lab_result_id', 'lab_order_action', self.CASCADE)


class LabStrategiesWrapper(Model):

    
    lab_strategy_id = 'lab_strategy_id'
    lab_strategy_name = 'lab_strategy_name'
    lab_strategy_content = 'lab_strategy_content'
    lab_strategy_takeprofit = 'lab_strategy_takeprofit'
    lab_strategy_stoploss = 'lab_strategy_stoploss'
    lab_strategy_baseprofit = 'lab_strategy_baseprofit'
    lab_strategy_stepprofit = 'lab_strategy_stepprofit'
    lab_strategy_backprofit = 'lab_strategy_backprofit'
    lab_strategy_baseprofit_baseon = 'lab_strategy_baseprofit_baseon'
    lab_strategy_timelife = 'lab_strategy_timelife'
    lab_strategy_interval = 'lab_strategy_interval'
    lab_strategy_note = 'lab_strategy_note'
    lab_strategy_container = 'lab_strategy_container'
    lab_strategy_margin = 'lab_strategy_margin'

    def __init__(self):
        super().__init__(LabStrategies, 'default')


class LabStrategyContainerWrapper(Model):

    
    lab_stra_con_id = 'lab_stra_con_id'
    lab_stra_con_container = 'lab_stra_con_container'
    lab_stra_con_child = 'lab_stra_con_child'
    lab_stra_con_weight = 'lab_stra_con_weight'
    lab_stra_con_slot = 'lab_stra_con_slot'
    lab_stra_con_blacklist = 'lab_stra_con_blacklist'

    def __init__(self):
        super().__init__(LabStrategyContainer, 'default')


class LabTrackBalanceWrapper(Model):

    
    lab_track_bl_id = 'lab_track_bl_id'
    lab_track_bl_account = 'lab_track_bl_account'
    lab_track_bl_time = 'lab_track_bl_time'
    lab_track_bl_margin_bl = 'lab_track_bl_margin_bl'
    lab_track_bl_invest = 'lab_track_bl_invest'
    lab_track_bl_unrealize = 'lab_track_bl_unrealize'
    lab_track_bl_balance = 'lab_track_bl_balance'

    def __init__(self):
        super().__init__(LabTrackBalance, 'default')


class LabWatchlistWrapper(Model):

    lab_wl_id = 'lab_wl_id'
    lab_wl_symbol = 'lab_wl_symbol'
    lab_wl_time = 'lab_wl_time'
    lab_wl_stoptime = 'lab_wl_stoptime'

    def __init__(self):
        super().__init__(LabWatchlist, 'default')


class LabOptResultWrapper(Model):
    
    lab_opt_result_id = 'lab_opt_result_id'
    lab_opt_result_optimization = 'lab_opt_result_optimization'
    lab_opt_result_params = 'lab_opt_result_params'
    lab_opt_result_strategy = 'lab_opt_result_strategy'
    lab_opt_result_balance = 'lab_opt_result_balance'
    lab_opt_result_margin_balance = 'lab_opt_result_margin_balance'
    lab_opt_result_unrelize_max = 'lab_opt_result_unrelize_max'
    lab_opt_result_invest_max = 'lab_opt_result_invest_max'
    lab_opt_result_account = 'lab_opt_result_account'
    lab_opt_result_campaign = 'lab_opt_result_campaign'
    lab_opt_result_event = 'lab_opt_result_event'
    lab_opt_result_interval_avg = 'lab_opt_result_interval_avg'
    lab_opt_result_interval_max = 'lab_opt_result_interval_max'
    lab_opt_result_total_position = 'lab_opt_result_total_position'
    lab_opt_result_log = 'lab_opt_result_log'
    lab_opt_result_done = 'lab_opt_result_done'
    lab_opt_result_total_long = 'lab_opt_result_total_long'
    lab_opt_result_total_short = 'lab_opt_result_total_short'
    lab_opt_result_total_takeprofit = 'lab_opt_result_total_takeprofit'
    lab_opt_result_total_stoploss = 'lab_opt_result_total_stoploss'
    
    def __init__(self):
        super().__init__(LabOptResult, 'default')


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