import os
import sys
from time import time
from Console.Helper.Defaults import *
from django.core.management.base import BaseCommand
from Console.Helper.Telegram import Tele
from Console.Models.Wrappers.Lab.Coin_lab import LabOptResultWrapper
from Console.Phoenix.Lab.Optimization import Optimization
import re
import json

class Command(BaseCommand):
    help = 'Start a Lab Optimization'

    def add_arguments(self, parser):
        parser.add_argument('id', nargs=1, type=int)
        pass

    def handle(self, *args, **options):

        id = options['id'][0]

        regex = r"\{.lab_opt_result_id.*(?={.lab_opt_result_id)|\{.lab_opt_result_id.*\}"

        file1 = open(f'logs/py_lab_optimization_{id}.log', 'r')
        Lines = file1.readlines()

        missData = []

        for line in Lines:
            matches = re.findall(regex, line)
            if(matches):
                for match in matches:
                    print(match)
                    dt = eval(match)
                    if(dt['lab_opt_result_id'] is not None):
                        missData.append(dt)
       
        for data in missData:
            LabOptResultWrapper().edit({
                LabOptResultWrapper.lab_opt_result_id : data[LabOptResultWrapper.lab_opt_result_id]
            }, data)
    