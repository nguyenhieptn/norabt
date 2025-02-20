class Reply:
    @staticmethod
    def make(result, message=None, data=None):
        return {
            'result': result,
            'message': message,
            'data': data
        }