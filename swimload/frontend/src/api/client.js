// src/api/client.js
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const subjectsApi = {
  list:   ()      => api.get('/subjects').then(r => r.data),
  create: (data)  => api.post('/subjects', data).then(r => r.data),
  get:    (id)    => api.get(`/subjects/${id}`).then(r => r.data),
}

export const sessionsApi = {
  start:     (data)        => api.post('/sessions/start', data).then(r => r.data),
  end:       (id, data)    => api.post(`/sessions/${id}/end`, data).then(r => r.data),
  list:      (subjectId)   => api.get(`/sessions/subject/${subjectId}`).then(r => r.data),
  table:     ()            => api.get('/sessions/table').then(r => r.data),
}

export const imuApi = {
  uploadCsv: (sessionId, file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/imu/${sessionId}/upload_csv`, form,
      { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data)
  },
  batch:     (sessionId, samples) =>
    api.post(`/imu/${sessionId}/batch`, samples).then(r => r.data),
}

export const analysisApi = {
  cumulativeLoad: (subjectId) =>
    api.get(`/analysis/subject/${subjectId}/cumulative_load`).then(r => r.data),
  armComparison:  (subjectId) =>
    api.get(`/analysis/subject/${subjectId}/arm_comparison`).then(r => r.data),
  intraSession:   (sessionId) =>
    api.get(`/analysis/session/${sessionId}/intra_session`).then(r => r.data),
}

export const aiApi = {
  generate: (sessionId) =>
    api.post(`/recommendations/${sessionId}/generate`).then(r => r.data),
  latest:   (sessionId) =>
    api.get(`/recommendations/${sessionId}/latest`).then(r => r.data),
}
