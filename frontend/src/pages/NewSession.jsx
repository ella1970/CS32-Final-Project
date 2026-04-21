// src/pages/NewSession.jsx
import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { subjectsApi, sessionsApi } from '../api/client'

function Timer({ active }) {
  const [elapsed, setElapsed] = useState(0)
  const ref = useRef(null)

  useEffect(() => {
    if (active) {
      ref.current = setInterval(() => setElapsed(e => e + 1), 1000)
    } else {
      clearInterval(ref.current)
    }
    return () => clearInterval(ref.current)
  }, [active])

  useEffect(() => { if (!active) setElapsed(0) }, [active])

  const h = String(Math.floor(elapsed / 3600)).padStart(2, '0')
  const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0')
  const s = String(elapsed % 60).padStart(2, '0')
  return <div className="session-timer">{h}:{m}:{s}</div>
}

export default function NewSession() {
  const navigate = useNavigate()
  const [step, setStep]           = useState('setup')   // setup | active | post
  const [subjects, setSubjects]   = useState([])
  const [subjectId, setSubjectId] = useState('')
  const [armSide, setArmSide]     = useState('left')
  const [newCode, setNewCode]     = useState('')
  const [newAge, setNewAge]       = useState('')
  const [injuredArm, setInjuredArm] = useState('left')
  const [creating, setCreating]   = useState(false)
  const [session, setSession]     = useState(null)
  const [painScore, setPainScore] = useState(null)
  const [notes, setNotes]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [showNewSubj, setShowNewSubj] = useState(false)

  useEffect(() => {
    subjectsApi.list().then(setSubjects)
  }, [])

  async function handleCreateSubject() {
    if (!newCode) return
    setCreating(true)
    const s = await subjectsApi.create({ code: newCode, age: parseInt(newAge) || null, injured_arm: injuredArm })
    setSubjects(prev => [...prev, s])
    setSubjectId(String(s.id))
    setShowNewSubj(false)
    setCreating(false)
  }

  async function handleStart() {
    if (!subjectId) return
    setLoading(true)
    const sess = await sessionsApi.start({ subject_id: parseInt(subjectId), arm_side: armSide })
    setSession(sess)
    setStep('active')
    setLoading(false)
  }

  async function handleStop() {
    setStep('post')
  }

  async function handleFinish() {
    if (!session) return
    setLoading(true)
    await sessionsApi.end(session.id, { pain_score: painScore, notes })
    navigate(`/session/${session.id}`)
  }

  const selectedSubject = subjects.find(s => String(s.id) === subjectId)

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontFamily: 'Space Mono', fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
        {step === 'setup' ? 'New Session' : step === 'active' ? 'Session Active' : 'Post-Session'}
      </h1>
      <p style={{ color: 'var(--text-dim)', fontSize: 14, marginBottom: 32 }}>
        {step === 'setup' ? 'Configure your session before recording' :
         step === 'active' ? 'Session is recording. Stop when done swimming.' :
         'Rate your pain and save session data.'}
      </p>

      {/* ── SETUP ── */}
      {step === 'setup' && (
        <div className="card">
          <div className="card-title">Session Setup</div>

          <div className="form-group">
            <label className="form-label">Subject</label>
            <select className="form-select" value={subjectId}
                    onChange={e => setSubjectId(e.target.value)}>
              <option value="">— Select subject —</option>
              {subjects.map(s => (
                <option key={s.id} value={s.id}>{s.code} ({s.injured_arm} arm injured)</option>
              ))}
            </select>
            <button className="btn btn-secondary btn-sm" style={{ alignSelf: 'flex-start', marginTop: 8 }}
                    onClick={() => setShowNewSubj(v => !v)}>
              {showNewSubj ? 'Cancel' : '+ New Subject'}
            </button>
          </div>

          {showNewSubj && (
            <div style={{ background: 'var(--bg3)', borderRadius: 8, padding: 16, marginBottom: 20 }}>
              <div className="card-title">Create Subject</div>
              <div className="form-group">
                <label className="form-label">Subject Code</label>
                <input className="form-input" placeholder="e.g. SUB_007"
                       value={newCode} onChange={e => setNewCode(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Age (optional)</label>
                <input className="form-input" type="number" placeholder="22"
                       value={newAge} onChange={e => setNewAge(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Injured Arm</label>
                <div className="arm-toggle">
                  <button className={`arm-btn left ${injuredArm === 'left' ? 'active' : ''}`}
                          onClick={() => setInjuredArm('left')}>Left</button>
                  <button className={`arm-btn right ${injuredArm === 'right' ? 'active' : ''}`}
                          onClick={() => setInjuredArm('right')}>Right</button>
                </div>
              </div>
              <button className="btn btn-primary btn-sm" onClick={handleCreateSubject} disabled={creating}>
                {creating ? 'Creating…' : 'Create Subject'}
              </button>
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Recording Arm</label>
            <div className="arm-toggle">
              <button className={`arm-btn left ${armSide === 'left' ? 'active' : ''}`}
                      onClick={() => setArmSide('left')}>Left</button>
              <button className={`arm-btn right ${armSide === 'right' ? 'active' : ''}`}
                      onClick={() => setArmSide('right')}>Right</button>
            </div>
            {selectedSubject && (
              <p style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 6 }}>
                {armSide === selectedSubject.injured_arm
                  ? '⚠ This is the INJURED arm'
                  : '✓ This is the healthy arm'}
              </p>
            )}
          </div>

          <button className="btn btn-primary btn-lg" style={{ width: '100%' }}
                  onClick={handleStart} disabled={!subjectId || loading}>
            {loading ? 'Starting…' : '▶  Start Session'}
          </button>
        </div>
      )}

      {/* ── ACTIVE ── */}
      {step === 'active' && session && (
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ marginBottom: 8 }}>
            <span className="badge badge-active">● Recording</span>
          </div>
          <div className="card-title" style={{ textAlign: 'center' }}>
            Session #{session.session_number} — {session.arm_side} arm
          </div>
          <Timer active={true} />
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 32 }}>
            Sensor is streaming. Press stop when the session is complete.
          </p>
          <button className="btn btn-danger btn-lg" style={{ width: '100%' }}
                  onClick={handleStop}>
            ■ Stop Session
          </button>
        </div>
      )}

      {/* ── POST ── */}
      {step === 'post' && (
        <div className="card">
          <div className="card-title">Post-Session Report</div>
          <div className="form-group">
            <label className="form-label">Pain Scale (VAS 0 = no pain, 10 = worst)</label>
            <div className="pain-scale">
              {[0,1,2,3,4,5,6,7,8,9,10].map(n => (
                <button key={n}
                  className={`pain-btn ${painScore === n ? 'selected' : ''}`}
                  onClick={() => setPainScore(n)}>
                  {n}
                </button>
              ))}
            </div>
            {painScore !== null && (
              <p style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 8 }}>
                {painScore === 0 ? 'No pain' :
                 painScore <= 3 ? 'Mild pain' :
                 painScore <= 6 ? 'Moderate pain' :
                 'Severe pain — will flag for AI review'}
              </p>
            )}
          </div>

          <div className="form-group">
            <label className="form-label">Notes (optional)</label>
            <textarea className="form-input" rows={3} placeholder="Any observations about technique, fatigue, etc."
                      value={notes} onChange={e => setNotes(e.target.value)}
                      style={{ resize: 'vertical' }} />
          </div>

          <button className="btn btn-primary btn-lg" style={{ width: '100%' }}
                  onClick={handleFinish} disabled={loading}>
            {loading ? 'Saving…' : 'Save Session & View Results'}
          </button>
        </div>
      )}
    </div>
  )
}
