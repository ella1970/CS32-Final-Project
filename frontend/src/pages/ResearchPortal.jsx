// src/pages/ResearchPortal.jsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { sessionsApi } from '../api/client'

function downloadCSV(rows) {
  if (!rows.length) return
  const headers = Object.keys(rows[0])
  const csv = [
    headers.join(','),
    ...rows.map(r => headers.map(h => {
      const v = r[h]
      if (v == null) return ''
      if (typeof v === 'string' && v.includes(',')) return `"${v}"`
      return v
    }).join(','))
  ].join('\n')
  const blob = new URL(`data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`)
  const a = document.createElement('a')
  a.href = `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`
  a.download = `swimload_export_${new Date().toISOString().slice(0,10)}.csv`
  a.click()
}

export default function ResearchPortal() {
  const [rows, setRows]         = useState([])
  const [loading, setLoading]   = useState(true)
  const [filter, setFilter]     = useState({ subject: '', arm: 'all', injured: 'all' })
  const [sort, setSort]         = useState({ key: 'subject_code', dir: 1 })

  useEffect(() => {
    sessionsApi.table().then(data => { setRows(data); setLoading(false) })
  }, [])

  function toggleSort(key) {
    setSort(s => ({ key, dir: s.key === key ? -s.dir : 1 }))
  }

  const filtered = rows
    .filter(r => !filter.subject || r.subject_code.toLowerCase().includes(filter.subject.toLowerCase()))
    .filter(r => filter.arm === 'all' || r.arm_side === filter.arm)
    .filter(r => filter.injured === 'all' ||
      (filter.injured === 'yes' ? r.is_injured_arm : !r.is_injured_arm))
    .sort((a, b) => {
      const av = a[sort.key], bv = b[sort.key]
      if (av == null) return 1; if (bv == null) return -1
      return (av < bv ? -1 : av > bv ? 1 : 0) * sort.dir
    })

  const SortHdr = ({ k, label }) => (
    <th onClick={() => toggleSort(k)} style={{ cursor: 'pointer', userSelect: 'none' }}>
      {label} {sort.key === k ? (sort.dir === 1 ? '↑' : '↓') : ''}
    </th>
  )

  function fmt(v, dec=2, unit='') {
    if (v == null) return <span style={{ color: 'var(--text-muted)' }}>—</span>
    return <>{parseFloat(v).toFixed(dec)}{unit}</>
  }

  return (
    <div>
      <div className="section-header" style={{ marginBottom: 28 }}>
        <div>
          <h1 style={{ fontFamily: 'Space Mono', fontSize: 20, fontWeight: 700, marginBottom: 4 }}>
            Research Portal
          </h1>
          <p style={{ color: 'var(--text-dim)', fontSize: 14 }}>
            All subjects × sessions · {filtered.length} records
          </p>
        </div>
        <button className="btn btn-secondary" onClick={() => downloadCSV(filtered)}>
          ↓ Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Subject code</label>
            <input className="form-input" placeholder="Filter…" style={{ width: 160 }}
                   value={filter.subject}
                   onChange={e => setFilter(f => ({ ...f, subject: e.target.value }))} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Arm side</label>
            <select className="form-select" style={{ width: 130 }} value={filter.arm}
                    onChange={e => setFilter(f => ({ ...f, arm: e.target.value }))}>
              <option value="all">All</option>
              <option value="left">Left</option>
              <option value="right">Right</option>
            </select>
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Arm type</label>
            <select className="form-select" style={{ width: 140 }} value={filter.injured}
                    onChange={e => setFilter(f => ({ ...f, injured: e.target.value }))}>
              <option value="all">All</option>
              <option value="yes">Injured only</option>
              <option value="no">Healthy only</option>
            </select>
          </div>
          <button className="btn btn-secondary btn-sm"
                  onClick={() => setFilter({ subject: '', arm: 'all', injured: 'all' })}>
            Clear
          </button>
        </div>
      </div>

      {/* Summary stats */}
      {filtered.length > 0 && (
        <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(5,1fr)', marginBottom: 20 }}>
          {[
            { label: 'Subjects',    val: new Set(filtered.map(r => r.subject_id)).size },
            { label: 'Sessions',    val: filtered.length },
            {
              label: 'Avg Total Load',
              val: (filtered.filter(r => r.total_load != null)
                            .reduce((a,r) => a + r.total_load, 0) /
                   Math.max(1, filtered.filter(r => r.total_load != null).length)).toFixed(1) + ' rad'
            },
            {
              label: 'Avg Pain',
              val: filtered.filter(r => r.pain_score != null).length
                ? (filtered.filter(r => r.pain_score != null)
                           .reduce((a,r) => a + r.pain_score, 0) /
                   filtered.filter(r => r.pain_score != null).length).toFixed(1) + '/10'
                : '—'
            },
            { label: 'Injured sessions', val: filtered.filter(r => r.is_injured_arm).length },
          ].map(s => (
            <div key={s.label} className="stat-card">
              <div className="stat-label">{s.label}</div>
              <div className="stat-value" style={{ fontSize: 22 }}>{s.val}</div>
            </div>
          ))}
        </div>
      )}

      {/* Table */}
      <div className="card">
        {loading ? (
          <div className="loading"><div className="spinner"/>Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="empty">
            <h3>No sessions match your filters</h3>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <SortHdr k="subject_code"  label="Subject" />
                  <SortHdr k="session_number" label="Session #" />
                  <SortHdr k="arm_side"      label="Arm" />
                  <th>Type</th>
                  <SortHdr k="started_at"    label="Date" />
                  <SortHdr k="pain_score"    label="Pain" />
                  <SortHdr k="total_load"    label="Total Load" />
                  <SortHdr k="stroke_count"  label="Strokes" />
                  <SortHdr k="duration_s"    label="Duration" />
                  <SortHdr k="rom_flexion"   label="ROM Flex" />
                  <SortHdr k="rom_abduction" label="ROM Abd" />
                  <SortHdr k="rom_rotation"  label="ROM Rot" />
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(r => (
                  <tr key={r.session_id}>
                    <td style={{ fontFamily: 'Space Mono', fontSize: 12 }}>{r.subject_code}</td>
                    <td className="num">{r.session_number}</td>
                    <td>
                      <span className={`badge badge-${r.arm_side === 'left' ? 'injured' : 'healthy'}`}>
                        {r.arm_side}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${r.is_injured_arm ? 'badge-injured' : 'badge-healthy'}`}>
                        {r.is_injured_arm ? 'Injured' : 'Healthy'}
                      </span>
                    </td>
                    <td>{r.started_at ? new Date(r.started_at).toLocaleDateString() : '—'}</td>
                    <td className="num" style={{ color: r.pain_score > 6 ? 'var(--injured)' : undefined }}>
                      {fmt(r.pain_score, 0)}
                    </td>
                    <td className="num">{fmt(r.total_load, 1, ' rad')}</td>
                    <td className="num">{fmt(r.stroke_count, 0)}</td>
                    <td className="num">{r.duration_s ? Math.round(r.duration_s) + 's' : '—'}</td>
                    <td className="num">{fmt(r.rom_flexion, 1, '°')}</td>
                    <td className="num">{fmt(r.rom_abduction, 1, '°')}</td>
                    <td className="num">{fmt(r.rom_rotation, 1, '°')}</td>
                    <td>
                      <Link to={`/session/${r.session_id}`} className="btn btn-secondary btn-sm">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
