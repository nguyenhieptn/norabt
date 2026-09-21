---
name: ui-design-system
description: Quy chuẩn thiết kế UI/UX cao cấp và hệ thống Design System chuẩn mực. Kết hợp triết lý học thuật tinh tế (Academic Aesthetics) và công nghệ Web3 hiện đại (Glow, Glassmorphism, HSL/OKLCH, Tailwind, shadcn/ui, Framer Motion).
---

# 🎨 HỆ THỐNG THIẾT KẾ UI ĐẲNG CẤP (ELITE UI DESIGN SYSTEM)
> **Tài liệu hướng dẫn & Skill thiết kế giao diện hoàn chỉnh**: Được đúc kết từ hệ thống thực chiến của `wallet` và `learn`. Dành cho lập trình viên và AI Agent khi xây dựng giao diện web hiện đại, sang trọng và chuẩn mực.

---

## MỤC LỤC
1. [Triết Lý Cốt Lõi (Core Principles)](#1-triết-lý-cốt-lõi-core-principles)
2. [Hệ Thống Phối Màu & Tokens (HSL & OKLCH)](#2-hệ-thống-phối-màu--tokens-hsl--oklch)
3. [Hệ Thống Typography Phân Tầng](#3-hệ-thống-typography-phân-tầng)
4. [Thang Bo Góc (Border Radius Hierarchy)](#4-thang-bo-góc-border-radius-hierarchy)
5. [Hiệu Ứng Thị Giác, Chiều Sâu & Glassmorphism](#5-hiệu-ứng-thị-giác-chiều-sâu--glassmorphism)
6. [Micro-Animations & Chuyển Động (Framer Motion)](#6-micro-animations--chuyển-động-framer-motion)
7. [Bộ Mã Nguồn Khởi Tạo (Full Boilerplate Code)](#7-bộ-mã-nguồn-khởi-tạo-full-boilerplate-code)
   - [7.1 package.json (Dependencies)](#71-packagejson-dependencies)
   - [7.2 components.json (shadcn/ui)](#72-componentsjson-shadcnui)
   - [7.3 tailwind.config.ts](#73-tailwindconfigts)
   - [7.4 src/index.css (Design Tokens)](#74-srcindexcss-design-tokens)
   - [7.5 src/lib/utils.ts (Class Merger)](#75-srclibutilsts-class-merger)
8. [Quy Tắc Vàng Thiết Kế (Do's & Don'ts)](#8-quy-tắc-vàng-thiết-kế-dos--donts)

---

## 1. Triết Lý Cốt Lõi (Core Principles)

1. **Typography-First & Whitespace**:
   - Vẻ đẹp sang trọng không đến từ các hình khối rối rắm hay màu sắc quá rực rỡ, mà đến từ **khoảng trắng thở (whitespace)**, tỷ lệ phân tầng phông chữ chuẩn xác và căn lề hài hòa.
2. **Chuẩn tương phản WCAG AA (Contrast Ratio ≥ 4.5:1)**:
   - Tất cả văn bản đọc phải đảm bảo tỷ lệ tương phản tối thiểu **4.5:1** trên nền sáng lẫn tối.
   - **Tách bạch 2 vai trò màu thương hiệu**:
     - *Màu nhận diện trang trí* (dải màu, viền, thanh progress): Có thể dùng màu tươi sáng nhẹ nhàng.
     - *Màu hành động (CTA button, link, tiêu đề)*: Phải dùng phiên bản có độ bão hòa và độ sáng được tính toán để chữ trắng trên nền đạt độ tương phản từ **6.7:1**.
3. **Màu HSL / OKLCH với Alpha Blending**:
   - Khai báo token màu dưới dạng `H S% L%` (không bọc sẵn hàm `hsl()`) để Tailwind CSS có thể can thiệp opacity tùy ý: `bg-primary/10`, `border-border/60`, `text-primary/90`.
4. **Chiều sâu không gian 3 lớp (Elevation Layering)**:
   - Lớp 1: Mặt nền (`--background`).
   - Lớp 2: Mặt thẻ nổi (`--card`) kết hợp viền mờ 1px (`--border`).
   - Lớp 3: Ánh sáng phát quang nhẹ (`--glow-primary`) hoặc bóng đổ đa tầng mịn (`--shadow-card`).

---

## 2. Hệ Thống Phối Màu & Tokens (HSL & OKLCH)

### 2.1 Bảng Màu Giao Diện Sáng / Tối (Light & Dark Theme)

Mọi màu sắc được tính toán cẩn thận để không bao giờ xuất hiện màu đen thô ráp (`#000000`) hay trắng tinh chói lóa (`#ffffff` trên nền xám bệt).

```css
/* ═══════════════════════════════════════════════════════════════════════════
   LIGHT THEME (Trong trẻo, thanh lịch, chuẩn mực học thuật)
   ═══════════════════════════════════════════════════════════════════════════ */
:root {
  /* Mặt nền & Thẻ bề mặt */
  --background:        210 22% 98%;   /* Xám ngọc nhạt cao cấp */
  --foreground:        222 40% 14%;   /* Đen than chì (Slate Dark) */
  --card:              0 0% 100%;     /* Trắng ngọc nổi trên nền */
  --card-foreground:   222 40% 14%;
  --border:            215 18% 88%;   /* Viền xám khói nhẹ */
  --input:             215 18% 88%;
  --ring:              217 85% 50%;

  /* Văn bản phụ */
  --muted:             210 20% 95%;
  --muted-foreground:  215 16% 42%;   /* Tương phản 5.42:1 -> Đạt WCAG AA */

  /* Màu thương hiệu: Royal Azure & Cyan */
  --primary:           217 85% 50%;   /* Nút bấm chính (#2563eb), chữ trắng đạt 6.70:1 */
  --primary-foreground:0 0% 100%;
  --brand-blue:        217 91% 60%;   /* Xanh Azure mềm cho viền, badge */
  --brand-cyan:        199 89% 50%;   /* Xanh ngọc Cyan cho highlight */
  --accent:            217 85% 50%;
  --accent-foreground: 0 0% 100%;

  /* Màu trạng thái nghiệp vụ (Academic Muted Semantic) */
  --success:           174 60% 28%;   /* Xanh ngọc lục bảo sâu (Emerald) */
  --warning:           38 78% 42%;    /* Vàng hổ phách trầm (Amber) */
  --danger:            0 65% 46%;     /* Đỏ thẫm cảnh báo (Crimson) */

  /* Màu danh mục / Tag phân loại (Category Palette) */
  --cat-doc:           217 85% 50%;   /* Tài liệu / Văn bản */
  --cat-code:          199 89% 45%;   /* Lập trình / Smart Contract */
  --cat-cert:          38 78% 42%;    /* Chứng chỉ / Huy hiệu */
  --cat-data:          190 65% 32%;   /* Dữ liệu / Phân tích */
  --cat-event:         340 60% 46%;   /* Sự kiện / Workshop */
  --cat-reward:        160 55% 30%;   /* Phần thưởng / Token */
}

/* ═══════════════════════════════════════════════════════════════════════════
   DARK THEME (Sâu thẳm, dịu mắt, huyền bí phong cách Web3)
   ═══════════════════════════════════════════════════════════════════════════ */
.dark {
  --background:        222 47% 7%;    /* Xanh đen than vũ trụ (#0b0f19) */
  --foreground:        210 40% 98%;   /* Trắng sáng ngà */
  --card:              222 47% 10%;   /* Lớp card nổi hơn nền 1 bậc */
  --card-foreground:   210 40% 98%;
  --border:            217 32% 17%;   /* Đường viền mờ tối */
  --input:             217 32% 17%;
  --ring:              217 91% 60%;

  --muted:             217 32% 14%;
  --muted-foreground:  215 20% 65%;

  --primary:           217 91% 60%;   /* Tăng độ sáng để nổi trên nền tối */
  --primary-foreground:222 47% 7%;

  --success:           172 55% 55%;
  --warning:           38 85% 62%;
  --danger:            0 75% 66%;
}
```

### 2.2 Không Gian Màu OKLCH (Cho Hero Banner & Web3 Landing)
Sử dụng không gian màu `oklch` loại bỏ hoàn toàn hiện tượng chuyển màu bị đục:

```css
.landing-hero {
  --landing-background: oklch(0.13 0.04 250);       /* Nền đen sâu ánh xanh */
  --landing-card:       oklch(0.17 0.05 252 / 0.6); /* Kính mờ phủ tối */
  --landing-primary:    oklch(0.82 0.18 200);       /* Cyan Neon điện tử */
  --landing-accent:     oklch(0.70 0.22 290);       /* Tím Cyber rực rỡ */
  --gradient-cta:       linear-gradient(135deg, oklch(0.82 0.18 200), oklch(0.70 0.22 290));
}
```

---

## 3. Hệ Thống Typography Phân Tầng

Nhúng bộ 4 font Google Fonts vào thẻ `<head>` của `index.html`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Roboto:wght@400;500;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
```

### Phân vai trò phông chữ:
1. **`Inter`** (`font-sans`): Phông chữ mặc định cho toàn bộ giao diện UI, form controls, nút bấm, menu, bảng biểu. Cực kỳ dễ đọc ở size nhỏ (12px - 14px).
2. **`Roboto`** (`font-serif` hoặc heading alternative): Dùng cho tiêu đề bài giảng, tài liệu hướng dẫn học thuật.
3. **`JetBrains Mono`** (`font-mono`): Bắt buộc dùng cho:
   - Địa chỉ ví blockchain (`0x71C...49b2`)
   - Transaction hash (`0xfa3...`)
   - Số dư token lớn
   - Code Solidity / JavaScript / JSON log.
4. **`Space Grotesk`** (`font-display`): Dành riêng cho tiêu đề Hero cỡ lớn (`text-4xl` đến `text-6xl`) trên các trang Landing Page hiện đại.

---

## 4. Thang Bo Góc (Border Radius Hierarchy)

Không áp dụng một chỉ số bo góc ngẫu nhiên. Mọi góc bo tuân thủ thang 5 cấp độ chuẩn thiết kế hiện đại:

| Biến CSS | Giá Trị | Đối Tượng Áp Dụng | Class Tailwind |
| :--- | :--- | :--- | :--- |
| `--radius-xs` | `0.25rem` (4px) | Badge nhỏ, chip đếm số, tag trạng thái cực gọn | `rounded-xs` |
| `--radius-sm` | `0.5rem` (8px) | Nút bấm nhỏ, ô nhập input, select box | `rounded-sm` |
| `--radius-md` | `0.75rem` (12px) | Dropdown menu, popover, button tiêu chuẩn, icon wrapper | `rounded-md` |
| `--radius-lg` | `1.0rem` (16px) | Modal dialog, notification sheet, drawer | `rounded-lg` |
| `--radius-xl` | `1.25rem` (20px) | Thẻ card chính, hero container, khung thống kê | `rounded-xl` |

---

## 5. Hiệu Ứng Thị Giác, Chiều Sâu & Glassmorphism

### 5.1 Hiệu Ứng Phát Quang Nhẹ (Ambient Glow)
Tránh bóng đen đặc làm tối giao diện. Thay vào đó, dùng ánh sáng cùng tone màu dịu nhẹ:

```css
/* Ánh sáng dịu quanh nút hoặc khối được active */
--glow-primary: 0 1px 2px hsl(222 40% 14% / 0.05), 0 2px 8px hsl(217 85% 50% / 0.08);
--glow-accent:  0 1px 2px hsl(222 40% 14% / 0.05), 0 2px 8px hsl(174 60% 28% / 0.08);
```

### 5.2 Kính Mờ Cao Cấp (Glassmorphism)
```css
.glass-card {
  background: hsl(var(--card) / 0.80);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid hsl(var(--border) / 0.60);
  box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
}
```

### 5.3 Gradient CTA Đẳng Cấp
```css
/* Dải chuyển màu mềm mại cho nút Call-to-Action */
--gradient-cta: linear-gradient(135deg, hsl(217 85% 50%) 0%, hsl(199 89% 48%) 100%);
```

---

## 6. Micro-Animations & Chuyển Động (Framer Motion)

Sử dụng thư viện `framer-motion` với các thông số chuyển động tự nhiên:

```tsx
import { motion } from "framer-motion";

// 1. Cấu hình lò xo mượt mà (Apple Spring)
export const springTransition = {
  type: "spring",
  stiffness: 400,
  damping: 30,
};

// 2. Hiệu ứng Hover & Nhấn nút tinh tế
export const interactiveMotion = {
  whileHover: { y: -2, transition: { duration: 0.15 } },
  whileTap: { scale: 0.97 }
};

// 3. Hiệu ứng Modal / Popup mở ra
export const modalAnimation = {
  initial: { opacity: 0, scale: 0.96, y: 8 },
  animate: { opacity: 1, scale: 1, y: 0 },
  exit: { opacity: 0, scale: 0.96, y: 8 },
  transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] } // easeOutExpo
};

// 4. Stagger Animation cho danh sách Card
export const containerStagger = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06 }
  }
};

export const itemFadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } }
};
```

---

## 7. Bộ Mã Nguồn Khởi Tạo (Full Boilerplate Code)

### 7.1 `package.json` (Dependencies)
```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.6.0",
    "class-variance-authority": "^0.7.1",
    "lucide-react": "^0.462.0",
    "framer-motion": "^12.31.0",
    "sonner": "^1.7.4",
    "@radix-ui/react-slot": "^1.2.3",
    "@radix-ui/react-dialog": "^1.1.14",
    "@radix-ui/react-dropdown-menu": "^2.1.15",
    "@radix-ui/react-tabs": "^1.1.12",
    "@radix-ui/react-tooltip": "^1.2.7",
    "@radix-ui/react-progress": "^1.1.7"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.17",
    "tailwindcss-animate": "^1.0.7",
    "postcss": "^8.5.6",
    "autoprefixer": "^10.4.21",
    "typescript": "^5.8.3"
  }
}
```

### 7.2 `components.json` (Chuẩn shadcn/ui)
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/index.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui"
  }
}
```

### 7.3 `tailwind.config.ts`
```ts
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      fontFamily: {
        sans: ['Inter', 'Roboto', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Space Grotesk', 'sans-serif'],
      },
      borderRadius: {
        xs: "var(--radius-xs)",
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        success: "hsl(var(--success))",
        warning: "hsl(var(--warning))",
        danger: "hsl(var(--danger))",
        brand: {
          blue: "hsl(var(--brand-blue))",
          cyan: "hsl(var(--brand-cyan))",
        },
        cat: {
          doc: "hsl(var(--cat-doc))",
          code: "hsl(var(--cat-code))",
          cert: "hsl(var(--cat-cert))",
          data: "hsl(var(--cat-data))",
          event: "hsl(var(--cat-event))",
          reward: "hsl(var(--cat-reward))",
        },
      },
      boxShadow: {
        glow: "var(--glow-primary)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
```

### 7.4 `src/index.css` (Design Tokens)
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Roboto:wght@400;500;700&family=Space+Grotesk:wght@500;600;700&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background:        210 22% 98%;
    --foreground:        222 40% 14%;
    --card:              0 0% 100%;
    --card-foreground:   222 40% 14%;
    --border:            215 18% 88%;
    --input:             215 18% 88%;
    --ring:              217 85% 50%;
    --muted:             210 20% 95%;
    --muted-foreground:  215 16% 42%;
    --primary:           217 85% 50%;
    --primary-foreground:0 0% 100%;
    --brand-blue:        217 91% 60%;
    --brand-cyan:        199 89% 50%;
    --accent:            217 85% 50%;
    --accent-foreground: 0 0% 100%;
    --success:           174 60% 28%;
    --warning:           38 78% 42%;
    --danger:            0 65% 46%;

    --radius-xs: 0.25rem;
    --radius-sm: 0.5rem;
    --radius-md: 0.75rem;
    --radius-lg: 1.0rem;
    --radius-xl: 1.25rem;

    --glow-primary: 0 1px 2px hsl(222 40% 14% / 0.05), 0 2px 8px hsl(217 85% 50% / 0.08);
  }

  .dark {
    --background:        222 47% 7%;
    --foreground:        210 40% 98%;
    --card:              222 47% 10%;
    --card-foreground:   210 40% 98%;
    --border:            217 32% 17%;
    --input:             217 32% 17%;
    --ring:              217 91% 60%;
    --muted:             217 32% 14%;
    --muted-foreground:  215 20% 65%;
    --primary:           217 91% 60%;
    --primary-foreground:222 47% 7%;
    --success:           172 55% 55%;
    --warning:           38 85% 62%;
    --danger:            0 75% 66%;
  }

  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground font-sans antialiased;
  }
}
```

### 7.5 `src/lib/utils.ts` (Class Merger)
```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

---

## 8. Quy Tắc Vàng Thiết Kế (Do's & Don'ts)

| ❌ ĐIỀU NÊN TRÁNH (DON'T) | ✅ CÁCH THIẾT KẾ ĐÚNG (DO) |
| :--- | :--- |
| **Màu gốc thô**: Dùng màu thuần `#ff0000`, `#00ff00`, `#0000ff`. | **Màu tinh chỉnh**: Dùng HSL Azure (`217 85% 50%`), Emerald (`174 60% 28%`). |
| **Chữ đen tuyền**: Dùng `#000000` trên nền trắng tinh `#ffffff`. | **Màu than chì Slate**: Dùng `hsl(222 40% 14%)` trên nền xám ngọc `hsl(210 22% 98%)`. |
| **Bo góc hỗn loạn**: Mỗi chỗ một bán kính ngẫu nhiên (5px, 9px, 30px). | **Hệ thống 5 bậc**: Tuân thủ chuẩn `--radius-xs` đến `--radius-xl`. |
| **Bóng đổ đen đục**: Dùng `box-shadow: 0 10px 20px rgba(0,0,0,0.5)`. | **Bóng mịn đa tầng**: Dùng ambient shadow mờ kết hợp glow nhẹ cùng tone màu. |
| **Font chữ cẩu thả**: Dùng font Sans thường để hiển thị mã Hex / TxHash. | **Monospace chuẩn**: Luôn dùng `JetBrains Mono` cho hash, address và số tiền. |
| **Tương tác đơ cứng**: Không có trạng thái hover, focus, active. | **Micro-feedback**: Thêm `transition-all duration-150` hoặc Framer Motion spring. |
