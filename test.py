import pymongo

# Cấu hình MongoDB
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "raw_kline1m_future"


def find_empty_collections():
    """Kiểm tra collection nào trong database không có dữ liệu"""
    try:
        # Kết nối MongoDB
        client = pymongo.MongoClient(MONGO_URI)
        db = client[MONGO_DB]

        # Lấy danh sách tất cả collection
        collections = db.list_collection_names()
        empty_collections = []

        for collection in collections:
            count = db[collection].count_documents({})
            if count == 0:
                empty_collections.append(collection)

        client.close()
        return empty_collections

    except Exception as err:
        print(f"Lỗi MongoDB: {err}")
        return []


# Chạy kiểm tra
empty_collections = find_empty_collections()
if empty_collections:
    print("Các collection không có dữ liệu:", empty_collections)
else:
    print("Tất cả các collection đều có dữ liệu.")
