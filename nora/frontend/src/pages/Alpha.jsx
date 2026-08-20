import React from 'react'
import { useSearchParams } from 'react-router-dom'
import KhoAlpha from './Strategies'
import PhienDao from './Miner'

/**
 * Alpha — chiến lược và việc đào ra chiến lược vốn là một việc,
 * nên gộp chung một mục, đổi góc nhìn bằng nút thay vì tách hai trang.
 */
export default function Alpha() {
  const [sp, setSp] = useSearchParams()
  const tab = sp.get('tab') === 'dao' ? 'dao' : 'kho'
  const doi = (t) => setSp(t === 'dao' ? { tab: 'dao' } : {}, { replace: true })

  return (
    <>
      <div className="head">
        <div className="head-row">
          <h1>Alpha</h1>
          <div className="switch">
            <button className={tab === 'kho' ? 'on' : ''} onClick={() => doi('kho')}>Kho alpha</button>
            <button className={tab === 'dao' ? 'on' : ''} onClick={() => doi('dao')}>Đào alpha</button>
          </div>
        </div>
        <p>
          {tab === 'kho'
            ? 'Kho chiến thuật đang có — bấm vào một dòng để xem điều kiện vào lệnh.'
            : 'Quét dải tham số để đào ra alpha mới. Bấm vào một phiên để xem bảng xếp hạng và tinh chỉnh tham số.'}
        </p>
      </div>

      {tab === 'kho' ? <KhoAlpha /> : <PhienDao />}
    </>
  )
}
