const EPOCH = new Date('2026-01-10T00:00:00Z').getTime()
const YC_DEADLINE = new Date('2026-07-27T00:00:00Z').getTime()

export function getDayNumber(now: Date = new Date()): number {
  return Math.floor((now.getTime() - EPOCH) / 86_400_000) + 1
}

// Clamped at 0, matching /api/metrics: once the deadline passes the UI hides
// the countdown instead of showing a negative number of days.
export function getYcDaysRemaining(now: Date = new Date()): number {
  return Math.max(0, Math.ceil((YC_DEADLINE - now.getTime()) / 86_400_000))
}

export function getIstTimeString(now: Date = new Date()): string {
  return now.toLocaleTimeString('en-IN', {
    hour12: false,
    timeZone: 'Asia/Kolkata',
  })
}
