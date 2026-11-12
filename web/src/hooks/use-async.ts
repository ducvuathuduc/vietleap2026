"use client"

import * as React from "react"

export interface AsyncState<T> {
  data: T | undefined
  error: Error | undefined
  loading: boolean
  reload: () => void
}

/** Run an async loader whenever `deps` change; ignores stale responses. */
export function useAsync<T>(loader: () => Promise<T> | null, deps: React.DependencyList): AsyncState<T> {
  const [state, setState] = React.useState<{ data?: T; error?: Error; loading: boolean }>({ loading: true })
  const [tick, setTick] = React.useState(0)
  React.useEffect(() => {
    let alive = true
    const p = loader()
    if (!p) {
      setState({ loading: false })
      return
    }
    setState((s) => ({ data: s.data, loading: true }))
    p.then(
      (data) => alive && setState({ data, loading: false }),
      (error: Error) => alive && setState({ error, loading: false })
    )
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])
  return { ...state, reload: () => setTick((t) => t + 1) }
}
