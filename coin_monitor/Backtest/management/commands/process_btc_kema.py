from models.Mongo.CandleModel import Candle_Model
from django.core.management.base import BaseCommand
from dateutil import tz
import pandas as pd
import plotly.graph_objects as go

import datetime
import requests
from pymongo import UpdateOne


class Command(BaseCommand):
    help = "Process BTCUSDT kema"

    def __init__(
        self, stdout=None, stderr=None, no_color=False, force_color=False
    ):
        super().__init__(stdout, stderr, no_color, force_color)

    def handle(self, *args, **options):
        self.model_1d = Candle_Model("backtest_data_1m", "candle_1d")
        data_1d = self.model_1d.collection.find(
            {"symbol": "BTCUSDT", "is_close": 1}
        )
        data_1d = pd.DataFrame(data_1d)

        data_1d = data_1d.sort_values(by="open_time").reset_index(drop=True)

        # Thêm các cột LONG_KEMA_30, LONG_KEMA_45, LONG_KEMA_15
        data_1d[["LONG_KEMA_30", "LONG_KEMA_45", "LONG_KEMA_15"]] = 0

        # Khởi tạo cờ trạng thái
        long_30 = False
        long_45 = False
        long_15 = False

        for i, row in data_1d.iterrows():
            # Xử lý LONG_KEMA_15
            if not long_15 and row["close"] >= row["KUP15"]:
                long_15 = True
            elif long_15 and row["close"] <= row["KLO15"]:
                long_15 = False
            data_1d.at[i, "LONG_KEMA_15"] = 1 if long_15 else 0

            # Xử lý LONG_KEMA_30
            if not long_30 and row["close"] >= row["KUP30"]:
                long_30 = True
            elif long_30 and row["close"] <= row["KLO30"]:
                long_30 = False
            data_1d.at[i, "LONG_KEMA_30"] = 1 if long_30 else 0

            # Xử lý LONG_KEMA_45
            if not long_45 and row["close"] >= row["KUP45"]:
                long_45 = True
            elif long_45 and row["close"] <= row["KLO45"]:
                long_45 = False
            data_1d.at[i, "LONG_KEMA_45"] = 1 if long_45 else 0
        bulk_updates_1d = []
        for i, row in data_1d.iterrows():
            bulk_updates_1d.append(
                UpdateOne(
                    {"_id": row["_id"]},  # Định danh bản ghi
                    {
                        "$set": {
                            "LONG_KEMA_30": int(row["LONG_KEMA_30"]),
                            "LONG_KEMA_45": int(row["LONG_KEMA_45"]),
                            "LONG_KEMA_15": int(row["LONG_KEMA_15"]),
                        }
                    },
                )
            )

        if bulk_updates_1d:
            result_1d = self.model_1d.collection.bulk_write(bulk_updates_1d)
            print(
                f"Đã cập nhật {result_1d.modified_count} bản ghi LONG_KEMA_1d vào MongoDB!"
            )

        self.model_1w = Candle_Model("backtest_data_1m", "candle_1w")
        data_1w = self.model_1w.collection.find(
            {"symbol": "BTCUSDT", "is_close": 1}
        )
        data_1w = pd.DataFrame(data_1w)
        data_1w = data_1w.sort_values(by="open_time").reset_index(drop=True)

        # Thêm các cột LONG_KEMA_30, LONG_KEMA_45, LONG_KEMA_15
        data_1w[["LONG_KEMA_7"]] = 0

        # Khởi tạo cờ trạng thái
        long_7 = False

        for i, row in data_1w.iterrows():
            if i == 0:
                continue
            prev_close = data_1w.at[i - 1, "close"]
            prev_kup7 = data_1w.at[i - 1, "KUP7"]
            prev_klo7 = data_1w.at[i - 1, "KLO7"]
            # Xử lý LONG_KEMA_15
            if not long_7 and prev_close >= prev_kup7:
                long_7 = True
            elif long_7 and prev_close <= prev_klo7:
                long_7 = False
            data_1w.at[i, "LONG_KEMA_7"] = 1 if long_7 else 0

        bulk_updates_1w = []
        for i, row in data_1w.iterrows():
            bulk_updates_1w.append(
                UpdateOne(
                    {"_id": row["_id"]},  # Định danh bản ghi
                    {
                        "$set": {
                            "LONG_KEMA_7": int(row["LONG_KEMA_7"]),
                        }
                    },
                )
            )

        if bulk_updates_1w:
            result_1w = self.model_1w.collection.bulk_write(bulk_updates_1w)
            print(
                f"Đã cập nhật {result_1w.modified_count} bản ghi LONG_KEMA_7 vào MongoDB!"
            )

        # data_1w["open_time"] = pd.to_datetime(data_1w["open_time"], unit="ms")

        # # Vẽ candlestick
        # fig = go.Figure(
        #     data=[
        #         go.Candlestick(
        #             x=data_1w["open_time"],
        #             open=data_1w["open"],
        #             high=data_1w["high"],
        #             low=data_1w["low"],
        #             close=data_1w["close"],
        #             name="Candlestick",
        #         )
        #     ]
        # )
        # fig.add_trace(
        #     go.Scatter(
        #         x=data_1w["open_time"],
        #         y=data_1w["KUP7"],
        #         mode="lines",
        #         line=dict(color="blue", width=1.5),
        #         name="KUP7",
        #     )
        # )

        # # Thêm đường KLO7 (đường hỗ trợ)
        # fig.add_trace(
        #     go.Scatter(
        #         x=data_1w["open_time"],
        #         y=data_1w["KLO7"],
        #         mode="lines",
        #         line=dict(color="red", width=1.5),
        #         name="KLO7",
        #     )
        # )
        # # Đánh dấu các nến có LONG_KEMA_15 == 1 bằng chấm xanh
        # long_points = data_1w[data_1w["LONG_KEMA_7"] == 1]
        # fig.add_trace(
        #     go.Scatter(
        #         x=long_points["open_time"],
        #         y=long_points["high"],  # Đặt điểm trên giá cao nhất của nến
        #         mode="markers",
        #         marker=dict(color="green", size=7, symbol="triangle-up"),
        #         name="LONG_KEMA_7",
        #     )
        # )

        # # Tuỳ chỉnh giao diện
        # fig.update_layout(
        #     title="BTCUSDT Candlestick with LONG_KEMA_7",
        #     xaxis_title="Time",
        #     yaxis_title="Price",
        #     xaxis_rangeslider_visible=False,
        #     template="plotly_dark",
        #     height=600,
        #     width=1000,
        # )

        # # Hiển thị
        # fig.show()
