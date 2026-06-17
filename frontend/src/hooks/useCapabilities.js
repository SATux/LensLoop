import { useState, useEffect } from 'react'
import { api } from '../api.js'

let _cache = null

export function useCapabilities() {
  const [state, setState] = useState(
    _cache ? { modes: _cache.modes, model: _cache.model, loading: false, error: null }
           : { modes: [], model: '', loading: true, error: null }
  )

  useEffect(() => {
    if (_cache) return
    api.getCameraCapabilities()
      .then((data) => {
        _cache = data
        setState({ modes: data.modes, model: data.model, loading: false, error: null })
      })
      .catch((err) => {
        setState({ modes: [], model: '', loading: false, error: err.message })
      })
  }, [])

  return state
}
