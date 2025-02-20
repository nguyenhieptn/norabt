
from helper.Defaults import *
from helper.Reply import Reply


class Model(metaclass=Singleton):
    DENY = 'DENY'
    CASCADE = 'CASCADE'
    SET_NULL = 'SET_NULL'
    def __init__(self, modelClass, using='default'):
        self.modelClass = modelClass
        self.using = using
        self.preDropBook = {}

    def cls(self):
        return self.modelClass

    def new(self, *args, **options):
        newArgs = []
        for arg in args:
            if(type(arg) is dict):
                options.update(arg)
            else:
                newArgs.append(arg)
        inst = self.modelClass(**options)
        inst._state.db = self.using
        return inst
    
    def __getattr__(self, name):
        def function(*args, **options):
            fn = getattr(self.modelClass.objects.using(self.using), name, None)
            if(callable(fn)): 
                newArgs = []
                for arg in args:
                    if(type(arg) is dict):
                        options.update(arg)
                    else:
                        newArgs.append(arg)
                return fn(*newArgs, **options)
        return function


    #drop function block
      
    def preDropRegister(self, modelWrapper, keyCol, partnerKeyCol, action='DENY'):
        id = modelWrapper.__module__ + "." + modelWrapper.__class__.__name__ + "." + keyCol + "." + partnerKeyCol
        self.preDropBook[id] = {
            "modelWrapper":modelWrapper, 
            "keyCol":keyCol, 
            "partnerKeyCol":partnerKeyCol, 
            "action":action
        }
    
    def preDrop(self, querySet):
        if(len(self.preDropBook) == 0): return Reply.make(True, 'Success')
        limit = 500
        offset = 0

        #get all key col name
        keyCols = []
        for id in self.preDropBook:
            keyColName = self.preDropBook[id]['keyCol']
            if(not keyColName in keyCols): keyCols.append(keyColName)

        while True:
            deleteDatas = querySet[offset: offset+limit].values(*keyCols)
            offset += len(deleteDatas)
            for id in self.preDropBook:
                relation = self.preDropBook[id]
                wapperModel = relation['modelWrapper']
                deleteKeys = []
                for delData in deleteDatas:
                    if(isset(delData, relation['keyCol'])):
                        deleteKeys.append(delData[relation['keyCol']])

                if(len(deleteKeys) == 0): continue

                if(relation['action'] == Model.DENY):
                    isExist = wapperModel.filter(**{relation['partnerKeyCol'] + "__in": deleteKeys}).exists()
                    if(isExist): return Reply.make(False, 'Please remove ' + wapperModel.modelClass.__name__ + ' First')

                if(relation['action'] == Model.CASCADE):
                    dropResult = wapperModel.drop(**{relation['partnerKeyCol'] + "__in": deleteKeys})
                    if(not dropResult['result']): return dropResult
            
                if(relation['action'] == Model.SET_NULL):
                    wapperModel.filter(**{relation['partnerKeyCol'] + "__in": deleteKeys}).update(**{relation['partnerKeyCol']:None})

            if(len(deleteDatas) <= limit): break
        
        return Reply.make(True, 'Success')

    def drop(self, *args, **options):
        for arg in args:
            if(type(arg) is dict):
                options.update(arg)
        querySet = self.modelClass.objects.using(self.using).filter(**options)
        preDropResult = self.preDrop(querySet.all())
        if(not preDropResult['result']): return preDropResult
        delResult = querySet.delete()
        return Reply.make(True, 'success', delResult)

    #end drop functions block

    #start edit functions block
    def edit(self, condition, editData):
        querySet = self.modelClass.objects.using(self.using).filter(**condition)
        result = querySet.update(**editData)
        return Reply.make(True, 'success', result)

    def save(self, instance):
        instance.save(using=self.using)

    def toDict(self, instance):
        dic = {}
        keys = instance.__dict__.keys()
        for key in keys:
            if "_" not in key[0]:
                dic[key] = instance.__dict__[key]
        return dic

    



        
