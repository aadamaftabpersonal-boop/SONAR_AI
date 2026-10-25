import { useEffect, useState } from 'react'

/** The current time, refreshed so "3 min ago" stays true while the page is open. */
export function useNow(everyMs = 15000): Date {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), everyMs)
    return () => clearInterval(id)
  }, [everyMs])
  return now
}

export function timeAgo(iso: string, now: Date = new Date()): string {
  const seconds = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 1000))
  if (seconds < 10) return 'just now'
  if (seconds < 60) return `${seconds} s ago`
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  return `${hours} h ago`
}

export function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function elapsed(fromIso: string | null, toIso: string | null, now: Date = new Date()) {
  if (!fromIso) return null
  const end = toIso ? new Date(toIso) : now
  const s = Math.max(0, Math.round((end.getTime() - new Date(fromIso).getTime()) / 1000))
  return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${s % 60} s`
}
