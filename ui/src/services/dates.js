const DAY = 86400000;

// Date-only strings ("2026-05-10") and Dates both read as a UTC calendar day.
export function utcDay(value) {
  if (value instanceof Date) return new Date(Date.UTC(value.getUTCFullYear(), value.getUTCMonth(), value.getUTCDate()));
  return new Date(`${String(value).slice(0, 10)}T00:00:00Z`);
}

export const todayUTC = () => utcDay(new Date());

export const isoDay = (d) => utcDay(d).toISOString().slice(0, 10);

export const fmtDate = (d) =>
  utcDay(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

export const clampDate = (d, min, max) => new Date(Math.min(Math.max(d, min), max));

// Accepts "2026-05-12", "12 May 2026", "May 12 2026"; null when unreadable.
export function parseDay(text) {
  const t = text.trim();
  if (!t) return null;
  const d = /^\d{4}-\d{2}-\d{2}$/.test(t) ? new Date(`${t}T00:00:00Z`) : new Date(`${t} UTC`);
  return Number.isNaN(d.getTime()) ? null : utcDay(d);
}

// Slider stops: the start, every month boundary (or 1st and 15th for spans under six
// months, so short corpora still get several stops), then the end.
export function snapStops(start, end) {
  const s = utcDay(start);
  const e = utcDay(end);
  if (e <= s) return [s];
  const fine = (e - s) / DAY < 183;
  const stops = [s];
  let y = s.getUTCFullYear();
  let m = s.getUTCMonth();
  for (;;) {
    for (const dom of fine ? [1, 15] : [1]) {
      const d = new Date(Date.UTC(y, m, dom));
      if (d >= e) return [...stops, e];
      if (d > s) stops.push(d);
    }
    m += 1;
    if (m === 12) { m = 0; y += 1; }
  }
}
