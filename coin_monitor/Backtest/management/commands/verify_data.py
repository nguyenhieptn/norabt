import mysql.connector
import pymongo
import requests
from time import sleep
import pymysql
from django.core.management.base import BaseCommand
import requests

# Cấu hình MongoDB
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "backtest_data_1m"
BINANCE_FUTURES_API = "https://fapi.binance.com/fapi/v1/klines"


class Command(BaseCommand):
    help = "verify data"

    def __init__(
        self, stdout=None, stderr=None, no_color=False, force_color=False
    ):
        super().__init__(stdout, stderr, no_color, force_color)

    def add_arguments(self, parser):
        parser.add_argument("--exchange", nargs="?", default="future", type=str)

    def handle(self, *args, **options):
        exchange = options.get("exchange", "future")
        symbols = get_symbols(exchange)
        if not symbols:
            print("Không có symbols nào được tìm thấy.")
            return

        print("Bắt đầu kiểm tra dữ liệu...")
        compare_binance_vs_mongodb(symbols)


def get_db_connection():

    host = "127.0.0.1"  # IP của server Ubuntu
    port = 3306  # Port của MySQL
    user = "phoenix"  # Username đã tạo
    password = "Phoenix@1235"  # Mật khẩu của bạn
    database = "coin_lab"  # Tên database muốn kết nối

    try:
        # Kết nối đến MySQL
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            auth_plugin_map={"mysql_native_password": None},
        )
        return connection

    except pymysql.MySQLError as err:
        print(f"Lỗi: {err}")


def get_symbols(exchange="future"):
    if exchange == "future":
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    else:
        url = "https://api.binance.com/api/v3/exchangeInfo"
    request = requests.get(url)
    data = request.json()
    symbolData = data["symbols"]
    symbols = list()
    for symbolItem in symbolData:
        if symbolItem["quoteAsset"] == "USDT":
            symbols.append(symbolItem["symbol"])
    symbols.sort()
    return symbols


def get_mongo_data_count(symbol):
    """Đếm số lượng nến trong MongoDB trong khoảng thời gian cụ thể"""
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db["candle_4h"]

        count = collection.count_documents(
            {
                "symbol": symbol,
                "is_close": 1,
            }
        )

        client.close()
        return count

    except Exception as err:
        print(f"Lỗi MongoDB: {err}")
        return 0


def get_binance_data(symbol, frame):
    """Lấy dữ liệu nến từ Binance trong khoảng thời gian cụ thể"""
    data = []
    start_time = 1577836800000

    while True:
        try:
            url = f"{BINANCE_FUTURES_API}?symbol={symbol}&interval={frame}&startTime={start_time}&limit=1000"
            response = requests.get(url)
            response.raise_for_status()

            used_weight = int(response.headers.get("X-MBX-USED-WEIGHT-1M", 0))
            max_weight = 2400

            candles = response.json()
            if not candles:
                break

            for dt in candles:
                close_time = int(dt[6])
                data.append(
                    {
                        "open_time": int(dt[0]),
                        "close_time": close_time,
                    }
                )

            start_time = candles[-1][6] + 1
            if len(candles) < 1000:
                break

            if used_weight >= max_weight * 0.95:
                sleep(60)

        except requests.exceptions.RequestException:
            break

    return data


def compare_binance_vs_mongodb(symbols):
    """So sánh dữ liệu nến giữa Binance và MongoDB trong khoảng thời gian cụ thể"""

    for symbol in symbols:
        # Đếm số lượng nến trong MongoDB
        mongo_count = get_mongo_data_count(symbol)

        # Lấy dữ liệu từ Binance
        binance_data = get_binance_data(symbol, "4h")
        binance_count = len(binance_data)
        if abs(binance_count - mongo_count) < 5:
            # In kết quả so sánh
            print(
                f"✅{symbol}: MongoDB = {mongo_count}, Binance = {binance_count}"
            )
        else:
            print(
                f"⚠️Độ lệch lớn  {symbol}: MongoDB = {mongo_count}, Binance = {binance_count}"
            )
    print("Hoàn thành so sánh dữ liệu")
