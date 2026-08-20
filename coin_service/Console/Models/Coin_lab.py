# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class LabAccount(models.Model):
    lab_account_id = models.AutoField(primary_key=True)
    lab_account_name = models.CharField(unique=True, max_length=150, blank=True, null=True)
    lab_account_balance = models.FloatField(blank=True, null=True)
    lab_account_margin_balance = models.FloatField(blank=True, null=True)
    lab_account_reserve = models.FloatField(blank=True, null=True)
    lab_account_compound = models.IntegerField(blank=True, null=True)
    lab_account_note = models.TextField(blank=True, null=True)
    lab_account_log = models.TextField(blank=True, null=True)
    lab_account_params = models.TextField(blank=True, null=True)
    lab_account_margin_type = models.CharField(max_length=20, blank=True, null=True)
    lab_account_track_balance = models.IntegerField(blank=True, null=True)
    lab_account_running = models.IntegerField(blank=True, null=True)
    lab_account_sync = models.IntegerField(blank=True, null=True, default=1)
    lab_account_leap = models.IntegerField(blank=True, null=True, default=0)
    lab_account_db = models.TextField(blank=True, null=True)
    lab_account_data_type = models.CharField(max_length=150, blank=True, null=True)
    lab_account_data_length = models.IntegerField(blank=True, null=True)
    lab_account_server = models.CharField(max_length=150, blank=True, null=True)
    lab_account_choice_strategy = models.IntegerField(blank=True, null=True)
    lab_account_choice_period = models.IntegerField(blank=True, null=True)
    lab_account_choice_result = models.TextField(blank=True, null=True)
    lab_account_choice_condition = models.TextField(blank=True, null=True)
    lab_account_tele_bot = models.CharField(max_length=150, blank=True, null=True)
    lab_account_tele_group_notice = models.CharField(max_length=150, blank=True, null=True)
    lab_account_tele_group_summary = models.CharField(max_length=150, blank=True, null=True)
    lab_account_tele_group_error = models.CharField(max_length=150, blank=True, null=True)
    lab_account_user = models.IntegerField(blank=True, null=True)
    lab_account_group = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lab_account'


class LabCampaigns(models.Model):
    lab_campaign_id = models.AutoField(primary_key=True)
    lab_campaign_name = models.CharField(max_length=150, blank=True, null=True)
    lab_campaign_symbol = models.CharField(max_length=150, blank=True, null=True)
    lab_campaign_start = models.IntegerField(blank=True, null=True)
    lab_campaign_stop = models.IntegerField(blank=True, null=True)
    lab_campaign_params = models.TextField(blank=True, null=True)
    lab_campaign_side = models.CharField(max_length=10)
    lab_campaign_strategy = models.IntegerField(blank=True, null=True)
    lab_campaign_status = models.TextField(blank=True, null=True)
    lab_campaign_running = models.IntegerField(blank=True, null=True)
    lab_campaign_last = models.IntegerField(blank=True, null=True)
    lab_campaign_budget = models.FloatField(blank=True, null=True)
    lab_campaign_reserve = models.FloatField(blank=True, null=True)
    lab_campaign_compound = models.FloatField(blank=True, null=True)
    lab_campaign_profit = models.FloatField(blank=True, null=True)
    lab_campaign_account = models.IntegerField(blank=True, null=True)
    lab_campaign_money = models.FloatField(blank=True, null=True)
    lab_campaign_active_budget = models.FloatField(blank=True, null=True)
    lab_campaign_priority = models.IntegerField(blank=True, null=True)
    lab_campaign_runtime = models.BigIntegerField(blank=True, null=True)
    lab_campaign_log = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lab_campaigns'


class LabEventLogs(models.Model):
    lab_elog_id = models.AutoField(primary_key=True)
    lab_elog_campaign = models.IntegerField(blank=True, null=True)
    lab_elog_symbol = models.CharField(max_length=20, blank=True, null=True)
    lab_elog_time = models.BigIntegerField(blank=True, null=True)
    lab_elog_chart = models.FloatField(blank=True, null=True)
    lab_elog_result = models.TextField(blank=True, null=True)  # This field type is a guess.
    lab_elog_maxprofit = models.FloatField(blank=True, null=True)
    lab_elog_minprofit = models.FloatField(blank=True, null=True)
    lab_elog_profit = models.FloatField(blank=True, null=True)
    lab_elog_baseprofit = models.FloatField(blank=True, null=True)
    lab_elog_status = models.CharField(max_length=15, blank=True, null=True)
    lab_elog_matched = models.IntegerField(blank=True, null=True)
    lab_elog_base = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'lab_event_logs'


class LabOrder(models.Model):
    lab_order_id = models.AutoField(primary_key=True)
    lab_order_time = models.BigIntegerField(blank=True, null=True)
    lab_order_action = models.BigIntegerField(blank=True, null=True)
    lab_order_symbol = models.CharField(max_length=150, blank=True, null=True)
    lab_order_qty = models.FloatField(blank=True, null=True)
    lab_order_price = models.FloatField(blank=True, null=True)
    lab_order_commit = models.FloatField(blank=True, null=True)
    lab_order_pnl = models.FloatField(blank=True, null=True)
    lab_order_baseon = models.TextField(blank=True, null=True)
    lab_order_type = models.IntegerField(blank=True, null=True)
    lab_order_phase = models.IntegerField(blank=True, null=True)
    lab_order_account = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lab_order'


class LabResults(models.Model):
    lab_result_id = models.AutoField(primary_key=True)
    lab_result_campaign = models.IntegerField(blank=True, null=True)
    lab_result_strategy = models.IntegerField(blank=True, null=True)
    lab_result_symbol = models.CharField(max_length=20, blank=True, null=True)
    lab_result_chart = models.FloatField(blank=True, null=True)
    lab_result_chart_price = models.FloatField(blank=True, null=True)
    lab_result_enter_time = models.BigIntegerField(blank=True, null=True)
    lab_result_enter_price = models.FloatField(blank=True, null=True)
    lab_result_order_time = models.BigIntegerField(blank=True, null=True)
    lab_result_order_price = models.FloatField(blank=True, null=True)
    lab_result_order_qty = models.FloatField(blank=True, null=True)
    lab_result_order_phase = models.IntegerField(blank=True, null=True)
    lab_result_order_release = models.IntegerField(blank=True, null=True)
    lab_result_high = models.FloatField(blank=True, null=True)
    lab_result_low = models.FloatField(blank=True, null=True)
    lab_result_type = models.IntegerField(blank=True, null=True)
    lab_result_base = models.TextField(blank=True, null=True)
    lab_result_params = models.TextField(blank=True, null=True)
    lab_result_start_reason = models.TextField(blank=True, null=True)
    lab_result_status = models.IntegerField(blank=True, null=True)
    lab_result_matched_price = models.FloatField(blank=True, null=True)
    lab_result_first_price = models.FloatField(blank=True, null=True)
    lab_result_matched_time = models.FloatField(blank=True, null=True)
    lab_result_matched_qty = models.FloatField(blank=True, null=True)
    lab_result_last_price = models.FloatField(blank=True, null=True)
    lab_result_matched_ema5 = models.FloatField(blank=True, null=True)
    lab_result_sell_price = models.FloatField(blank=True, null=True)
    lab_result_sell_time = models.FloatField(blank=True, null=True)
    lab_result_profit = models.FloatField(blank=True, null=True)
    lab_result_commit = models.FloatField(blank=True, null=True)
    lab_result_eventprofit = models.FloatField(blank=True, null=True)
    lab_result_realprofit = models.FloatField(blank=True, null=True)
    lab_result_realpnl = models.FloatField(blank=True, null=True)
    lab_result_baseprofit = models.FloatField(blank=True, null=True)
    lab_result_pending = models.IntegerField(blank=True, null=True)
    lab_result_phase = models.IntegerField(blank=True, null=True)
    lab_result_budget = models.FloatField(blank=True, null=True)
    lab_result_flow = models.CharField(max_length=150, blank=True, null=True)
    lab_result_log = models.TextField(blank=True, null=True)
    lab_result_interval = models.BigIntegerField(blank=True, null=True)
    lab_result_btc_wma45_1d = models.FloatField(blank=True, null=True)
    lab_result_btc_wma45_1w = models.FloatField(blank=True, null=True)
    lab_result_container = models.IntegerField(blank=True, null=True)
    lab_result_account = models.IntegerField(blank=True, null=True)
    lab_result_margin = models.FloatField(blank=True, null=True)
    lab_result_close_time = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lab_results'


class LabStrategies(models.Model):
    lab_strategy_id = models.AutoField(primary_key=True)
    lab_strategy_name = models.CharField(max_length=150, blank=True, null=True)
    lab_strategy_content = models.TextField(blank=True, null=True)
    lab_strategy_takeprofit = models.CharField(max_length=150, blank=True, null=True)
    lab_strategy_stoploss = models.CharField(max_length=150, blank=True, null=True)
    lab_strategy_baseprofit = models.CharField(max_length=150, blank=True, null=True)
    lab_strategy_stepprofit = models.CharField(max_length=150, blank=True, null=True)
    lab_strategy_backprofit = models.CharField(max_length=150, blank=True, null=True)
    lab_strategy_baseprofit_baseon = models.CharField(max_length=150, blank=True, null=True)
    lab_strategy_timelife = models.CharField(max_length=150, blank=True, null=True)
    lab_strategy_interval = models.CharField(max_length=150, blank=True, null=True)
    lab_strategy_note = models.TextField(blank=True, null=True)
    lab_strategy_container = models.IntegerField(blank=True, null=True)
    lab_strategy_margin = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lab_strategies'


class LabStrategyContainer(models.Model):
    lab_stra_con_id = models.AutoField(primary_key=True)
    lab_stra_con_container = models.IntegerField(blank=True, null=True)
    lab_stra_con_child = models.IntegerField(blank=True, null=True)
    lab_stra_con_weight = models.IntegerField(blank=True, null=True)
    lab_stra_con_slot = models.IntegerField(blank=True, null=True)
    lab_stra_con_blacklist = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lab_strategy_container'


class LabTrackBalance(models.Model):
    lab_track_bl_id = models.AutoField(primary_key=True)
    lab_track_bl_account = models.IntegerField(blank=True, null=True)
    lab_track_bl_time = models.BigIntegerField(blank=True, null=True)
    lab_track_bl_margin_bl = models.FloatField(blank=True, null=True)
    lab_track_bl_invest = models.FloatField(blank=True, null=True)
    lab_track_bl_unrealize = models.FloatField(blank=True, null=True)
    lab_track_bl_balance = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lab_track_balance'


class LabWatchlist(models.Model):
    lab_wl_id = models.AutoField(primary_key=True)
    lab_wl_symbol = models.CharField(max_length=150, blank=True, null=True)
    lab_wl_time = models.IntegerField(blank=True, null=True)
    lab_wl_stoptime = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lab_watchlist'


class LabOptimization(models.Model):
    lab_opt_id = models.AutoField(primary_key=True)
    lab_opt_name = models.CharField(max_length=150, blank=True, null=True)
    lab_opt_account = models.IntegerField(blank=True, null=True)
    lab_opt_params = models.TextField(blank=True, null=True)
    lab_opt_thread = models.IntegerField(blank=True, null=True)
    lab_opt_data_leng = models.IntegerField(blank=True, null=True, default=15)
    lab_opt_note = models.TextField(blank=True, null=True)
    lab_opt_log = models.TextField(blank=True, null=True)
    lab_opt_start_time = models.IntegerField(blank=True, null=True)
    lab_opt_stop_time = models.IntegerField(blank=True, null=True)
    lab_opt_processed = models.TextField(blank=True, null=True)
    lab_opt_server = models.CharField(max_length=150, blank=True, null=True, default="localhost")

    class Meta:
        managed = False
        db_table = 'lab_optimization'


class LabOptResult(models.Model):
    lab_opt_result_id = models.AutoField(primary_key=True)
    lab_opt_result_optimization = models.IntegerField(blank=True, null=True)
    lab_opt_result_params = models.TextField(blank=True, null=True)
    lab_opt_result_strategy = models.TextField(blank=True, null=True)
    lab_opt_result_balance = models.FloatField(blank=True, null=True)
    lab_opt_result_margin_balance = models.FloatField(blank=True, null=True)
    lab_opt_result_unrelize_max = models.FloatField(blank=True, null=True)
    lab_opt_result_invest_max = models.FloatField(blank=True, null=True)
    lab_opt_result_account = models.TextField(blank=True, null=True)
    lab_opt_result_campaign = models.TextField(blank=True, null=True)
    lab_opt_result_event = models.TextField(blank=True, null=True)
    lab_opt_result_interval_avg = models.FloatField(blank=True, null=True)
    lab_opt_result_interval_max = models.FloatField(blank=True, null=True)
    lab_opt_result_total_position = models.IntegerField(blank=True, null=True)
    lab_opt_result_log = models.TextField(blank=True, null=True)
    lab_opt_result_done = models.IntegerField(blank=True, null=True, default=0)
    lab_opt_result_total_long = models.IntegerField(blank=True, null=True)
    lab_opt_result_total_short = models.IntegerField(blank=True, null=True)
    lab_opt_result_total_takeprofit = models.IntegerField(blank=True, null=True)
    lab_opt_result_total_stoploss = models.IntegerField(blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'lab_opt_result'


class LabNode(models.Model):
    lab_node_id = models.AutoField(primary_key=True)
    lab_node_name = models.CharField(unique=True, max_length=150, blank=True, null=True)
    lab_node_ip = models.CharField(max_length=150, blank=True, null=True)
    lab_node_port = models.IntegerField(blank=True, null=True)
    lab_node_sid = models.CharField(unique=True, max_length=150, blank=True, null=True)
    lab_node_status = models.CharField(max_length=150, blank=True, null=True)
    lab_node_ram = models.FloatField(blank=True, null=True)
    lab_node_ram_total = models.FloatField(blank=True, null=True)
    lab_node_cpu = models.FloatField(blank=True, null=True)
    lab_node_cpu_core = models.FloatField(blank=True, null=True)
    lab_node_disk = models.FloatField(blank=True, null=True)
    lab_node_disk_total = models.FloatField(blank=True, null=True)
    lab_node_note = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lab_node'

