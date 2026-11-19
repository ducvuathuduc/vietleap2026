/**
 * First-view entrance: opacity 0→1 and a 4px rise, 180 ms,
 * once per mount, CSS only. `starting:` is `@starting-style`, so it cannot
 * re-trigger on scroll; with no transition the reduced-motion rules jump straight
 * to the final state.
 */
export function enterClass(delayMs = 0): string {
  const base =
    "transition-[opacity,translate] duration-[180ms] ease-out starting:opacity-0 starting:translate-y-1 motion-reduce:transition-none"
  return delayMs > 0 ? `${base} [transition-delay:${delayMs}ms]` : base
}
