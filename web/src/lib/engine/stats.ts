// Pure TypeScript statistical & ML helpers (no Python/SciPy required).

export function sortedNums(xs: number[]): number[] {
  return [...xs].filter((x) => Number.isFinite(x)).sort((a, b) => a - b)
}

export function quantile(sorted: number[], q: number): number {
  if (sorted.length === 0) return 0
  const pos = (sorted.length - 1) * q
  const lo = Math.floor(pos)
  const hi = Math.ceil(pos)
  if (lo === hi) return sorted[lo]
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo)
}

export function median(xs: number[]): number {
  const s = sortedNums(xs)
  return s.length ? quantile(s, 0.5) : 0
}

export function mean(xs: number[]): number {
  const valid = xs.filter(Number.isFinite)
  return valid.length ? valid.reduce((a, b) => a + b, 0) / valid.length : 0
}

export function std(xs: number[]): number {
  const valid = xs.filter(Number.isFinite)
  if (valid.length < 2) return 0
  const m = mean(valid)
  const v = valid.reduce((a, x) => a + (x - m) ** 2, 0) / (valid.length - 1)
  return Math.sqrt(v)
}

export function skewness(xs: number[]): number {
  const valid = xs.filter(Number.isFinite)
  if (valid.length < 3) return 0
  const m = mean(valid)
  const sd = std(valid)
  if (sd === 0) return 0
  const n = valid.length
  const m3 = valid.reduce((a, x) => a + ((x - m) / sd) ** 3, 0) / n
  return m3
}

export function iqr3Bounds(xs: number[]): { lo: number; hi: number; count: number } {
  const s = sortedNums(xs)
  if (s.length < 4) return { lo: -Infinity, hi: Infinity, count: 0 }
  const q1 = quantile(s, 0.25)
  const q3 = quantile(s, 0.75)
  const iqr = q3 - q1
  if (iqr === 0) return { lo: -Infinity, hi: Infinity, count: 0 }
  const lo = q1 - 3 * iqr
  const hi = q3 + 3 * iqr
  const count = s.filter((x) => x < lo || x > hi).length
  return { lo, hi, count }
}

export function histogram(xs: number[], bins = 20): { counts: number[]; edges: number[] } | undefined {
  const s = sortedNums(xs)
  if (s.length < 5) return undefined
  const lo = quantile(s, 0.01)
  const hi = quantile(s, 0.99)
  if (hi <= lo) return undefined
  const step = (hi - lo) / bins
  const edges = Array.from({ length: bins + 1 }, (_, i) => Number((lo + i * step).toPrecision(5)))
  const counts = new Array<number>(bins).fill(0)
  for (const x of s) {
    if (x < lo || x > hi) continue
    const idx = Math.min(bins - 1, Math.floor((x - lo) / step))
    counts[idx]++
  }
  return { counts, edges }
}

/** Regularized incomplete gamma Q(a, x) / erf approx for p-values. */
function erf(x: number): number {
  const sign = x >= 0 ? 1 : -1
  const a = Math.abs(x)
  const t = 1 / (1 + 0.3275911 * a)
  const y = 1 - (((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t) * Math.exp(-a * a)
  return sign * y
}

export function normalTwoTailP(z: number): number {
  return Math.max(1e-12, Math.min(1, 1 - erf(Math.abs(z) / Math.SQRT2)))
}

function logGamma(z: number): number {
  const p = [
    676.5203681218851, -1259.1392167224028, 771.32342877765313,
    -176.61502916214059, 12.507343278686905, -0.13857109526572012,
    9.9843695780195716e-6, 1.5056327351493116e-7,
  ]
  if (z < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * z)) - logGamma(1 - z)
  const t = z - 1 + 7.5
  let x = 0.99999999999980993
  for (let i = 0; i < p.length; i++) x += p[i] / (z + i)
  return 0.5 * Math.log(2 * Math.PI) + (z - 0.5) * Math.log(t) - t + Math.log(x)
}

/** Upper-tail chi-square p-value Q(df/2, x/2) via series/continued fraction. */
export function chi2P(x: number, df: number): number {
  if (x <= 0 || df <= 0) return 1
  const a = df / 2
  const z = x / 2
  if (z < a + 1) {
    let ap = a
    let sum = 1 / a
    let del = sum
    for (let n = 1; n <= 200; n++) {
      ap += 1
      del *= z / ap
      sum += del
      if (Math.abs(del) < Math.abs(sum) * 1e-10) break
    }
    const p = sum * Math.exp(-z + a * Math.log(z) - logGamma(a))
    return Math.max(1e-12, Math.min(1, 1 - p))
  }
  let b = z + 1 - a
  let c = 1 / 1e-30
  let d = 1 / b
  let h = d
  for (let i = 1; i <= 200; i++) {
    const an = -i * (i - a)
    b += 2
    d = an * d + b
    if (Math.abs(d) < 1e-30) d = 1e-30
    c = b + an / c
    if (Math.abs(c) < 1e-30) c = 1e-30
    d = 1 / d
    const del = d * c
    h *= del
    if (Math.abs(del - 1) < 1e-10) break
  }
  const q = Math.exp(-z + a * Math.log(z) - logGamma(a)) * h
  return Math.max(1e-12, Math.min(1, q))
}

function ranks(xs: number[]): number[] {
  const indexed = xs.map((v, i) => ({ v, i })).sort((a, b) => a.v - b.v)
  const out = new Array<number>(xs.length)
  let i = 0
  while (i < indexed.length) {
    let j = i
    while (j + 1 < indexed.length && indexed[j + 1].v === indexed[i].v) j++
    const avgRank = (i + j) / 2 + 1
    for (let k = i; k <= j; k++) out[indexed[k].i] = avgRank
    i = j + 1
  }
  return out
}

export function pearson(xs: number[], ys: number[]): { r: number; p: number; n: number } {
  const pairs: [number, number][] = []
  for (let i = 0; i < Math.min(xs.length, ys.length); i++) {
    if (Number.isFinite(xs[i]) && Number.isFinite(ys[i])) pairs.push([xs[i], ys[i]])
  }
  const n = pairs.length
  if (n < 4) return { r: 0, p: 1, n }
  const mx = mean(pairs.map((p) => p[0]))
  const my = mean(pairs.map((p) => p[1]))
  let num = 0
  let dx2 = 0
  let dy2 = 0
  for (const [x, y] of pairs) {
    const dx = x - mx
    const dy = y - my
    num += dx * dy
    dx2 += dx * dx
    dy2 += dy * dy
  }
  const denom = Math.sqrt(dx2 * dy2)
  const r = denom > 0 ? Math.max(-1, Math.min(1, num / denom)) : 0
  if (Math.abs(r) >= 0.999999) return { r, p: 1e-12, n }
  const z = 0.5 * Math.log((1 + r) / (1 - r)) * Math.sqrt(Math.max(1, n - 3))
  return { r, p: normalTwoTailP(z), n }
}

export function spearman(xs: number[], ys: number[]): { rho: number; p: number; n: number } {
  const pairs: [number, number][] = []
  for (let i = 0; i < Math.min(xs.length, ys.length); i++) {
    if (Number.isFinite(xs[i]) && Number.isFinite(ys[i])) pairs.push([xs[i], ys[i]])
  }
  if (pairs.length < 4) return { rho: 0, p: 1, n: pairs.length }
  const rx = ranks(pairs.map((p) => p[0]))
  const ry = ranks(pairs.map((p) => p[1]))
  const res = pearson(rx, ry)
  return { rho: res.r, p: res.p, n: res.n }
}

export function kruskalWallis(groups: number[][]): { H: number; p: number; epsilon2: number } | null {
  const valid = groups.filter((g) => g.length >= 2)
  if (valid.length < 2) return null
  const all = valid.flat()
  const N = all.length
  if (N < 5) return null
  const r = ranks(all)
  let offset = 0
  let sumR2 = 0
  for (const g of valid) {
    const gr = r.slice(offset, offset + g.length)
    offset += g.length
    const s = gr.reduce((a, b) => a + b, 0)
    sumR2 += (s * s) / g.length
  }
  const H = Math.max(0, (12 / (N * (N + 1))) * sumR2 - 3 * (N + 1))
  const k = valid.length
  const p = chi2P(H, k - 1)
  const epsilon2 = N > k ? Math.max(0, (H - k + 1) / (N - k)) : 0
  return { H: Number(H.toFixed(2)), p, epsilon2: Number(epsilon2.toFixed(3)) }
}

export function mannWhitney(a: number[], b: number[]): { p: number; rank_biserial: number } {
  if (a.length < 2 || b.length < 2) return { p: 1, rank_biserial: 0 }
  const combined = [...a, ...b]
  const r = ranks(combined)
  const r1 = r.slice(0, a.length).reduce((s, v) => s + v, 0)
  const n1 = a.length
  const n2 = b.length
  const u1 = r1 - (n1 * (n1 + 1)) / 2
  const mu = (n1 * n2) / 2
  const sigma = Math.sqrt((n1 * n2 * (n1 + n2 + 1)) / 12)
  const z = sigma > 0 ? (u1 - mu) / sigma : 0
  const rb = (2 * u1) / (n1 * n2) - 1
  return { p: normalTwoTailP(z), rank_biserial: Number(rb.toFixed(3)) }
}

/** Solve (A)x = b via Gaussian elimination with partial pivoting. */
function solveLinear(A: number[][], b: number[]): number[] | null {
  const n = b.length
  const M = A.map((row, i) => [...row, b[i]])
  for (let col = 0; col < n; col++) {
    let pivot = col
    for (let r = col + 1; r < n; r++) {
      if (Math.abs(M[r][col]) > Math.abs(M[pivot][col])) pivot = r
    }
    if (Math.abs(M[pivot][col]) < 1e-12) return null
    ;[M[col], M[pivot]] = [M[pivot], M[col]]
    const div = M[col][col]
    for (let j = col; j <= n; j++) M[col][j] /= div
    for (let r = 0; r < n; r++) {
      if (r === col) continue
      const f = M[r][col]
      for (let j = col; j <= n; j++) M[r][j] -= f * M[col][j]
    }
  }
  return M.map((row) => row[n])
}

function fitRidge(X: number[][], y: number[], alpha = 1.0): number[] {
  const n = X.length
  const p = X[0]?.length ?? 0
  if (n === 0 || p === 0) return []
  const XtX: number[][] = Array.from({ length: p }, () => new Array<number>(p).fill(0))
  const Xty = new Array<number>(p).fill(0)
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < p; j++) {
      Xty[j] += X[i][j] * y[i]
      for (let k = j; k < p; k++) {
        XtX[j][k] += X[i][j] * X[i][k]
      }
    }
  }
  for (let j = 0; j < p; j++) {
    XtX[j][j] += alpha
    for (let k = 0; k < j; k++) XtX[j][k] = XtX[k][j]
  }
  return solveLinear(XtX, Xty) ?? new Array<number>(p).fill(0)
}

function predictLinear(X: number[][], w: number[]): number[] {
  return X.map((row) => row.reduce((s, x, j) => s + x * w[j], 0))
}

function r2Score(yTrue: number[], yPred: number[]): number {
  const m = mean(yTrue)
  const ssTot = yTrue.reduce((s, y) => s + (y - m) ** 2, 0)
  if (ssTot <= 1e-12) return 0
  const ssRes = yTrue.reduce((s, y, i) => s + (y - yPred[i]) ** 2, 0)
  return 1 - ssRes / ssTot
}

/** Deterministic PRNG for repeatable bootstrap & k-means. */
function mulberry32(seed: number) {
  let t = seed >>> 0
  return () => {
    t += 0x6d2b79f5
    let r = Math.imul(t ^ (t >>> 15), 1 | t)
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r)
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296
  }
}

export interface DriverModelInternal {
  features: string[]
  means: number[]
  sds: number[]
  mins: number[]
  maxs: number[]
  corrs: number[][]
  yMean: number
  ySd: number
  logTarget: boolean
  bootWeights: number[][] // B x p standardized weights on y (or log(y))
  weights: number[]
}

export function buildDrivers(
  rows: Record<string, unknown>[],
  targetCol: string,
  featureCols: string[]
): {
  model: DriverModelInternal
  n: number
  leakage_excluded: string[]
  cv_r2: { ridge_mean: number; ridge_std: number; gb_mean: number; gb_std: number }
  importance: { feature: string; importance: number; std: number }[]
  coefficients: { feature: string; coef_std: number; ci90: [number, number]; direction: "+" | "-"; stable: boolean }[]
} | null {
  if (featureCols.length === 0 || rows.length < 10) return null

  const cleanCols = featureCols.filter((c) => c !== targetCol)
  const leakage_excluded: string[] = []
  const kept: string[] = []

  // Extract raw target
  const yAll = rows.map((r) => (typeof r[targetCol] === "number" ? (r[targetCol] as number) : NaN))
  for (const c of cleanCols) {
    const xAll = rows.map((r) => (typeof r[c] === "number" ? (r[c] as number) : NaN))
    const validCount = xAll.filter(Number.isFinite).length
    if (validCount < Math.max(8, rows.length * 0.25)) continue
    const sd = std(xAll)
    if (sd === 0) continue
    const corr = pearson(xAll, yAll)
    if (Math.abs(corr.r) > 0.985 && corr.n > 10) {
      leakage_excluded.push(c)
    } else {
      kept.push(c)
    }
  }
  const features = kept.slice(0, 12)
  if (features.length === 0) return null

  // Impute missing feature cells with column median on valid target rows
  const validIdx: number[] = []
  rows.forEach((r, i) => {
    if (typeof r[targetCol] === "number" && Number.isFinite(r[targetCol] as number)) validIdx.push(i)
  })
  if (validIdx.length < 10) return null

  const colMedians = features.map((f) => median(validIdx.map((i) => rows[i][f]).filter((v): v is number => typeof v === "number" && Number.isFinite(v))))
  const rawY = validIdx.map((i) => rows[i][targetCol] as number)
  const positiveAll = rawY.every((y) => y > 0)
  const logTarget = positiveAll && skewness(rawY) > 1.2
  const yVals = logTarget ? rawY.map((y) => Math.log(y)) : rawY
  const yMean = mean(yVals)
  const ySd = std(yVals) || 1
  const yNorm = yVals.map((y) => (y - yMean) / ySd)

  const Xraw = validIdx.map((i) =>
    features.map((f, j) => {
      const v = rows[i][f]
      return typeof v === "number" && Number.isFinite(v) ? v : colMedians[j]
    })
  )
  const means = features.map((_, j) => mean(Xraw.map((r) => r[j])))
  const sds = features.map((_, j) => std(Xraw.map((r) => r[j])) || 1)
  const mins = features.map((_, j) => Math.min(...Xraw.map((r) => r[j])))
  const maxs = features.map((_, j) => Math.max(...Xraw.map((r) => r[j])))
  const corrs = features.map((_, i) =>
    features.map((__, j) => (i === j ? 1 : pearson(Xraw.map((r) => r[i]), Xraw.map((r) => r[j])).r))
  )
  const X = Xraw.map((r) => r.map((v, j) => (v - means[j]) / sds[j]))

  // 5-fold CV
  const kFolds = Math.min(5, Math.floor(X.length / 3))
  const ridgeFolds: number[] = []
  const gbFolds: number[] = []
  for (let fold = 0; fold < kFolds; fold++) {
    const trX: number[][] = []
    const trY: number[] = []
    const teX: number[][] = []
    const teY: number[] = []
    for (let i = 0; i < X.length; i++) {
      if (i % kFolds === fold) {
        teX.push(X[i])
        teY.push(yNorm[i])
      } else {
        trX.push(X[i])
        trY.push(yNorm[i])
      }
    }
    const w = fitRidge(trX, trY, 2.0)
    const pred = predictLinear(teX, w)
    const r2 = Math.max(-0.5, Math.min(0.99, r2Score(teY, pred)))
    ridgeFolds.push(r2)
    // Simple 2-stage residual nonlinear adjustment proxy for GB CV
    const resTrain = trY.map((y, idx) => y - trX[idx].reduce((s, x, j) => s + x * w[j], 0))
    let bestFeat = 0
    let bestCorr = 0
    for (let j = 0; j < features.length; j++) {
      const c = Math.abs(spearman(trX.map((r) => r[j]), resTrain).rho)
      if (c > bestCorr) {
        bestCorr = c
        bestFeat = j
      }
    }
    const splitVal = median(trX.map((r) => r[bestFeat]))
    const loMean = mean(resTrain.filter((_, idx) => trX[idx][bestFeat] <= splitVal))
    const hiMean = mean(resTrain.filter((_, idx) => trX[idx][bestFeat] > splitVal))
    const predGb = pred.map((p, idx) => p + 0.35 * (teX[idx][bestFeat] <= splitVal ? loMean : hiMean))
    gbFolds.push(Math.max(-0.5, Math.min(0.99, r2Score(teY, predGb))))
  }

  // Full fit + 80 bootstrap resamples for 90% CI
  const weights = fitRidge(X, yNorm, 2.0)
  const rand = mulberry32(42)
  const bootWeights: number[][] = []
  const B = 80
  for (let b = 0; b < B; b++) {
    const bX: number[][] = []
    const bY: number[] = []
    for (let i = 0; i < X.length; i++) {
      const idx = Math.floor(rand() * X.length)
      bX.push(X[idx])
      bY.push(yNorm[idx])
    }
    bootWeights.push(fitRidge(bX, bY, 2.0))
  }

  // Permutation importance on held-out 25%
  const splitAt = Math.max(4, Math.floor(X.length * 0.75))
  const trainX = X.slice(0, splitAt)
  const trainY = yNorm.slice(0, splitAt)
  const testX = X.slice(splitAt)
  const testY = yNorm.slice(splitAt)
  const wHeld = fitRidge(trainX, trainY, 2.0)
  const baseR2 = r2Score(testY, predictLinear(testX, wHeld))

  const importance = features.map((f, j) => {
    const drops: number[] = []
    for (let rep = 0; rep < 5; rep++) {
      const permX = testX.map((r) => [...r])
      const col = permX.map((r) => r[j])
      for (let i = col.length - 1; i > 0; i--) {
        const k = Math.floor(rand() * (i + 1))
        ;[col[i], col[k]] = [col[k], col[i]]
      }
      permX.forEach((r, idx) => { r[j] = col[idx] })
      drops.push(Math.max(0, baseR2 - r2Score(testY, predictLinear(permX, wHeld))))
    }
    return {
      feature: f,
      importance: Number(mean(drops).toFixed(4)),
      std: Number(std(drops).toFixed(4)),
    }
  }).sort((a, b) => b.importance - a.importance)

  const coefficients = features.map((f, j) => {
    const bw = sortedNums(bootWeights.map((w) => w[j]))
    const lo = quantile(bw, 0.05)
    const hi = quantile(bw, 0.95)
    const coef = weights[j]
    return {
      feature: f,
      coef_std: Number(coef.toFixed(4)),
      ci90: [Number(lo.toFixed(4)), Number(hi.toFixed(4))] as [number, number],
      direction: (coef >= 0 ? "+" : "-") as "+" | "-",
      stable: (lo > 0 && hi > 0) || (lo < 0 && hi < 0),
    }
  }).sort((a, b) => Math.abs(b.coef_std) - Math.abs(a.coef_std))

  return {
    model: { features, means, sds, mins, maxs, corrs, yMean, ySd, logTarget, bootWeights, weights },
    n: validIdx.length,
    leakage_excluded,
    cv_r2: {
      ridge_mean: Number(mean(ridgeFolds).toFixed(3)),
      ridge_std: Number(std(ridgeFolds).toFixed(3)),
      gb_mean: Number(mean(gbFolds).toFixed(3)),
      gb_std: Number(std(gbFolds).toFixed(3)),
    },
    importance,
    coefficients,
  }
}

export function predictWhatIf(
  rows: Record<string, unknown>[],
  targetCol: string,
  model: DriverModelInternal,
  feature: string,
  pctChange: number
) {
  const j = model.features.indexOf(feature)
  if (j < 0) return null
  const validRows = rows.filter((r) => typeof r[targetCol] === "number" && Number.isFinite(r[targetCol] as number))
  const baselineMean = mean(validRows.map((r) => r[targetCol] as number))
  if (!Number.isFinite(baselineMean) || baselineMean === 0) return null

  const featMean = model.means[j]
  const deltaX = featMean * (pctChange / 100)
  const deltaZ = deltaX / (model.sds[j] || 1)

  const pctOutcomes = model.bootWeights.map((w) => {
    const deltaYNorm = w[j] * deltaZ
    if (model.logTarget) {
      const ratio = Math.exp(deltaYNorm * model.ySd) - 1
      return ratio * 100
    }
    const deltaAbs = deltaYNorm * model.ySd
    return (deltaAbs / Math.abs(baselineMean)) * 100
  })

  const pointNorm = model.weights[j] * deltaZ
  const pointPct = model.logTarget
    ? (Math.exp(pointNorm * model.ySd) - 1) * 100
    : ((pointNorm * model.ySd) / Math.abs(baselineMean)) * 100

  const sortedPcts = sortedNums(pctOutcomes)
  const ciLo = quantile(sortedPcts, 0.05)
  const ciHi = quantile(sortedPcts, 0.95)
  const absChange = (baselineMean * pointPct) / 100

  return {
    feature,
    pct_change: pctChange,
    target: targetCol,
    target_change_pct: Number(pointPct.toFixed(2)),
    ci90_pct: [Number(ciLo.toFixed(2)), Number(ciHi.toFixed(2))] as [number, number],
    target_change_abs: Number(absChange.toFixed(2)),
    baseline_target_mean: Number(baselineMean.toFixed(2)),
    interpretation: `Nếu ${feature} thay đổi ${pctChange > 0 ? "+" : ""}${pctChange}%, ${targetCol} dự kiến thay đổi ${pointPct >= 0 ? "+" : ""}${pointPct.toFixed(2)}% (khoảng tin cậy 90%: ${ciLo.toFixed(2)}% đến ${ciHi.toFixed(2)}%, tương quan tuyến tính chuẩn hoá).`,
  }
}

export function predictWhatIfMulti(
  rows: Record<string, unknown>[],
  targetCol: string,
  model: DriverModelInternal,
  changes: { feature: string; pct_change: number }[]
) {
  if (!Array.isArray(changes) || changes.length < 1 || changes.length > 5) {
    throw new Error("Kịch bản cần 1–5 biến thay đổi.")
  }
  const seen = new Set<string>()
  for (const ch of changes) {
    if (seen.has(ch.feature)) throw new Error(`Biến '${ch.feature}' bị trùng lặp trong kịch bản.`)
    seen.add(ch.feature)
    if (!Number.isFinite(ch.pct_change) || ch.pct_change < -30 || ch.pct_change > 30) {
      throw new Error(`pct_change cho '${ch.feature}' phải nằm trong [-30, 30].`)
    }
    if (!model.features.includes(ch.feature)) {
      throw new Error(`Biến '${ch.feature}' không có trong mô hình drivers.`)
    }
  }

  const validRows = rows.filter((r) => typeof r[targetCol] === "number" && Number.isFinite(r[targetCol] as number))
  const baselineMean = mean(validRows.map((r) => r[targetCol] as number))
  if (!Number.isFinite(baselineMean) || baselineMean === 0) return null

  const deltaZs: number[] = []
  const rangeWarnings: string[] = []
  const movedIndices: number[] = []
  const contributions: { feature: string; pct_change: number; target_change_pct: number | null; ci90_pct: [number | null, number | null] }[] = []

  for (const ch of changes) {
    const j = model.features.indexOf(ch.feature)
    const featMean = model.means[j]
    const deltaX = featMean * (ch.pct_change / 100)
    const deltaZ = deltaX / (model.sds[j] || 1)
    deltaZs.push(deltaZ)

    const single = predictWhatIf(rows, targetCol, model, ch.feature, ch.pct_change)
    contributions.push({
      feature: ch.feature,
      pct_change: ch.pct_change,
      target_change_pct: ch.pct_change === 0 ? 0 : (single?.target_change_pct ?? null),
      ci90_pct: ch.pct_change === 0 ? [0, 0] : (single?.ci90_pct ?? [null, null]),
    })

    if (ch.pct_change !== 0) {
      movedIndices.push(j)
      const implied = featMean + deltaX
      const loB = model.mins[j]
      const hiB = model.maxs[j]
      if (Number.isFinite(loB) && Number.isFinite(hiB) && (implied < loB || implied > hiB)) {
        rangeWarnings.push(
          `${ch.feature} (${implied.toFixed(2)}) vượt ngoài phạm vi dữ liệu quan sát [${loB.toFixed(2)}, ${hiB.toFixed(2)}] (ngoài phạm vi dữ liệu).`
        )
      }
    }
  }

  const collinearityWarnings: string[] = []
  for (let a = 0; a < movedIndices.length; a++) {
    for (let b = a + 1; b < movedIndices.length; b++) {
      const i = movedIndices[a]
      const j = movedIndices[b]
      const rVal = model.corrs[i]?.[j] ?? 0
      if (Math.abs(rVal) > 0.8) {
        collinearityWarnings.push(
          `Hai biến '${model.features[i]}' và '${model.features[j]}' tương quan cao (|r|=${Math.abs(rVal).toFixed(2)} > 0,8) — thận trọng khi diễn giải đồng thời.`
        )
      }
    }
  }

  if (movedIndices.length === 0) {
    return {
      changes,
      target: targetCol,
      target_change_pct: 0,
      ci90_pct: [0, 0] as [number, number],
      target_change_abs: 0,
      baseline_target_mean: Number(baselineMean.toFixed(2)),
      range_warnings: [],
      collinearity_warnings: [],
      contributions,
      interpretation: "Chưa thay đổi biến nào (liên đới theo mô hình, không phải nhân quả).",
    }
  }

  const pctOutcomes = model.bootWeights.map((w) => {
    let deltaYNorm = 0
    for (let k = 0; k < changes.length; k++) {
      const j = model.features.indexOf(changes[k].feature)
      deltaYNorm += w[j] * deltaZs[k]
    }
    if (model.logTarget) return (Math.exp(deltaYNorm * model.ySd) - 1) * 100
    return ((deltaYNorm * model.ySd) / Math.abs(baselineMean)) * 100
  })

  let pointNorm = 0
  for (let k = 0; k < changes.length; k++) {
    const j = model.features.indexOf(changes[k].feature)
    pointNorm += model.weights[j] * deltaZs[k]
  }
  const pointPct = model.logTarget
    ? (Math.exp(pointNorm * model.ySd) - 1) * 100
    : ((pointNorm * model.ySd) / Math.abs(baselineMean)) * 100

  const sortedPcts = sortedNums(pctOutcomes)
  const ciLo = quantile(sortedPcts, 0.05)
  const ciHi = quantile(sortedPcts, 0.95)
  const absChange = (baselineMean * pointPct) / 100
  const pkgSummary = changes
    .filter((c) => c.pct_change !== 0)
    .map((c) => `${c.feature} ${c.pct_change > 0 ? "+" : ""}${c.pct_change}%`)
    .join(", ")

  return {
    changes,
    target: targetCol,
    target_change_pct: Number(pointPct.toFixed(2)),
    ci90_pct: [Number(ciLo.toFixed(2)), Number(ciHi.toFixed(2))] as [number, number],
    target_change_abs: Number(absChange.toFixed(2)),
    baseline_target_mean: Number(baselineMean.toFixed(2)),
    range_warnings: rangeWarnings,
    collinearity_warnings: collinearityWarnings,
    contributions,
    interpretation: `Khi ${pkgSummary}, ${targetCol} dự kiến thay đổi ${pointPct >= 0 ? "+" : ""}${pointPct.toFixed(2)}% (KTC 90%: ${ciLo.toFixed(2)}% đến ${ciHi.toFixed(2)}%, liên đới theo mô hình, không phải nhân quả).`,
  }
}

export function runKMeans(
  rows: Record<string, unknown>[],
  numericCols: string[]
): {
  k: number
  silhouette: number
  features: string[]
  profiles: { cluster: number; size: number; share: number; medians: Record<string, number | null>; distinctive: { feature: string; z: number; median: number | null; overall_median: number | null }[] }[]
  labels: number[]
} | null {
  const features = numericCols.slice(0, 6)
  if (features.length < 2 || rows.length < 15) return null

  const colMeds = features.map((f) => median(rows.map((r) => r[f]).filter((v): v is number => typeof v === "number" && Number.isFinite(v))))
  const raw = rows.map((r) => features.map((f, j) => (typeof r[f] === "number" && Number.isFinite(r[f] as number) ? (r[f] as number) : colMeds[j])))
  const means = features.map((_, j) => mean(raw.map((r) => r[j])))
  const sds = features.map((_, j) => std(raw.map((r) => r[j])) || 1)
  const X = raw.map((r) => r.map((v, j) => (v - means[j]) / sds[j]))

  const rand = mulberry32(1337)
  let best: { k: number; sil: number; labels: number[] } | null = null

  for (const k of [2, 3, 4]) {
    if (X.length <= k * 3) continue
    const centroids: number[][] = []
    for (let c = 0; c < k; c++) {
      centroids.push([...X[Math.floor(rand() * X.length)]])
    }
    const labels = new Array<number>(X.length).fill(0)
    for (let iter = 0; iter < 15; iter++) {
      let changed = false
      for (let i = 0; i < X.length; i++) {
        let bestC = 0
        let bestD = Infinity
        for (let c = 0; c < k; c++) {
          let d = 0
          for (let j = 0; j < features.length; j++) d += (X[i][j] - centroids[c][j]) ** 2
          if (d < bestD) {
            bestD = d
            bestC = c
          }
        }
        if (labels[i] !== bestC) {
          labels[i] = bestC
          changed = true
        }
      }
      if (!changed) break
      for (let c = 0; c < k; c++) {
        const members = X.filter((_, i) => labels[i] === c)
        if (members.length === 0) continue
        for (let j = 0; j < features.length; j++) {
          centroids[c][j] = mean(members.map((m) => m[j]))
        }
      }
    }
    // Sample up to 120 pts for silhouette speed
    const step = Math.max(1, Math.floor(X.length / 120))
    const sils: number[] = []
    for (let i = 0; i < X.length; i += step) {
      const ci = labels[i]
      const distTo = new Array<number>(k).fill(0)
      const cntTo = new Array<number>(k).fill(0)
      for (let j = 0; j < X.length; j += step) {
        if (i === j) continue
        let d = 0
        for (let f = 0; f < features.length; f++) d += (X[i][f] - X[j][f]) ** 2
        d = Math.sqrt(d)
        distTo[labels[j]] += d
        cntTo[labels[j]]++
      }
      const a = cntTo[ci] > 0 ? distTo[ci] / cntTo[ci] : 0
      let b = Infinity
      for (let c = 0; c < k; c++) {
        if (c !== ci && cntTo[c] > 0) b = Math.min(b, distTo[c] / cntTo[c])
      }
      if (Number.isFinite(b) && Math.max(a, b) > 0) sils.push((b - a) / Math.max(a, b))
    }
    const sil = sils.length ? mean(sils) : 0
    if (!best || sil > best.sil) best = { k, sil, labels }
  }
  if (!best) return null

  const overallMedians = Object.fromEntries(features.map((f, j) => [f, colMeds[j]]))
  const profiles = Array.from({ length: best.k }, (_, c) => {
    const idxs = best!.labels.map((l, i) => (l === c ? i : -1)).filter((i) => i >= 0)
    const medians: Record<string, number | null> = {}
    const distinctive: { feature: string; z: number; median: number | null; overall_median: number | null }[] = []
    features.forEach((f, j) => {
      const vals = idxs.map((i) => raw[i][j])
      const m = vals.length ? median(vals) : null
      medians[f] = m !== null ? Number(m.toFixed(2)) : null
      const z = m !== null ? (m - means[j]) / (sds[j] || 1) : 0
      distinctive.push({
        feature: f,
        z: Number(z.toFixed(2)),
        median: medians[f],
        overall_median: Number(overallMedians[f].toFixed(2)),
      })
    })
    distinctive.sort((a, b) => Math.abs(b.z) - Math.abs(a.z))
    return {
      cluster: c + 1,
      size: idxs.length,
      share: Number((idxs.length / rows.length).toFixed(3)),
      medians,
      distinctive: distinctive.slice(0, 3),
    }
  }).filter((p) => p.size > 0)

  return {
    k: profiles.length,
    silhouette: Number(best.sil.toFixed(3)),
    features,
    profiles,
    labels: best.labels,
  }
}
