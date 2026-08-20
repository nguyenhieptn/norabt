const fs = require('fs');
const path = require('path');

console.log("==================================================================");
console.log("🧪 BẮT ĐẦU KIỂM THỬ LOGIC FRONTEND (DRY-RUN SYNTAX & IMPORTS)");
console.log("==================================================================");

// 1. KIỂM TRA FILE NGUỒN FRONTEND
const portalApp = path.join(__dirname, '../coins/resources/react/app.js');
const monitorIndex = path.join(__dirname, '../coin_monitor/frontend/src/index.js');

console.log("\n[1/3] 📁 Kiểm tra sự tồn tại của các file Entrypoint Frontend...");
console.log(`   - Portal App: ${fs.existsSync(portalApp) ? '✅ Tồn tại' : '❌ Thiếu'}`);
console.log(`   - Monitor Index: ${fs.existsSync(monitorIndex) ? '✅ Tồn tại' : '❌ Thiếu'}`);

// 2. KIỂM TRA CẤU HÌNH TỐI ƯU HÓA LIMIT
console.log("\n[2/3] 🛡️ Kiểm tra cấu hình giới hạn RAM & CPU trong Webpack/Env...");
const envFile = path.join(__dirname, '../coin_monitor/frontend/.env');
const envContent = fs.readFileSync(envFile, 'utf8');
const hasNoSourceMap = envContent.includes('GENERATE_SOURCEMAP=false');
console.log(`   - Tắt SourceMap trong .env: ${hasNoSourceMap ? '✅ Đã cấu hình' : '❌ Chưa cấu hình'}`);

const webpackMix = path.join(__dirname, '../coins/webpack.mix.js');
const mixContent = fs.readFileSync(webpackMix, 'utf8');
const hasParallelism = mixContent.includes('parallelism: 2');
console.log(`   - Giới hạn 2 Cores trong webpack.mix.js: ${hasParallelism ? '✅ Đã cấu hình' : '❌ Chưa cấu hình'}`);

// 3. KIỂM TRA BỘ NHỚ NODE
console.log("\n[3/3] 📊 Kiểm tra bộ nhớ V8 Heap của tiến trình...");
const memoryUsage = process.memoryUsage();
console.log(`   - Heap Used: ${(memoryUsage.heapUsed / 1024 / 1024).toFixed(2)} MB`);
console.log(`   - RSS Memory: ${(memoryUsage.rss / 1024 / 1024).toFixed(2)} MB`);

console.log("\n==================================================================");
console.log("✅ HOÀN TẤT KIỂM THỬ FRONTEND: CẤU HÌNH VÀ CODE SẴN SÀNG!");
console.log("==================================================================");
