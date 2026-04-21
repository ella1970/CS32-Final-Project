// src/pages/SessionPage.jsx
import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import { analysisApi, aiApi, imuApi } from '../api/client'

function IntraSessionChart({ sessionId }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    analysisApi.intraSession(sessionId).then(setData)
  }, [sessionId])

  if (!data || data.elapsed.length === 0) {
    return <p style={{ color: 'var(--text-muted)', fontSize: 13, padding: '20px 0' }}>
      No IMU data yet. Upload a CSV to see the load curve.
    </p>
  }

  const chartData = data.elapsed.map((t, i) => ({
    t: t.toFixed(1),
    load: data.cumulative_load[i]?.toFixed(2),
    gyro: data.gyro_mag[i]?.toFixed(3),
  }))

  return (
    <div>
      <p style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 12 }}>
        Cumulative load (rad) over session time
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="loadGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#00d4ff" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#00d4ff" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2d42" />
          <XAxis dataKey="t" tick={{ fill: '#7a94b4', fontSize: 10 }} unit="s" interval="preserveStartEnd" />
          <YAxis tick={{ fill: '#7a94b4', fontSize: 10 }} unit=" rad" width={60} />
          <Tooltip
            contentStyle={{ background: '#111720', border: '1px solid #1e2d42', borderRadius: 8, fontSize: 12 }}
            formatter={(v) => [v + ' rad', 'Cumulative Load']}
          />
          <Area type="monotone" dataKey="load" stroke="#00d4ff" fill="url(#loadGrad)" strokeWidth={2} dot={false} />
        </AreaChart>
      </ResponsiveContainer>

      <p style={{ fontSize: 12, color: 'var(--text-dim)', margin: '20px 0 12px' }}>
        Instantaneous gyro magnitude (rad/s) — stroke detection
      </p>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2d42" />
          <XAxis dataKey="t" tick={{ fill: '#7a94b4', fontSize: 10 }} unit="s" interval="preserveStartEnd" />
          <YAxis tick={{ fill: '#7a94b4', fontSize: 10 }} width={48} />
          <Tooltip
            contentStyle={{ background: '#111720', border: '1px solid #1e2d42', borderRadius: 8, fontSize: 12 }}
          />
          <Line type="monotone" dataKey="gyro" stroke="#43e97b" strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function AIRecBox({ sessionId }) {
  const [rec, setRec]         = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  async function generate() {
    setLoading(true); setError(null)
    try {
      const data = await aiApi.generate(sessionId)
      setRec(data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to generate recommendation')
    }
    setLoading(false)
  }

  useEffect(() => {
    aiApi.latest(sessionId).then(setRec).catch(() => {})
  }, [sessionId])

  return (
    <div className="rec-box">
      <div className="card-title" style={{ marginBottom: 16 }}>AI Recovery Recommendation</div>
      {!rec && !loading && (
        <div>
          <p style={{ color: 'var(--text-dim)', fontSize: 14, marginBottom: 16 }}>
            Generate a safe loading zone recommendation based on this session's data and clinical protocols.
          </p>
          <button className="btn btn-primary" onClick={generate}>
            ✦ Generate Recommendation
          </button>
        </div>
      )}
      {loading && <div className="loading"><div className="spinner"/> Consulting AI…</div>}
      {error && <p style={{ color: 'var(--injured)', fontSize: 13 }}>{error}</p>}
      {rec && (
        <div>
          <div className="rec-zone">
            <div>
              <div className="rec-zone-label">Safe Load — Next Session</div>
              <div className="rec-zone-val">
                {rec.safe_load_min?.toFixed(1)} – {rec.safe_load_max?.toFixed(1)} rad
              </div>
            </div>
            <span className={`badge badge-${
              rec.confidence === 'high' ? 'healthy' :
              rec.confidence === 'medium' ? 'warn' : 'injured'
            }`} style={{ marginLeft: 'auto' }}>
              {rec.confidence} confidence
            </span>
          </div>
          {rec.rationale && (
            <p style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 12, fontStyle: 'italic' }}>
              {rec.rationale}
            </p>
          )}
          <div className="rec-notes">{rec.recovery_notes}</div>
          {rec.red_flags && (
            <div style={{ marginTop: 12, padding: '10px 14px', background: 'rgba(255,107,107,0.08)',
                          border: '1px solid rgba(255,107,107,0.2)', borderRadius: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--injured)', textTransform: 'uppercase',
                             letterSpacing: '0.08em' }}>⚠ Red flags</span>
              <p style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 4 }}>{rec.red_flags}</p>
            </div>
          )}
          <button className="btn btn-secondary btn-sm" style={{ marginTop: 16 }} onClick={generate}>
            ↻ Regenerate
          </button>
        </div>
      )}
    </div>
  )
}

export default function SessionPage() {
  const { sessionId } = useParams()
  const [uploading, setUploading]   = useState(false)
  const [uploadMsg, setUploadMsg]   = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)

  async function handleUpload(e) {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true); setUploadMsg(null)
    try {
      const result = await imuApi.uploadCsv(parseInt(sessionId), file)
      setUploadMsg(`✓ Inserted ${result.inserted} samples`)
      setRefreshKey(k => k + 1)
    } catch (err) {
      setUploadMsg('✗ Upload failed: ' + (err.response?.data?.detail || err.message))
    }
    setUploading(false)
  }

  return (
    <div>
      <div className="section-header" style={{ marginBottom: 28 }}>
        <div>
          <Link to="/" style={{ color: 'var(--text-muted)', fontSize: 13, textDecoration: 'none' }}>
            ← Dashboard
          </Link>
          <h1 style={{ fontFamily: 'Space Mono', fontSize: 20, fontWeight: 700, marginTop: 6 }}>
            Session #{sessionId}
          </h1>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

          {/* CSV Upload */}
          <div className="card">
            <div className="card-title">Upload Sensor Data</div>
            <p style={{ color: 'var(--text-dim)', fontSize: 13, marginBottom: 16 }}>
              Upload the raw CSV exported from your IMU sensor hub.
              Columns: <code style={{ color: 'var(--accent)', fontSize: 12 }}>
                epoc (ms), elapsed (s), x-axis (g), y-axis (g), z-axis (g)
              </code>
            </p>
            <label className="btn btn-secondary" style={{ cursor: 'pointer' }}>
              {uploading ? 'Uploading…' : '↑ Choose CSV file'}
              <input type="file" accept=".csv" style={{ display: 'none' }} onChange={handleUpload} disabled={uploading} />
            </label>
            {uploadMsg && (
              <p style={{ marginTop: 10, fontSize: 13,
                          color: uploadMsg.startsWith('✓') ? 'var(--healthy)' : 'var(--injured)' }}>
                {uploadMsg}
              </p>
            )}
          </div>

          {/* Load curve */}
          <div className="card">
            <div className="card-title">Load Profile</div>
            <IntraSessionChart key={refreshKey} sessionId={parseInt(sessionId)} />
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <AIRecBox sessionId={parseInt(sessionId)} />
        </div>
      </div>
    </div>
  )
}
