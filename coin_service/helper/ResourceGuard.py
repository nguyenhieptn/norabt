import os
import psutil
import gc
import time

class ResourceGuard:
    """
    Hệ thống giám sát và điều tiết tài nguyên chủ động (Runtime Dynamic Throttle)
    Đảm bảo toàn bộ hệ thống luôn vận hành trong ngân sách < 1/2 Server (12 Cores, 14 GB RAM).
    """
    MAX_WORKERS_HARD_CAP = 6          # Tối đa 6 tiến trình song song
    MAX_RAM_ALLOWED_GB = 14.0         # Trần RAM tối đa cho toàn bộ dự án
    MIN_FREE_RAM_REQUIRED_GB = 3.0    # RAM khả dụng tối thiểu để khởi động tác vụ mới
    PROCESS_RAM_ALERT_MB = 1200       # Ngưỡng RAM của 1 process đơn lẻ kích hoạt dọn rác

    @classmethod
    def get_memory_info(cls):
        """Trả về thông tin RAM thực tế của máy chủ"""
        mem = psutil.virtual_memory()
        return {
            'total_gb': round(mem.total / (1024 ** 3), 2),
            'used_gb': round(mem.used / (1024 ** 3), 2),
            'available_gb': round(mem.available / (1024 ** 3), 2),
            'percent': mem.percent
        }

    @classmethod
    def get_current_process_ram_mb(cls):
        """Lấy dung lượng RAM thực tế (RSS) mà tiến trình hiện tại đang chiếm giữ"""
        try:
            process = psutil.Process(os.getpid())
            return round(process.memory_info().rss / (1024 * 1024), 2)
        except Exception:
            return 0.0

    @classmethod
    def is_safe_to_run(cls, min_available_gb=None):
        """Kiểm tra điều kiện an toàn TRƯỚC khi khởi chạy tác vụ"""
        if min_available_gb is None:
            min_available_gb = cls.MIN_FREE_RAM_REQUIRED_GB
        
        mem = cls.get_memory_info()
        if mem['available_gb'] < min_available_gb:
            return False, f"CẢNH BÁO: RAM khả dụng ({mem['available_gb']} GB) < ngưỡng an toàn ({min_available_gb} GB)."
        return True, "Tài nguyên an toàn."

    @classmethod
    def runtime_heartbeat(cls, context_tag="Worker"):
        """
        GIÁM SÁT VÀ ĐIỀU TIẾT ĐỘNG TRONG QUÁ TRÌNH CHẠY (RUNTIME THROTTLING):
        Được gọi liên tục bên trong các vòng lặp xử lý nến/block để:
        1. Tự động dọn rác nếu process ngốn RAM.
        2. Tự động hãm tốc độ (adaptive pause) nếu RAM server bắt đầu bị ép.
        """
        proc_ram_mb = cls.get_current_process_ram_mb()
        mem = cls.get_memory_info()

        # 1. Tự dọn rác cục bộ nếu tiến trình vượt ngưỡng
        if proc_ram_mb > cls.PROCESS_RAM_ALERT_MB:
            gc.collect()

        # 2. Nếu RAM server khả dụng dưới 3GB -> Hãm tiến trình 0.5s để giải phóng IO/Memory
        if mem['available_gb'] < 3.0:
            gc.collect()
            time.sleep(0.5)

        # 3. Nếu RAM server khả dụng dưới 2GB -> Hãm sâu 1.5s để bảo vệ máy chủ
        if mem['available_gb'] < 2.0:
            gc.collect()
            time.sleep(1.5)

    @classmethod
    def get_safe_worker_count(cls, requested_workers=None):
        """Giới hạn số worker đa luồng trong ngân sách an toàn"""
        mem = cls.get_memory_info()
        available_gb = mem['available_gb']

        if requested_workers is None or requested_workers <= 0:
            requested_workers = 4

        safe_workers = min(int(requested_workers), cls.MAX_WORKERS_HARD_CAP)

        if available_gb < 4.0:
            safe_workers = min(safe_workers, 2)
        elif available_gb < 8.0:
            safe_workers = min(safe_workers, 4)

        return max(1, safe_workers)

    @classmethod
    def cleanup_memory(cls):
        """Kích hoạt dọn dẹp rác bộ nhớ ngay lập tức"""
        gc.collect()
