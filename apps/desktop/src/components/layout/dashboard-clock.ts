import { useEffect, useState } from 'react';

export function formatDashboardClock(instant: Date, timeZone: string) {
  // One formatter keeps the time, calendar date and DST-sensitive zone label together.
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    hourCycle: 'h23',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    month: 'short',
    day: '2-digit',
    timeZoneName: 'short',
  }).formatToParts(instant);
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((entry) => entry.type === type)?.value ?? '';
  return {
    time: `${part('hour')}:${part('minute')}:${part('second')}`,
    date: `${part('month').toUpperCase()} ${part('day')}`,
    zoneLabel: part('timeZoneName'),
    timeZone,
  };
}

function readDashboardClock() {
  // Resolve again on every update so a device-zone change does not leave cached formatting.
  const timeZone = new Intl.DateTimeFormat().resolvedOptions().timeZone;
  return formatDashboardClock(new Date(), timeZone);
}

export function useDashboardClock() {
  const [clock, setClock] = useState(readDashboardClock);
  useEffect(() => {
    const refresh = () => setClock(readDashboardClock());
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') refresh();
    };
    const timer = window.setInterval(refresh, 1000);
    window.addEventListener('focus', refresh);
    window.addEventListener('pageshow', refresh);
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', refresh);
      window.removeEventListener('pageshow', refresh);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, []);
  return clock;
}
