import { useState } from 'react';
import { Modal, Badge } from '@alice/ui';
import { useConsole } from '../../state/console';
import { isNative, nativeCall } from '../../lib/native';
export function SettingsModal({ onClose }: { onClose: () => void }) {
  const { llm, refreshLLM, mode } = useConsole();
  const [model, setModel] = useState(llm.status === 'READY' ? llm.model : ''),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  return (
    <Modal title="Local connections" onClose={onClose}>
      <div className="settings-content">
        <Badge tone={mode === 'mock' ? 'warning' : 'information'}>
          {mode === 'mock' ? 'MOCK ALICE TRANSPORT' : 'REMOTE ALICE TRANSPORT'}
        </Badge>
        {mode === 'remote' && (
          <div className="settings-boundary">
            <h3>Live Pi feed</h3>
            <p>
              The workstation reads the Pi ledger through the configured local bridge. Initial
              history loads automatically, then new events arrive without refresh.
            </p>
            <p>
              Configure ALICE_FEED_URL and ALICE_FEED_TOKEN in the native app or Vite server
              environment. Pi access uses SSH forwarding. Connection credentials stay outside this
              dashboard.
            </p>
            <p>
              Remote accept/deny delivery is unavailable. Reconnecting never loads demonstration
              records.
            </p>
            <button
              className="small-button"
              onClick={() =>
                void useConsole
                  .getState()
                  .start()
                  .catch((e) => setError(String(e)))
              }
            >
              Reconnect and reload runtime history
            </button>
          </div>
        )}
        <h3>Local language gateway</h3>
        <p>
          Ollama runs on this Mac. Select an already installed model. Core review controls remain
          available when the model is offline.
        </p>
        <form
          className="stack-form"
          onSubmit={(e) => {
            e.preventDefault();
            setBusy(true);
            void nativeCall('configure_llm', { model })
              .then(refreshLLM)
              .catch((e) => setError(String(e)))
              .finally(() => setBusy(false));
          }}
        >
          <label>
            Ollama model
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="e.g. qwen2.5:7b"
            />
          </label>
          <button className="primary-button" disabled={!isNative || busy}>
            {busy ? 'Checking model…' : 'Save & check connection'}
          </button>
        </form>
        <p>
          Gateway: <strong>{llm.status}</strong> · {llm.model || 'No model selected'}
        </p>
        {!isNative && (
          <p className="inline-notice">
            Open the native app to configure Ollama and biometric connections.
          </p>
        )}
        <p className="inline-error">{error}</p>
        <div className="settings-boundary">
          <h3>Face identity</h3>
          <p>
            Live face recognition uses your Mac camera, guided head movements and the local
            biometric service. Face data stays on this computer.
          </p>
        </div>
      </div>
    </Modal>
  );
}
