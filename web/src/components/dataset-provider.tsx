"use client"

import * as React from "react"

import { api } from "@/lib/api/client"
import type { DatasetDetail, DatasetSummary } from "@/lib/api/types"

interface DatasetContextValue {
  datasets: DatasetSummary[]
  datasetId: string | null
  detail: DatasetDetail | null
  error: string | null
  loading: boolean
  select: (id: string) => void
  refresh: () => Promise<void>
}

const DatasetContext = React.createContext<DatasetContextValue | null>(null)
const KEY = "vietleap.dataset"

export function DatasetProvider({ children }: { children: React.ReactNode }) {
  const [datasets, setDatasets] = React.useState<DatasetSummary[]>([])
  const [datasetId, setDatasetId] = React.useState<string | null>(null)
  const [detail, setDetail] = React.useState<DatasetDetail | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [loading, setLoading] = React.useState(true)

  // setState only runs in promise callbacks, never synchronously inside an effect
  const refresh = React.useCallback(
    () =>
      api.datasets().then(
        (list) => {
          setDatasets(list)
          setError(null)
          setDatasetId((cur) => {
            const fromUrl = new URLSearchParams(window.location.search).get("ds")
            const saved = window.localStorage.getItem(KEY)
            const wanted = [cur, fromUrl, saved].find((x) => x && list.some((d) => d.id === x))
            return wanted ?? list[0]?.id ?? null
          })
          setLoading(false)
        },
        (e: Error) => {
          setError(e.message)
          setLoading(false)
        }
      ),
    []
  )

  React.useEffect(() => {
    void refresh()
  }, [refresh])

  React.useEffect(() => {
    if (!datasetId) return
    window.localStorage.setItem(KEY, datasetId)
    let alive = true
    api.dataset(datasetId).then(
      (d) => alive && setDetail(d),
      (e: Error) => alive && setError(e.message)
    )
    return () => {
      alive = false
    }
  }, [datasetId])

  const value = React.useMemo(
    () => ({ datasets, datasetId, detail, error, loading, select: setDatasetId, refresh }),
    [datasets, datasetId, detail, error, loading, refresh]
  )
  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>
}

export function useDataset() {
  const ctx = React.useContext(DatasetContext)
  if (!ctx) throw new Error("useDataset must be used inside <DatasetProvider>")
  return ctx
}
