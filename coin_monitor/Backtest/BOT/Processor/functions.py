import re

def fillStrategy(strategy, params:dict={}):
    if(type(strategy) is dict):
        for key in strategy:
            if(type(strategy[key]) is dict or type(strategy[key])):
                fillStrategy(strategy[key], params)
            if(type(strategy[key]) is str):
                regex = r"\#([^\#]+)\#"
                match = re.search(regex, strategy[key])
                if(match is not None):
                    matchParams = match.groups()[0]
                    strategy[key] = params.get(matchParams, None)
    if(type(strategy) is list):
        for key,value in enumerate(strategy):
            if(type(strategy[key]) is dict or type(strategy[key])):
                fillStrategy(strategy[key], params)
            if(type(strategy[key]) is str):
                regex = r"\#([^\#]+)\#"
                match = re.search(regex, strategy[key])
                if(match is not None):
                    matchParams = match.groups()[0]
                    strategy[key] = params.get(matchParams, None)






