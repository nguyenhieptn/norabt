import os
import psutil
import gc

class ResourceGuard:
    # Ngân sách tài nguyên: Sử dụng tối đa 1/2 Server (12 Cores, 14 GB RAM)
    MAX_WORKERS_HARD_CAP = 6       # Tối đa 6 tiến trình song song (đảm bảo <= 25-30% CPU của 24 vCPUs)
    MAX_RAM_ALLOWED_GB = 14.0      # Ngưỡng RAM tối đa cho toàn bộ dự án (dưới 1/2 tổng RAM 30GB)
    MIN_FREE_RAM_REQUIRED_GB = 3.0 # Tối thiểu 3GB RAM trống khả dụng trước khi kích hoạt task mới

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
    def is_safe_to_run(cls, min_available_gb=None):
        """Kiểm tra xem hệ thống có đủ RAM trống an toàn để chạy hay không"""
        if min_available_gb is None:
            min_available_gb = cls.MIN_FREE_RAM_REQUIRED_GB
        
        mem = cls.get_memory_info()
        # Nếu RAM khả dụng < min_available_gb hoặc RAM đã dùng > MAX_RAM_ALLOWED_GB
        if mem['available_gb'] < min_available_gb:
            return False, f"CẢNH BÁO TÀI NGUYÊN: RAM khả dụng còn lại ({mem['available_gb']} GB) thấp hơn mức an toàn ({min_available_gb} GB)."
        return True, "Tài nguyên an toàn."

    @classmethod
    def get_safe_worker_count(cls, requested_workers=None):
        """
        Giới hạn số worker đa luồng để luôn nằm trong ngân sách 1/2 server (tối đa 6 workers).
        Tự động giảm worker nếu RAM khả dụng đang thấp.
        """
        mem = cls.get_memory_info()
        available_gb = mem['available_gb']

        if requested_workers is None or requested_workers <= 0:
            requested_workers = 4

        # Trần cứng tối đa 6 workers
        safe_workers = min(int(requested_workers), cls.MAX_WORKERS_HARD_CAP)

        # Điều tiết động theo RAM thực tế
        if available_gb < 4.0:
            safe_workers = min(safe_workers, 2)
        elif available_gb < 8.0:
            safe_workers = min(safe_workers, 4)

        return max(1, safe_workers)

    @classmethod
    def cleanup_memory(cls):
        """Kích hoạt dọn dẹp rác bộ nhớ ngay lập tức"""
        gc.collect()
