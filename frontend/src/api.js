const base = ''

async function request(method, path, body) {
  const opts = {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  }
  const res = await fetch(base + path, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw Object.assign(new Error(err.detail || 'Request failed'), { status: res.status })
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  getCameraInfo: () => request('GET', '/api/camera/info'),
  getCameraCapabilities: () => request('GET', '/api/camera/capabilities'),
  getStreamQuality: () => request('GET', '/api/stream/quality'),
  setStreamQuality: (width, height) => request('POST', '/api/stream/quality', { width, height }),
  getLogLevel: () => request('GET', '/api/debug/level'),
  setLogLevel: (level) => request('POST', '/api/debug/level', { level }),

  getTimelapsStatus: () => request('GET', '/api/timelapse/status'),
  startTimelapse: (body) => request('POST', '/api/timelapse/start', body),
  stopTimelapse: () => request('POST', '/api/timelapse/stop'),
  latestFrameUrl: (n) => `/api/timelapse/latest-frame?n=${n}`,

  getPreviewStatus: () => request('GET', '/api/preview/status'),
  triggerPreview: () => request('GET', '/api/preview'),

  listVideos: () => request('GET', '/api/videos'),
  getVideo: (id) => request('GET', `/api/videos/${id}`),
  deleteVideo: (id) => request('DELETE', `/api/videos/${id}`),
  videoFileUrl: (id) => `/api/videos/${id}/file`,
  thumbnailUrl: (id) => `/api/videos/${id}/thumbnail`,

  getSettings: () => request('GET', '/api/settings'),
  updateSettings: (body) => request('PATCH', '/api/settings', body),
  deleteAllData: () => request('DELETE', '/api/settings/data'),

  listSchedules: () => request('GET', '/api/schedule'),
  createSchedule: (body) => request('POST', '/api/schedule', body),
  updateSchedule: (id, body) => request('PUT', `/api/schedule/${id}`, body),
  deleteSchedule: (id) => request('DELETE', `/api/schedule/${id}`),
  enableSchedule: (id) => request('POST', `/api/schedule/${id}/enable`),
  disableSchedule: (id) => request('POST', `/api/schedule/${id}/disable`),
  runScheduleNow: (id) => request('POST', `/api/schedule/${id}/run_now`),
}
