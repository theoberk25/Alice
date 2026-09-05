import { useEffect, useRef, useState } from 'react';
import { Camera, VideoOff } from 'lucide-react';
export function CameraCapture({
  onCapture,
  busy,
  count = 1,
}: {
  onCapture: (frames: string[]) => Promise<void>;
  busy: boolean;
  count?: number;
}) {
  const video = useRef<HTMLVideoElement>(null),
    stream = useRef<MediaStream | undefined>(undefined);
  const [error, setError] = useState(''),
    [cameras, setCameras] = useState<MediaDeviceInfo[]>([]),
    [device, setDevice] = useState(''),
    [ready, setReady] = useState(false),
    [sample, setSample] = useState(0);
  useEffect(() => {
    let disposed = false;
    setReady(false);
    setError('');
    async function open() {
      try {
        const next = await navigator.mediaDevices.getUserMedia({
          video: device
            ? { deviceId: { exact: device }, width: 640, height: 480 }
            : { width: 640, height: 480 },
          audio: false,
        });
        if (disposed) {
          next.getTracks().forEach((t) => t.stop());
          return;
        }
        stream.current = next;
        if (video.current) {
          video.current.srcObject = next;
          await video.current.play();
        }
        setCameras(
          (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === 'videoinput'),
        );
        setReady(true);
      } catch (e) {
        setError(
          e instanceof DOMException && e.name === 'NotAllowedError'
            ? 'Camera permission denied. Allow Camera access for ALICE in macOS Privacy & Security.'
            : `Camera unavailable: ${String(e)}`,
        );
      }
    }
    void open();
    return () => {
      disposed = true;
      stream.current?.getTracks().forEach((t) => t.stop());
    };
  }, [device]);
  async function capture() {
    const frames: string[] = [];
    setError('');
    try {
      for (let i = 0; i < count; i++) {
        if (!video.current?.videoWidth) throw new Error('Camera frame is not ready.');
        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 480;
        canvas.getContext('2d')?.drawImage(video.current, 0, 0, 640, 480);
        frames.push(canvas.toDataURL('image/jpeg', 0.86).split(',')[1]!);
        setSample(i + 1);
        if (i + 1 < count) await new Promise((resolve) => setTimeout(resolve, 450));
      }
      await onCapture(frames);
    } catch (e) {
      setError(String(e));
    } finally {
      setSample(0);
    }
  }
  return (
    <div className="camera-capture">
      <div className="camera-preview">
        <video ref={video} playsInline muted />
        <div className="face-frame" />
        {error && (
          <div className="camera-error">
            <VideoOff size={30} />
            <p>{error}</p>
          </div>
        )}
      </div>
      {cameras.length > 1 && (
        <select
          aria-label="Select camera"
          value={device}
          onChange={(e) => setDevice(e.target.value)}
        >
          {cameras.map((c) => (
            <option key={c.deviceId} value={c.deviceId}>
              {c.label || 'Camera'}
            </option>
          ))}
        </select>
      )}
      <p className="capture-guidance">
        Center one face in the frame. Use even lighting.
        {count > 1 ? ' Move your head slightly between samples.' : ''}
      </p>
      <button
        className="primary-button"
        disabled={busy || !ready || sample > 0}
        onClick={() => void capture()}
      >
        <Camera size={16} />
        {busy
          ? 'Verifying identity…'
          : sample
            ? `Capturing sample ${sample} / ${count}`
            : `Capture ${count > 1 ? `${count} samples` : 'and verify'}`}
      </button>
    </div>
  );
}
