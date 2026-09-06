"""Consented camera/model diagnostic; never enrolls, logs in or issues a grant.

No raw frames, face vectors or participant identifiers are written to disk.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import queue
import resource
import subprocess
import sys
import threading
import time
import uuid
from console_paths import CONSOLE_ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--helper', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=15, choices=range(1, 31))
    parser.add_argument('--consent-live-camera', action='store_true', required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(CONSOLE_ROOT / 'services/biometrics'))
    import numpy as np
    from app.config import Settings
    from app.engine import ArcFaceEngine
    from app.imaging import CaptureError, decode_frame
    from app.live_contract import Outcome
    from app.live_models import load
    config = Settings('diagnostic-does-not-use-service', Path('/tmp/alice-unused-diagnostic-store'),
                      CONSOLE_ROOT / 'services/biometrics/models')
    engine = ArcFaceEngine(config)
    pose_factory, pad, _ = load(config)
    if not engine.ready or not pose_factory or pad is None:
        raise RuntimeError('Required diagnostic models unavailable; camera not opened')
    pose = pose_factory()
    channel = queue.Queue(maxsize=1)
    helper = subprocess.Popen([str(args.helper.resolve()), str(uuid.uuid4()), str(args.seconds)],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    stopped = threading.Event()
    events = []
    dropped = [0]
    preview_times = []

    def read():
        while not stopped.is_set():
            raw = helper.stdout.readline(700_001)
            if not raw:
                break
            if len(raw) > 700_000:
                helper.kill(); break
            packet = json.loads(raw)
            if packet.get('kind') == 'preview':
                # Counts/timestamps only: never retain preview pixels in evidence.
                preview_times.append(packet['elapsed_ms'])
                continue
            if packet.get('kind') != 'frame':
                events.append({k: v for k, v in packet.items() if k != 'session_id'})
                continue
            try:
                channel.put_nowait(packet)
            except queue.Full:
                dropped[0] += 1
        stopped.set()

    worker = threading.Thread(target=read, daemon=True); worker.start()
    counts, regions, timing = Counter(), Counter(), {'identity': [], 'pose': [], 'pad': []}
    start = time.monotonic()
    try:
        while time.monotonic() - start < args.seconds + 2 and (not stopped.is_set() or not channel.empty()):
            try:
                packet = channel.get(timeout=0.2)
            except queue.Empty:
                continue
            counts['sampled'] += 1
            image = None
            try:
                image = decode_frame(packet['jpeg'])
                t = time.perf_counter(); _, bbox = engine.observe(image)
                timing['identity'].append((time.perf_counter()-t)*1000)
                t = time.perf_counter(); observation = pose.observe(image, packet['elapsed_ms'])
                timing['pose'].append((time.perf_counter()-t)*1000)
                t = time.perf_counter(); result = pad.verify(image, bbox)
                timing['pad'].append((time.perf_counter()-t)*1000)
                if not observation.calibrated:
                    counts['calibration_pending'] += 1
                else:
                    regions[observation.region or 'OUT_OF_RANGE'] += 1
                counts['pad_' + result.result.value.lower()] += 1
                if result.result == Outcome.PASS:
                    # Commit only diagnostic pose calibration, never a template
                    # or identity decision. This tool has no enrollment store.
                    pose.accept()
                else:
                    pose.interrupt()
            except CaptureError as error:
                pose.interrupt()
                counts[str(error)] += 1
            del packet, image
    finally:
        helper.kill() if helper.poll() is None else None
        helper.wait(timeout=2); worker.join(timeout=1); pose.close()
    measured = {key: {'count':len(v), 'p50_ms':round(float(np.percentile(v,50)),2),
                      'p95_ms':round(float(np.percentile(v,95)),2)} for key,v in timing.items() if v}
    print(json.dumps({'scope':'camera and adapter diagnostic only; not a labeled genuine or attack trial',
                      'counts':dict(counts), 'pose_regions':dict(regions), 'dropped':dropped[0],
                      'timing':measured, 'python_peak_rss_mib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024**2,1),
                      'helper_events':events, 'helper_exit':helper.returncode,
                      'preview': {'frames':len(preview_times),
                          'fps':round((len(preview_times)-1)*1000/(preview_times[-1]-preview_times[0]),2)
                              if len(preview_times)>1 else 0,
                          'interval_p95_ms':round(float(np.percentile(np.diff(preview_times),95)),2)
                              if len(preview_times)>1 else None},
                      'authorization':'NOT_ATTEMPTED'}, indent=2))

if __name__ == '__main__':
    main()
