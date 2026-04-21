// src/pages/AthleteDashboard.jsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { subjectsApi, analysisApi, sessionsApi } from '../api/client'

const COLORS = { injured: '#ff6b6b', healthy: '#43e97b', accent: '#00d4ff' }

function LoadChart({ data, injuredArm }) {
  // Build dual-line series: one per arm
  const sessions = data?.sessions || []
  const byNum = {}
  sessions.forEach(s => {
    if (!byNum[s.session_number]) byNum[s.session_number] = { session: s.session_number }
    const key = s.is_injured ? 'injured' : 'healthy'
    byNum[s.session_number][key] = s.cumulative_load
    byNum[s.session_number][`${key}_pain`] = s.pain_score
  })
  const chartData = Object.values(byNum).sort((a,b) => a.session - b.session)

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="injGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={COLORS.injured} stopOpacity={0.3}/>
            <stop offset="95%" stopColor={COLORS.injured} stopOpacity={0}/>
          </linearGradient>
          <linearGradient id="hlthGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={COLORS.healthy} stopOpacity={0.2}/>
            <stop offset="95%" stopColor={COLORS.healthy} stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2d42" />
        <XAxis dataKey="session" tick={{ fill: '#7a94b4', fontSize: 11 }}
               label={{ value: 'Session', fill: '#3d5473', fontSize: 11, position: 'insideBottom', offset: -2 }} />
        <YAxis tick={{ fill: '#7a94b4', fontSize: 11 }} unit=" rad" width={65} />
        <Tooltip
          contentStyle={{ background: '#111720', border: '1px solid #1e2d42', borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: '#e8f0fc', fontFamily: 'Space Mono', marginBottom: 4 }}
          formatter={(val, name) => [val ? val.toFixed(1) + ' rad' : '—', name === 'injured' ? `Injured (${injuredArm})` : 'Healthy']}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
          formatter={n => n === 'injured' ? `Injured arm (${injuredArm})` : 'Healthy arm'} />
        <Area type="monotone" dataKey="injured" stroke={COLORS.injured} fill="url(#injGrad)"
              strokeWidth={2} dot={{ fill: COLORS.injured, r: 3 }} connectNulls />
        <Area type="monotone" dataKey="healthy" stroke={COLORS.healthy} fill="url(#hlthGrad)"
              strokeWidth={2} dot={{ fill: COLORS.healthy, r: 3 }} connectNulls />
      </AreaChart>
    </ResponsiveContainer>
  )
}

function ROMChart({ data }) {
  const sessions = (data?.sessions || [])
    .filter(s => s.is_injured)
    .map(s => ({
      session: s.session_number,
      flexion: s.rom_flexion,
      abduction: s.rom_abduction,
      rotation: s.rom_rotation,
    }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={sessions} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2d42" />
        <XAxis dataKey="session" tick={{ fill: '#7a94b4', fontSize: 11 }} />
        <YAxis tick={{ fill: '#7a94b4', fontSize: 11 }} unit="°" width={48} />
        <Tooltip
          contentStyle={{ background: '#111720', border: '1px solid #1e2d42', borderRadius: 8, fontSize: 12 }}
          formatter={(v, n) => [v ? v.toFixed(1) + '°' : '—', n]}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="flexion"   stroke="#00d4ff" strokeWidth={2} dot={{ r: 3 }} connectNulls />
        <Line type="monotone" dataKey="abduction" stroke="#a78bfa" strokeWidth={2} dot={{ r: 3 }} connectNulls />
        <Line type="monotone" dataKey="rotation"  stroke="#ffd93d" strokeWidth={2} dot={{ r: 3 }} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  )
}

function PainChart({ data }) {
  const sessions = (data?.sessions || [])
    .filter(s => s.pain_score != null)
    .map(s => ({ session: s.session_number, pain: s.pain_score, load: s.session_load }))

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={sessions} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2d42" />
        <XAxis dataKey="session" tick={{ fill: '#7a94b4', fontSize: 11 }} />
        <YAxis domain={[0, 10]} tick={{ fill: '#7a94b4', fontSize: 11 }} width={32} />
        <ReferenceLine y={7} stroke="#ff6b6b" strokeDasharray="4 4" label={{ value: 'High pain', fill: '#ff6b6b', fontSize: 10 }} />
        <Tooltip
          contentStyle={{ background: '#111720', border: '1px solid #1e2d42', borderRadius: 8, fontSize: 12 }}
        />
        <Line type="monotone" dataKey="pain" stroke="#ffd93d" strokeWidth={2} dot={{ fill: '#ffd93d', r: 4 }} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  )
}

export default function AthleteDashboard() {
  const [subjects, setSubjects]     = useState([])
  const [selected, setSelected]     = useState(null)
  const [loadData, setLoadData]     = useState(null)
  const [sessions, setSessions]     = useState([])
  const [loading, setLoading]       = useState(false)

  useEffect(() => {
    subjectsApi.list().then(data => {
      setSubjects(data)
      if (data.length > 0) setSelected(data[0])
    })
  }, [])

  useEffect(() => {
    if (!selected) return
    setLoading(true)
    Promise.all([
      analysisApi.cumulativeLoad(selected.id),
      sessionsApi.list(selected.id),
    ]).then(([ld, sess]) => {
      setLoadData(ld)
      setSessions(sess.filter(s => !s.is_active))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [selected])

  const lastSession  = sessions[sessions.length - 1]
  const activeSess   = sessions.find(s => s.is_active)
  const totalSessions = sessions.length
  const avgPain = sessions.filter(s => s.pain_score != null).length > 0
    ? (sessions.filter(s => s.pain_score != null).reduce((a,s) => a + s.pain_score, 0) /
       sessions.filter(s => s.pain_score != null).length).toFixed(1)
    : '—'

  return (
    <div>
      {/* Header */}
      <div className="section-header" style={{ marginBottom: 28 }}>
        <div>
          <h1 style={{ fontFamily: 'Space Mono', fontSize: 20, fontWeight: 700, marginBottom: 4 }}>
            Athlete Dashboard
          </h1>
          <p style={{ color: 'var(--text-dim)', fontSize: 14 }}>
            Shoulder load tracking · IMU-based recovery monitoring
          </p>
        </div>
        <Link to="/session/new" className="btn btn-primary">+ New Session</Link>
      </div>

      {/* Subject selector */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title">Select Subject</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {subjects.map(s => (
            <button key={s.id}
              className={`btn ${selected?.id === s.id ? 'btn-primary' : 'btn-secondary'} btn-sm`}
              onClick={() => setSelected(s)}
            >
              {s.code}
              <span className={`badge badge-${s.injured_arm === 'left' ? 'injured' : 'healthy'}`}
                    style={{ marginLeft: 4 }}>
                {s.injured_arm} arm injured
              </span>
            </button>
          ))}
          {subjects.length === 0 && (
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              No subjects yet. <Link to="/session/new" style={{ color: 'var(--accent)' }}>Add one →</Link>
            </p>
          )}
        </div>
      </div>

      {loading && <div className="loading"><div className="spinner"/> Loading data…</div>}

      {!loading && selected && (
        <>
          {/* Stats row */}
          <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 24 }}>
            <div className="stat-card">
              <div className="stat-label">Total Sessions</div>
              <div className="stat-value">{totalSessions}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Avg Pain (VAS)</div>
              <div className="stat-value" style={{ color: avgPain > 6 ? 'var(--injured)' : 'var(--text)' }}>
                {avgPain}<span className="stat-unit">/10</span>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Injured Arm</div>
              <div className="stat-value" style={{ color: 'var(--injured)', textTransform: 'capitalize' }}>
                {selected.injured_arm}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Last Session</div>
              <div className="stat-value" style={{ fontSize: 18 }}>
                {lastSession
                  ? new Date(lastSession.started_at).toLocaleDateString()
                  : '—'}
              </div>
            </div>
          </div>

          {/* Cumulative Load Chart */}
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-title">Cumulative Load — Injured vs Healthy Arm</div>
            <LoadChart data={loadData} injuredArm={selected.injured_arm} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
            {/* ROM */}
            <div className="card">
              <div className="card-title">Range of Motion — Injured Arm (°)</div>
              <ROMChart data={loadData} />
              <div style={{ display: 'flex', gap: 16, marginTop: 12 }}>
                <span style={{ fontSize: 11, color: 'var(--accent)' }}>— Flexion</span>
                <span style={{ fontSize: 11, color: '#a78bfa' }}>— Abduction</span>
                <span style={{ fontSize: 11, color: 'var(--warn)' }}>— Rotation</span>
              </div>
            </div>

            {/* Pain */}
            <div className="card">
              <div className="card-title">Pain Score Over Sessions (VAS 0–10)</div>
              <PainChart data={loadData} />
            </div>
          </div>

          {/* Recent sessions table */}
          <div className="card">
            <div className="section-header">
              <div className="card-title" style={{ marginBottom: 0 }}>Recent Sessions</div>
              <Link to={`/subject/${selected.id}`} style={{ color: 'var(--accent)', fontSize: 13 }}>
                View all →
              </Link>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>#</th><th>Arm</th><th>Date</th><th>Pain</th>
                    <th>Total Load</th><th>Strokes</th><th>Duration</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.slice(-10).reverse().map(s => (
                    <tr key={s.id}>
                      <td className="num">{s.session_number}</td>
                      <td>
                        <span className={`badge badge-${s.arm_side === selected.injured_arm ? 'injured' : 'healthy'}`}>
                          {s.arm_side}
                        </span>
                      </td>
                      <td>{new Date(s.started_at).toLocaleDateString()}</td>
                      <td className="num" style={{ color: s.pain_score > 6 ? 'var(--injured)' : 'var(--text-dim)' }}>
                        {s.pain_score ?? '—'}
                      </td>
                      <td className="num">—</td>
                      <td className="num">—</td>
                      <td className="num">—</td>
                      <td>
                        <Link to={`/session/${s.id}`} className="btn btn-secondary btn-sm">
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {sessions.length === 0 && (
                <div className="empty">
                  <h3>No completed sessions yet</h3>
                  <p>Start a session to begin tracking load.</p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
