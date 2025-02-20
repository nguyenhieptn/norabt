


import re
class Validate:
    INT = 'INT'
    FLOAT = 'FLOAT'
    STR = 'STR'

    regexs = {
        INT: '^[+-]?\d+$',
        FLOAT: '^[+-]?([0-9]*[.])?[0-9]+$',
        STR: '^[\w\d\s\_]+$'
    }
    @staticmethod
    def check(data, dataType):
        data = str(data)
        try:
            if(dataType in Validate.regexs):
                if(re.match(re.compile(Validate.regexs[dataType]), data)):
                    return True
            else:
                if(dataType[0] == '^' and dataType[-1] == '$'):
                    if(re.match(re.compile(dataType), data)):
                        return True

            return False
            
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def check_raise(data, dataType):        
        if(not Validate.check(data, dataType)): raise Exception(f"Wrong data. {data} is not {dataType}")

    