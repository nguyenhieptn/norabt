import React from 'react'
import { money, pct, num, int } from '../lib/format'

/** Lỗ gộp trong dữ liệu là số dương (độ lớn) — hiển thị đúng dấu âm cho dễ đọc */
const am = (v) => money(-Math.abs(Number(v || 0)))

/** Xếp hạng một chỉ số theo các mốc quen dùng trong đánh giá chiến lược.
 *  moc: [ngưỡng, nhãn, tone] xếp từ tốt xuống kém; cao = giá trị càng lớn càng tốt. */
function xep(v, moc, cao = true) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return null
  const x = Number(v)
  for (const [nguong, nhan, tone] of moc) {
    if (cao ? x >= nguong : x <= nguong) return { nhan, tone }
  }
  const cuoi = moc[moc.length - 1]
  return { nhan: cuoi[1], tone: cuoi[2] }
}

/** Danh sách chỉ số đánh giá một lần chạy, gom theo nhóm. */
export function bangChiSo(m) {
  const G = (ten, hang) => ({ ten, hang: hang.filter(Boolean) })
  const R = (ten, gt, tone, danh, y) => ({ ten, gt, tone: tone || '', danh, y })

  return [
    G('Hiệu quả', [
      R('Lãi lỗ ròng', money(m.net), Number(m.net) > 0 ? 'up' : 'down',
        xep(m.net, [[0.0001, 'Có lãi', 'tot'], [-1e18, 'Lỗ', 'xau']]),
        'tổng lãi lỗ của mọi lệnh, đã trừ phí'),
      R('Tỷ suất sinh lời', pct(m.roi_pct), Number(m.roi_pct) > 0 ? 'up' : 'down', null,
        'lãi lỗ ròng so với vốn ban đầu'),
      R('Tăng trưởng năm (CAGR)', pct(m.cagr_pct), '', null,
        m.du_dai_de_quy_nam === false
          ? `mới ${int(m.so_ngay)} ngày — quá ngắn để quy đổi về năm`
          : `quy đổi về một năm, tính trên ${int(m.so_ngay)} ngày chạy`),
      R('Kỳ vọng mỗi lệnh', money(m.expectancy),
        Number(m.expectancy) > 0 ? 'up' : 'down', null,
        'trung bình một lệnh mang về bao nhiêu'),
      R('Số dư đầu → cuối', `${num(m.start_balance)} → ${num(m.end_balance)}`, '', null,
        'vốn lúc bắt đầu và lúc kết thúc'),
    ]),

    G('Rủi ro', [
      R('Sụt giảm tối đa (MDD)', pct(m.mdd_pct), 'down',
        xep(m.mdd_pct, [[25, 'Chấp nhận được', 'tot'], [50, 'Cao', 'canh'], [1e18, 'Rất rủi ro', 'xau']], false),
        m.peak_at ? `từ đỉnh ${m.peak_at} xuống đáy ${m.trough_at}` : 'mức tụt sâu nhất của đường vốn'),
      R('Mức sụt giảm tuyệt đối', am(m.mdd_abs), 'down', null,
        'số tiền mất đi trong đợt tụt sâu nhất'),
      R('Biến động năm', pct(m.volatility_pct), '',
        xep(m.volatility_pct, [[50, 'Vừa phải', 'tot'], [100, 'Cao', 'canh'], [1e18, 'Rất cao', 'xau']], false),
        'độ dao động của lãi lỗ hằng ngày, quy về năm'),
      R('Chuỗi thua dài nhất', `${int(m.max_loss_streak)} lệnh`, '',
        xep(m.max_loss_streak, [[10, 'Ngắn', 'tot'], [30, 'Dài', 'canh'], [1e18, 'Rất dài', 'xau']], false),
        'số lệnh thua liên tiếp — thước đo sức chịu đựng'),
      R('Chuỗi thắng dài nhất', `${int(m.max_win_streak)} lệnh`, '', null,
        'số lệnh thắng liên tiếp'),
    ]),

    G('Chất lượng', [
      R('Sharpe', num(m.sharpe), '',
        xep(m.sharpe, [[2, 'Tốt', 'tot'], [1, 'Chấp nhận được', 'kha'], [-1e18, 'Kém', 'xau']]),
        'lãi thu được trên mỗi đơn vị biến động'),
      R('Sortino', num(m.sortino), '',
        xep(m.sortino, [[2, 'Tốt', 'tot'], [1, 'Chấp nhận được', 'kha'], [-1e18, 'Kém', 'xau']]),
        'như Sharpe nhưng chỉ phạt biến động phía lỗ'),
      R('Calmar', num(m.calmar), '',
        xep(m.calmar, [[3, 'Tốt', 'tot'], [1, 'Chấp nhận được', 'kha'], [-1e18, 'Kém', 'xau']]),
        m.calmar === null || m.calmar === undefined
          ? 'cần ít nhất 30 ngày dữ liệu mới tính được'
          : 'tăng trưởng năm chia cho sụt giảm tối đa'),
      R('Hệ số lợi nhuận', num(m.profit_factor), '',
        xep(m.profit_factor, [[1.5, 'Tốt', 'tot'], [1.1, 'Mỏng', 'canh'], [1, 'Rất mỏng', 'canh'], [-1e18, 'Thua lỗ', 'xau']]),
        'tổng lãi chia tổng lỗ — dưới 1 là lỗ'),
    ]),

    G('Giao dịch', [
      R('Số lệnh', int(m.trades), '', null, 'tổng số lệnh đã đóng'),
      R('Thắng / Thua', `${int(m.wins)} / ${int(m.losses)}`, '', null, null),
      R('Tỷ lệ thắng', pct(m.winrate), '',
        xep(m.winrate, [[50, 'Cao', 'tot'], [35, 'Trung bình', 'kha'], [-1, 'Thấp', 'canh']]),
        'tỷ lệ thắng thấp vẫn có thể lãi nếu lệnh thắng đủ lớn'),
      R('Lãi gộp / Lỗ gộp', `${money(m.gross_profit)} / ${am(m.gross_loss)}`, '', null,
        'cộng riêng phần lãi và phần lỗ'),
      R('Lệnh lãi nhất / lỗ nhất', `${money(m.best)} / ${money(m.worst)}`, '', null, null),
      R('Độ lệch chuẩn lãi lỗ', num(m.pnl_sd), '', null,
        'lãi lỗ mỗi lệnh phân tán quanh mức trung bình bao nhiêu'),
    ]),
  ]
}

/**
 * Bảng thống kê dạng tham số của một lần chạy.
 * Khác với các bảng thống kê lệnh: mỗi dòng ở đây là một chỉ số đánh giá,
 * kèm mức xếp hạng và một câu giải thích ý nghĩa.
 */
export default function MetricTable({ m, gonNheYNghia = false }) {
  const nhom = bangChiSo(m)
  const thieu_von = m.co_duong_von === false
  return (
    <div className="tblwrap">
      {thieu_von && (
        <div className="pre luu_y" style={{ margin: '12px 14px' }}>
          Lần chạy này không bật theo dõi số dư nên không có đường vốn — mọi chỉ số
          rủi ro (sụt giảm, Sharpe, Sortino, Calmar, biến động) không tính được.
          Các chỉ số tính từ danh sách lệnh vẫn đúng.
        </div>
      )}
      <table className="chiso">
        <thead>
          <tr>
            <th>Chỉ số</th>
            <th className="n">Giá trị</th>
            <th>Đánh giá</th>
            {!gonNheYNghia && <th>Ý nghĩa</th>}
          </tr>
        </thead>
        <tbody>
          {nhom.map((g) => (
            <React.Fragment key={g.ten}>
              <tr className="nhom">
                <td colSpan={gonNheYNghia ? 3 : 4}>{g.ten}</td>
              </tr>
              {g.hang.map((h) => (
                <tr key={h.ten}>
                  <td>{h.ten}</td>
                  <td className={`n ${h.tone}`}>{h.gt}</td>
                  <td>{h.danh ? <span className={`tag ${h.danh.tone}`}>{h.danh.nhan}</span> : '—'}</td>
                  {!gonNheYNghia && (
                    <td style={{ color: 'var(--ink-3)', fontSize: 12.5, whiteSpace: 'normal' }}>
                      {h.y || ''}
                    </td>
                  )}
                </tr>
              ))}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}
