import inspect
from django.core.management.base import BaseCommand
# import Console.Models.Coin_lab
import importlib
class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('module', nargs=1, type=str)
        parser.add_argument('--using',nargs='?', action='store', default='default')
        parser.add_argument('--class',nargs='?', action='append')

    def handle(self, *args, **options):
        try:

            template = """
class ##classname##Wrapper(Model):
    
    ##attributes##
    def __init__(self):
        super().__init__(##classname##, '##using##')
"""
            note = """
# This is an auto-generated model wrapper singleton develope by LIN.
# This wrapper allow you to:
# - Set defaul using
# - Auto-fill the field of the model
# - Define some SQL relation over Register (preDropRegister)
# Feel free to rename the models, but don't rename db_table values or field names. 

"""
            module = options['module'][0]
            using = options['using']
            selectClass = options['class']
           
            imported = importlib.import_module(module)
            classes = [x for x in dir(imported) if inspect.isclass(getattr(imported, x))]
            appName = str(module).split('.')[0]
            
            output = note
            output += "from " + appName + ".Models.Wrappers.Model import Model\n"
            output += "from " + module + " import *\n"
            
            for className in classes:
                attribute = ""
                if(not selectClass is None):
                    if(not className in selectClass):
                        continue
                tem = template.replace('##classname##', className).replace("##using##", using)
                classObject = eval('imported.' + className)._meta.fields
                for attr in classObject:
                    attrClean = str(attr).split('.')[-1]
                    attribute += attrClean + " = '" + attrClean + "'\n    "

                tem = tem.replace("##attributes##", attribute)
                output += "\n" + tem

            print(output)
                
        except Exception as e:
            print(e)
    