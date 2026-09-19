import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Wallet,
  Activity,
  Award,
  Layers,
  Sparkles,
  ExternalLink,
  Copy,
  CheckCircle2,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

import { Navbar } from "./components/Navbar";
import { StatsTile } from "./components/StatsTile";
import { Button } from "./components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Input } from "./components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "./components/ui/dialog";
import { Toaster } from "./components/ui/sonner";

export function App() {
  const [darkMode, setDarkMode] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [recipient, setRecipient] = useState("0x71C845137636888209E047970DE33450B27265E9");

  const toggleTheme = () => {
    setDarkMode(!darkMode);
    if (!darkMode) {
      document.documentElement.classList.add("dark");
      toast.info("Đã chuyển sang Chế độ Tối (Dark Mode)");
    } else {
      document.documentElement.classList.remove("dark");
      toast.info("Đã chuyển sang Chế độ Sáng (Light Mode)");
    }
  };

  const copyAddress = (addr: string) => {
    navigator.clipboard.writeText(addr);
    toast.success("Đã sao chép địa chỉ ví!", {
      description: addr,
    });
  };

  const handleSendTransaction = (e: React.FormEvent) => {
    e.preventDefault();
    setModalOpen(false);
    toast.success("Giao dịch được gửi thành công!", {
      description: "Hash: 0x8a9f...3c21 • Xác nhận sau 2.4s",
    });
  };

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-200">
      <Toaster position="top-right" richColors />

      {/* 1. Header Navigation */}
      <Navbar
        darkMode={darkMode}
        onToggleTheme={toggleTheme}
        onOpenAction={() => setModalOpen(true)}
      />

      <main className="container mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:py-12">
        {/* 2. Hero Showcase Banner */}
        <section className="relative overflow-hidden rounded-2xl border border-border/80 bg-card p-6 sm:p-10 shadow-sm">
          {/* Subtle Ambient Background Gradient */}
          <div className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full bg-primary/10 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-20 -left-20 h-72 w-72 rounded-full bg-brand-cyan/10 blur-3xl" />

          <div className="relative z-10 max-w-3xl">
            <div className="flex items-center gap-2">
              <Badge variant="info" className="gap-1 px-3 py-1">
                <Sparkles className="h-3 w-3" />
                <span>Next-Gen Design System</span>
              </Badge>
              <Badge variant="success" className="gap-1">
                <ShieldCheck className="h-3 w-3" />
                <span>WCAG AA 6.7:1</span>
              </Badge>
            </div>

            <h1 className="mt-4 font-sans text-3xl font-extrabold tracking-tight sm:text-5xl lg:text-5xl">
              Nền Tảng Giao Diện <span className="text-primary">Học Thuật & Web3</span> Đẳng Cấp
            </h1>

            <p className="mt-3 text-base text-muted-foreground sm:text-lg">
              Được đồng bộ hoá từ kiến trúc thực chiến của hệ thống Wallet và Learn. 
              Áp dụng bảng màu HSL mượt mà, thang bo góc 5 bậc và tương tác chuyển động tự nhiên.
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Button variant="cta" size="lg" onClick={() => setModalOpen(true)}>
                <Zap className="h-4 w-4" />
                <span>Mở Dialog Thao Tác</span>
              </Button>
              <Button
                variant="outline"
                size="lg"
                onClick={() =>
                  toast.success("Thông báo kiểm thử", {
                    description: "Hệ thống Toast Sonner hoạt động trơn tru!",
                  })
                }
              >
                <span>Thử Toast Notification</span>
              </Button>
            </div>
          </div>
        </section>

        {/* 3. Stats Grid with Ambient Glow */}
        <section className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatsTile
            title="Tổng Số Dư Khả Dụng"
            value="14,250.85 ICTU"
            subtext="≈ 7,125.40 USD"
            icon={Wallet}
            trend="+12.5%"
            glowColor="primary"
          />
          <StatsTile
            title="Tần Suất Giao Dịch"
            value="1,420 Tx"
            subtext="32 giao dịch trong 24h qua"
            icon={Activity}
            trend="+5.2%"
            glowColor="success"
          />
          <StatsTile
            title="Chứng Chỉ Đã Cấp"
            value="89 NFT"
            subtext="Xác thực trên chuỗi khối"
            icon={Award}
            trend="+3 mới"
            glowColor="warning"
          />
          <StatsTile
            title="Bài Thực Hành Hoàn Thành"
            value="24/28 Lab"
            subtext="Tỷ lệ hoàn thành 85.7%"
            icon={Layers}
            trend="Xuất sắc"
            glowColor="primary"
          />
        </section>

        {/* 4. Tab Content & Data Table */}
        <section className="mt-10">
          <Tabs defaultValue="transactions" className="w-full">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-bold tracking-tight">Trung Tâm Dữ Liệu</h2>
                <p className="text-sm text-muted-foreground">Khám phá các thành phần UI mẫu</p>
              </div>
              <TabsList>
                <TabsTrigger value="transactions">Lịch Sử Giao Dịch</TabsTrigger>
                <TabsTrigger value="categories">Danh Mục & Tags</TabsTrigger>
                <TabsTrigger value="typography">Quy Chuẩn Font</TabsTrigger>
              </TabsList>
            </div>

            {/* TAB 1: Transactions Table */}
            <TabsContent value="transactions" className="mt-6">
              <Card className="overflow-hidden border-border/80 shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-border bg-muted/40 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      <tr>
                        <th className="px-6 py-3.5">Mã Giao Dịch (TxHash)</th>
                        <th className="px-6 py-3.5">Loại Tài Sản</th>
                        <th className="px-6 py-3.5">Giá Trị</th>
                        <th className="px-6 py-3.5">Trạng Thái</th>
                        <th className="px-6 py-3.5 text-right">Thao Tác</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {[
                        {
                          hash: "0x3f7a...9e12",
                          fullHash: "0x3f7a98b1c0e7d5421a89f9e123456789abcdef12",
                          type: "Chuyển Token",
                          category: "doc",
                          amount: "+250.00 ICTU",
                          status: "success",
                          statusText: "Thành công",
                        },
                        {
                          hash: "0x8b12...4c90",
                          fullHash: "0x8b1234567890abcdef1234567890abcdef4c9012",
                          type: "Mint Chứng Chỉ NFT",
                          category: "cert",
                          amount: "1 NFT",
                          status: "info",
                          statusText: "Đã ký",
                        },
                        {
                          hash: "0x1a45...8d33",
                          fullHash: "0x1a4567890abcdef1234567890abcdef128d3345",
                          type: "Biên dịch Smart Contract",
                          category: "code",
                          amount: "Gas: 0.004 ETH",
                          status: "warning",
                          statusText: "Đang duyệt",
                        },
                      ].map((item, idx) => (
                        <tr key={idx} className="transition-colors hover:bg-muted/30">
                          <td className="whitespace-nowrap px-6 py-4 font-mono font-medium text-foreground">
                            <span className="flex items-center gap-2">
                              {item.hash}
                              <button
                                onClick={() => copyAddress(item.fullHash)}
                                className="text-muted-foreground hover:text-primary transition-colors"
                                title="Sao chép đầy đủ"
                              >
                                <Copy className="h-3.5 w-3.5" />
                              </button>
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-6 py-4">
                            <Badge variant={item.category as any}>{item.type}</Badge>
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 font-mono font-semibold text-foreground">
                            {item.amount}
                          </td>
                          <td className="whitespace-nowrap px-6 py-4">
                            <Badge variant={item.status as any} className="gap-1">
                              <span className="h-1.5 w-1.5 rounded-full bg-current" />
                              {item.statusText}
                            </Badge>
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 text-right">
                            <Button variant="ghost" size="sm" className="h-8 gap-1 text-xs">
                              Chi tiết
                              <ExternalLink className="h-3 w-3" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </TabsContent>

            {/* TAB 2: Category Palette */}
            <TabsContent value="categories" className="mt-6">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {[
                  { title: "Tài liệu & Học thuật", tag: "doc", desc: "Giáo trình, bài báo nghiên cứu, đề án" },
                  { title: "Mã nguồn & Hợp đồng", tag: "code", desc: "Solidity smart contracts, GitHub repos" },
                  { title: "Chứng nhận & Văn bằng", tag: "cert", desc: "Chứng chỉ hoàn thành khóa học Web3, NFT bằng cấp" },
                  { title: "Dữ liệu & Báo cáo", tag: "info", desc: "Tập dữ liệu AI, telemetry nodes mạng thử nghiệm" },
                  { title: "Cảnh báo & Rủi ro", tag: "warning", desc: "Giao dịch cần xác nhận bổ sung hai lớp" },
                  { title: "Lỗi thực thi", tag: "danger", desc: "Giao dịch đảo ngược (reverted transaction)" },
                ].map((cat, i) => (
                  <Card key={i} className="border-border/70 p-5 hover:border-primary/40">
                    <div className="flex items-center justify-between">
                      <Badge variant={cat.tag as any}>Category: {cat.tag}</Badge>
                    </div>
                    <h3 className="mt-3 font-semibold text-foreground">{cat.title}</h3>
                    <p className="mt-1 text-sm text-muted-foreground">{cat.desc}</p>
                  </Card>
                ))}
              </div>
            </TabsContent>

            {/* TAB 3: Typography Rules */}
            <TabsContent value="typography" className="mt-6">
              <Card className="p-6">
                <div className="space-y-6">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      1. Font-sans (Inter) — UI Body & Controls
                    </span>
                    <p className="mt-1 text-base text-foreground font-sans">
                      The quick brown fox jumps over the lazy dog. Giao diện sắc nét, thân thiện và tối ưu trải nghiệm người dùng.
                    </p>
                  </div>
                  <div className="border-t border-border pt-4">
                    <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      2. Font-mono (JetBrains Mono) — Hex Hash & Code
                    </span>
                    <p className="mt-1 font-mono text-sm text-foreground">
                      0x71C845137636888209e047970de33450b27265e9 • GasPrice: 20 Gwei • Block: #18,920,412
                    </p>
                  </div>
                  <div className="border-t border-border pt-4">
                    <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      3. Font-display (Space Grotesk) — Hero Heading
                    </span>
                    <p className="mt-1 font-display text-2xl font-bold text-foreground">
                      Decentralized Knowledge Ledger & Identity Protocol
                    </p>
                  </div>
                </div>
              </Card>
            </TabsContent>
          </Tabs>
        </section>
      </main>

      {/* 5. Modal Dialog Example */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-primary" />
              Gửi Giao Dịch Thử Nghiệm
            </DialogTitle>
            <DialogDescription>
              Kiểm tra khả năng hiển thị của form input, nút bấm và trạng thái phản hồi.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSendTransaction} className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Địa chỉ nhận (Ví EVM)</label>
              <Input
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                placeholder="0x..."
                className="font-mono text-xs"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Số lượng (ICTU Token)</label>
              <Input type="number" defaultValue="50" step="0.1" required />
            </div>

            <DialogFooter className="mt-6">
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
                Hủy bỏ
              </Button>
              <Button type="submit" variant="cta">
                Xác nhận chuyển
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default App;
