"use client"

import * as React from "react"

export interface AsyncState<T> {
  data: T | undefined
  error: Error | undefined
  loading: boolean
  reload: () => void
}

const sameDeps = (a: React.DependencyList, b: React.DependencyList) =>
  a.length === b.length && a.every((v, i) => Object.is(v, b[i]))

/**
 * Run an async loader whenever `deps` change; ignores stale responses.
 * A loader returning null means "nothing to load" (loading=false, data=undefined).
 * Results are tagged with the deps "token", so loading is derived instead of set inside the effect.
 */
export function useAsync<T>(loader: () => Promise<T> | null, deps: React.DependencyList): AsyncState<T> {
  const [tick, setTick] = React.useState(0)
  // new token whenever deps/tick change (render-time state adjustment, see react.dev "you might not need an effect")
  const [gen, setGen] = React.useState<{ deps: React.DependencyList; tick: number; token: object }>(() => ({ deps, tick, token: {} }))
  if (gen.tick !== tick || !sameDeps(gen.deps, deps)) setGen({ deps, tick, token: {} })
  const token = gen.token
  const [res, setRes] = React.useState<{ token: object; data?: T; error?: Error } | null>(null)
  React.useEffect(() => {
    let alive = true
    const p: Promise<T | undefined> = loader() ?? Promise.resolve(undefined)
    p.then(
      (data) => alive && setRes({ token, data }),
      (error: Error) => alive && setRes({ token, error })
    )
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])
  const current = res?.token === token
  return {
    data: res?.data, // previous data stays visible while reloading
    error: current ? res?.error : undefined,
    loading: !current,
    reload: () => setTick((t) => t + 1),
  }
}
