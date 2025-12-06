// frontend/src/lib/time.ts
export function formatDurationSec(seconds?: number | null): string {
  if (seconds == null || Number.isNaN(seconds)) return "-";
  const s = Math.round(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  if (m === 0) return `${r}s`;
  if (r === 0) return `${m} min`;
  return `${m} min ${r}s`;
}
