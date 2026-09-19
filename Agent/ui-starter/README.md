# 🚀 Elite UI Design System - Starter Template

Dự án mẫu giao diện hoàn chỉnh chuẩn **Academic & Web3 Design System**, tích hợp sẵn:
- **Tailwind CSS (v3)** + **tailwindcss-animate**
- **Radix UI Primitives** + **shadcn/ui architecture**
- **Framer Motion** (Lò xo Apple Spring & Stagger animation)
- **Lucide Icons** & **Sonner Toast**
- Bảng màu **HSL Tokens**, thang bo góc **5 cấp bậc** và chế độ **Dark / Light Mode**.

---

## 📦 Cách Sử Dụng Cho Dự Án Mới

### Bước 1: Sao chép thư mục template sang dự án mới
```bash
cp -r /home/vmc01/ibnevm/templates/ui-starter /duong/dan/du-an-moi
cd /duong/dan/du-an-moi
```

### Bước 2: Cài đặt thư viện dependencies
```bash
npm install
```

### Bước 3: Khởi chạy môi trường phát triển
```bash
npm run dev
```

---

## 📂 Cấu Trúc Thư Mục

```
ui-starter/
├── components.json          # Cấu hình chuẩn shadcn/ui
├── tailwind.config.ts       # Mapping biến màu HSL, radius, fonts
├── src/
│   ├── index.css            # Toàn bộ Design Tokens (Light/Dark mode)
│   ├── main.tsx             # Entry point
│   ├── App.tsx              # Master Template (Hero, Stats, Tabs, Modal, Toasts)
│   ├── lib/
│   │   └── utils.ts         # Hàm tiện ích cn() (clsx + tailwind-merge)
│   └── components/
│       ├── Navbar.tsx       # Thanh điều hướng glassmorphism & nút Dark mode
│       ├── StatsTile.tsx    # Card chỉ số có hiệu ứng Ambient Radial Glow
│       └── ui/              # Bộ UI components cốt lõi:
│           ├── button.tsx   # Nút bấm (Default, CTA Gradient Glow, Outline...)
│           ├── card.tsx     # Thẻ hiển thị nội dung phân tầng
│           ├── badge.tsx    # Nhãn phân loại (3-layer Tint formula)
│           ├── input.tsx    # Ô nhập dữ liệu chuẩn form
│           ├── dialog.tsx   # Cửa sổ Modal pop-in
│           ├── tabs.tsx     # Tab chuyển đổi nội dung
│           └── sonner.tsx   # Toast thông báo góc màn hình
```
