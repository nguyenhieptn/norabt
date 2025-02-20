

from Console.Models.Control import Control

# params: control_lab_db

class Ctrl:
    @staticmethod
    def get(name, default=None):
        try:
            value = Control.objects.using('control').get(control_name=name)
            return value.control_value
        except Exception as e:
            print(e)
            return default

    @staticmethod
    def set(name, value):
        try:
            obj, created = Control.objects.using('control').update_or_create(control_name=name, defaults={'control_value':value})
            return obj
        except Exception as e:
            print(e)
            return False