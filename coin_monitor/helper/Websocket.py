import time
import orjson
import redis


class Websocket:

    def sendMessage(self, data):
        if data is not str:
            data = orjson.dumps(data)
        r = redis.Redis()
        pub = r.publish(
            channel='websocket',
            message=data
        )
        pub = r.pubsub()
        pub.subscribe('websocket_result')
        while True:
            data = pub.get_message()
            if data:
                message = data['data']
                if message and message != 1:
                    print("Message: {}".format(message))
                    break

            time.sleep(1)
