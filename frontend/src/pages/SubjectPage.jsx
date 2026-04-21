// src/pages/SubjectPage.jsx
import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer
} from 'recharts'
import { subjectsApi, analysisApi, sessionsApi } from '../api/client'

export default function SubjectPage() {
  const { subjectId } = useParams()
  const [subject, setSubject]       = useState(null)
  const [comparison, setComparison] = useState(null)
  const [sessions, setSessions]     = useState([])

  useEffect(() => {
    Promise.all([
      subjectsApi.get(parseInt(subjectId)),
      analysisApi.armComparison(parseInt(subjectId)),
      sessionsApi.list(parseInt(subjectId)),
    ]).then(([s, c, sess]) => {
      setSubject(s); setComparison(c); setSessions(sess)
    })
  }, [subjectId])

  const chartData = comparison?.comparison?.map(c => ({
    session:  `S${c.session_number}`,
    injured:  c[comparison.injured_arm]?.total_load ?? null,
    healthy:  c[comparison.injured_arm === 'left' ? 'right' : 'left']?.total_load ?? null,
  })) || []

  return (
    <div>
      <Link to="/" style={{ color: 'var(--text-muted)', fontSize: 13, textDecoration: 'none' }}>← Dashboard</Link>

      {subject && (
        <div style={{ marginTop: 12, marginBottom: 28 }}>
          <h1 style={{ fontFamily: 'Space Mono', fontSize: 22, fontWeight: 700 }}>
            {subject.code}
          </h1>
          <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
            {subject.age && <span className="badge badge-active">Age {subject.age}</span>}
            <span className="badge badge-injured">{subject.injured_arm} arm injured</span>
          </div>
        </div>
      )}

      {/* Arm comparison chart */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title">Session Load — Injured vs Healthy Arm</div>
        {chartData.length === 0 ? (
          <div className="empty"><h3>No completed sessions yet</h3></div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2d42" />
              <XAxis dataKey="session" tick={{ fill: '#7a94b4', fontSize: 12 }} />
              <YAxis tick={{ fill: '#7a94b4', fontSize: 11 }} unit=" rad" width={65} />
              <Tooltip
                contentStyle={{ background: '#111720', border: '1px solid #1e2d42', borderRadius: 8, fontSize: 12 }}
                formatter={(v, n) => [v ? v.toFixed(1) + ' rad' : '—', n]}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="injured" name="Injured arm" fill="#ff6b6b" radius={[4,4,0,0]} />
              <Bar dataKey="healthy" name="Healthy arm" fill="#43e97b" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Sessions list */}
      <div className="card">
        <div className="section-header">
          <div className="card-title" style={{ marginBottom: 0 }}>All Sessions</div>
          <Link to="/session/new" className="btn btn-primary btn-sm">+ New Session</Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th><th>Arm</th><th>Type</th><th>Date</th>
                <th>Pain</th><th>Duration</th><th></th>
              </tr>
            </thead>
            <tbody>
              {sessions.map(s => (
                <tr key={s.id}>
                  <td className="num">{s.session_number}</td>
                  <td><span className={`badge badge-${s.arm_side === subject?.injured_arm ? 'injured' : 'healthy'}`}>{s.arm_side}</span></td>
                  <td><span className={`badge ${s.arm_side === subject?.injured_arm ? 'badge-injured' : 'badge-healthy'}`}>
                    {s.arm_side === subject?.injured_arm ? 'Injured' : 'Healthy'}
                  </span></td>
                  <td>{new Date(s.started_at).toLocaleDateString()}</td>
                  <td className="num">{s.pain_score ?? '—'}</td>
                  <td className="num">{s.is_active ? <span className="badge badge-active">Active</span> : '—'}</td>
                  <td><Link to={`/session/${s.id}`} className="btn btn-secondary btn-sm">View</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
          {sessions.length === 0 && (
            <div className="empty"><h3>No sessions yet</h3></div>
          )}
        </div>
      </div>
    </div>
  )
}
