import { useState, useEffect, useCallback } from 'react'
import { api } from '../api.js'

export function useVideos() {
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const data = await api.listVideos()
      setVideos(data)
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return { videos, loading, refresh }
}
