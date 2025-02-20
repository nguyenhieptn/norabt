# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.

from djongo import models


class Scraper(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    scraper_name = models.CharField(max_length=150, unique=True, blank=True, null=True)
    scraper_ip = models.CharField(max_length=150, blank=True, null=True)
    scraper_cpu = models.FloatField(blank=True, null=True)
    scraper_cpu_total = models.FloatField(blank=True, null=True)
    scraper_ram = models.FloatField(blank=True, null=True)
    scraper_ram_total = models.FloatField(blank=True, null=True)
    scraper_disk = models.FloatField(blank=True, null=True)
    scraper_disk_total = models.FloatField(blank=True, null=True)
    scraper_status = models.CharField(max_length=150, blank=True, null=True)
    scraper_port = models.IntegerField(blank=True, null=True)
    scraper_sid = models.CharField(max_length=150, blank=True, null=True)
    scraper_note = models.TextField(blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'scraper'

class ScraperSystem(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    scraper_sys_name = models.CharField(max_length=150, unique=True, blank=True, null=True)
    scraper_sys_time = models.IntegerField(blank=True, null=True)
    scraper_sys_cpu = models.FloatField(blank=True, null=True)
    scraper_sys_cpu_total = models.FloatField(blank=True, null=True)
    scraper_sys_ram = models.FloatField(blank=True, null=True)
    scraper_sys_ram_total = models.FloatField(blank=True, null=True)
    scraper_sys_disk = models.FloatField(blank=True, null=True)
    scraper_sys_disk_total = models.FloatField(blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'scraper_system'


class ScraperProcess(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    scraper_process_name = models.CharField(max_length=150, unique=True, blank=True, null=True)
    scraper_process_script = models.CharField(max_length=150, blank=True, null=True)
    scraper_process_symbol = models.CharField(max_length=20,blank=True, null=True)
    scraper_process_arguments = models.JSONField(blank=True)
    scraper_process_cmdline = models.JSONField(blank=True)
    scraper_process_user = models.CharField(max_length=20,blank=True, null=True)
    scraper_process_ram = models.FloatField(blank=True, null=True)
    scraper_process_cpu = models.FloatField(blank=True, null=True)
    scraper_process_pid = models.IntegerField(blank=True, null=True)
    scraper_process_start = models.CharField(max_length=20,blank=True, null=True)
    scraper_process_time = models.CharField(max_length=20,blank=True, null=True)
    scraper_process_check_time = models.IntegerField(blank=True, null=True)
    scraper_process_stt = models.CharField(max_length=20,blank=True, null=True)
    scraper_process_status = models.IntegerField(blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'scraper_process'

class ScraperCoin(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    scraper_coin_name = models.CharField(max_length=150, unique=True, blank=True, null=True)
    scraper_coin_type = models.CharField(max_length=150, blank=True, null=True)
    scraper_coin_symbol = models.CharField(max_length=150, blank=True, null=True)
    scraper_coin_time = models.BigIntegerField(blank=True, null=True)
    scraper_coin_status = models.IntegerField(blank=True)
    
    class Meta:
        managed = False
        db_table = 'scraper_coin'
        indexes = [
            models.Index(fields=['scraper_coin_name','scraper_coin_type','scraper_coin_symbol']),
        ]