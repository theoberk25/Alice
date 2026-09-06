import { act, cleanup, render, renderHook, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  formatDashboardClock,
  useDashboardClock,
} from '../../apps/desktop/src/components/layout/dashboard-clock';
import { Header } from '../../apps/desktop/src/components/layout/Header';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

it.each([
  ['2026-01-15T17:34:56Z', 'America/New_York', '12:34:56', 'JAN 15', 'EST'],
  ['2026-07-15T17:34:56Z', 'America/New_York', '13:34:56', 'JUL 15', 'EDT'],
  ['2026-01-15T17:34:56Z', 'Asia/Tokyo', '02:34:56', 'JAN 16', 'GMT+9'],
  ['2026-01-15T18:30:00Z', 'Asia/Kolkata', '00:00:00', 'JAN 16', 'GMT+5:30'],
  ['2026-01-16T05:00:00Z', 'America/New_York', '00:00:00', 'JAN 16', 'EST'],
])('formats %s in %s with a matching local date and zone', (instant, zone, time, date, label) => {
  expect(formatDashboardClock(new Date(instant), zone)).toEqual({
    time,
    date,
    zoneLabel: label,
    timeZone: zone,
  });
});

it('changes both time and zone label at the Eastern spring DST transition', () => {
  const before = formatDashboardClock(new Date('2026-03-08T06:59:59Z'), 'America/New_York');
  const after = formatDashboardClock(new Date('2026-03-08T07:00:00Z'), 'America/New_York');
  expect(before).toMatchObject({ time: '01:59:59', date: 'MAR 08', zoneLabel: 'EST' });
  expect(after).toMatchObject({ time: '03:00:00', date: 'MAR 08', zoneLabel: 'EDT' });
});

it('changes the label with the repeated hour at the Eastern autumn DST transition', () => {
  const before = formatDashboardClock(new Date('2026-11-01T05:59:59Z'), 'America/New_York');
  const after = formatDashboardClock(new Date('2026-11-01T06:00:00Z'), 'America/New_York');
  expect(before).toMatchObject({ time: '01:59:59', date: 'NOV 01', zoneLabel: 'EDT' });
  expect(after).toMatchObject({ time: '01:00:00', date: 'NOV 01', zoneLabel: 'EST' });
});

describe('device clock updates', () => {
  let deviceZone: string;
  beforeEach(() => {
    deviceZone = 'America/New_York';
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] });
    vi.setSystemTime(new Date('2026-01-15T17:34:56Z'));
    const resolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;
    vi.spyOn(Intl.DateTimeFormat.prototype, 'resolvedOptions').mockImplementation(function (
      this: Intl.DateTimeFormat,
    ) {
      return { ...resolvedOptions.call(this), timeZone: deviceZone };
    });
  });

  it('reads the current wall clock after a jump instead of counting elapsed ticks', () => {
    const { result } = renderHook(useDashboardClock);
    expect(result.current.time).toBe('12:34:56');
    act(() => {
      vi.setSystemTime(new Date('2026-01-16T05:00:00Z'));
      vi.advanceTimersByTime(1000);
    });
    expect(result.current).toMatchObject({ time: '00:00:01', date: 'JAN 16', zoneLabel: 'EST' });
  });

  it('resolves a changed device zone on the next interval', () => {
    const { result } = renderHook(useDashboardClock);
    act(() => {
      deviceZone = 'Asia/Tokyo';
      vi.advanceTimersByTime(1000);
    });
    expect(result.current).toEqual({
      time: '02:34:57',
      date: 'JAN 16',
      zoneLabel: 'GMT+9',
      timeZone: 'Asia/Tokyo',
    });
  });

  it.each(['focus', 'pageshow', 'visibilitychange'])(
    'refreshes the instant and device zone immediately on %s without waiting for a tick',
    (event) => {
      vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
      const { result } = renderHook(useDashboardClock);
      act(() => {
        deviceZone = 'Asia/Kolkata';
        vi.setSystemTime(new Date('2026-07-15T18:30:00Z'));
        (event === 'visibilitychange' ? document : window).dispatchEvent(new Event(event));
      });
      expect(result.current).toEqual({
        time: '00:00:00',
        date: 'JUL 16',
        zoneLabel: 'GMT+5:30',
        timeZone: 'Asia/Kolkata',
      });
    },
  );

  it('removes the timer and all resume listeners on unmount', () => {
    const windowRemove = vi.spyOn(window, 'removeEventListener');
    const documentRemove = vi.spyOn(document, 'removeEventListener');
    const { unmount } = renderHook(useDashboardClock);
    expect(vi.getTimerCount()).toBe(1);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
    expect(windowRemove).toHaveBeenCalledWith('focus', expect.any(Function));
    expect(windowRemove).toHaveBeenCalledWith('pageshow', expect.any(Function));
    expect(documentRemove).toHaveBeenCalledWith('visibilitychange', expect.any(Function));
  });

  it('renders static local digits and exposes the IANA zone alongside the visible abbreviation', () => {
    render(<Header onIdentity={() => {}} onSettings={() => {}} />);
    const clock = screen.getByRole('timer');
    expect(clock).toHaveTextContent('12:34:56');
    expect(clock).toHaveTextContent('EST / JAN 15');
    expect(clock).toHaveAccessibleName('Device time: 12:34:56, JAN 15, EST (America/New_York)');
    expect(clock).toHaveAttribute('title', 'Device time zone: America/New_York');
    expect(clock.querySelector('strong')?.childElementCount).toBe(0);
  });
});
