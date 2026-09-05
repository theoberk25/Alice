import { useState } from 'react';
import { ArrowUp, Terminal, LoaderCircle } from 'lucide-react';
import { useConsole } from '../../state/console';
export function CommandPanel() {
  const { ask, llm, selectedId } = useConsole();
  const [input, setInput] = useState(''),
    [answer, setAnswer] = useState(''),
    [busy, setBusy] = useState(false);
  const [answerId, setAnswerId] = useState('');
  async function send(text = input) {
    if (!text.trim() || busy) return;
    setBusy(true);
    setAnswerId(selectedId);
    try {
      setAnswer(await ask(text));
      setInput('');
    } catch (e) {
      setAnswer(`Language assistance unavailable: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="command-panel">
      <div className="command-label">
        <span>
          <Terminal size={14} /> ALICE COMMAND
        </span>
        <span className="muted">
          {llm.status === 'READY' ? 'LOCAL LANGUAGE GATEWAY' : 'STRUCTURED FALLBACK'} <i>·</i> TEXT
          ONLY
        </span>
      </div>
      {answer && answerId === selectedId && (
        <div className="command-response" role="status">
          {answer}
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <span className="command-caret">›</span>
        <input
          aria-label="Ask ALICE"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about this decision, evidence, or agent justification…"
          maxLength={2000}
        />
        <button aria-label="Send question" disabled={busy || !input.trim()}>
          {busy ? <LoaderCircle className="spin" size={17} /> : <ArrowUp size={17} />}
        </button>
      </form>
      <div className="command-suggestions">
        <button onClick={() => void send('Why was this held?')}>Why was this held?</button>
        <button onClick={() => void send('What evidence is still unverified?')}>
          Unverified evidence
        </button>
        <span>Assistance cannot authorize actions.</span>
      </div>
    </section>
  );
}
