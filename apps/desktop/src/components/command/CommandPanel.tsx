import { useState } from 'react';
import { BorderTrail, CommandButton, Tooltip } from '@alice/ui';
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
      <BorderTrail active={busy} />
      <div className="command-label">
        <span>
          <Terminal size={14} /> ALICE assistance
        </span>
        <span className="muted">
          {llm.status === 'READY' ? 'Local language gateway' : 'Structured fallback'} <i>·</i> TEXT
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
        <Tooltip content="Send question">
          <CommandButton aria-label="Send question" disabled={busy || !input.trim()}>
            {busy ? <LoaderCircle className="spin" size={17} /> : <ArrowUp size={17} />}
          </CommandButton>
        </Tooltip>
      </form>
      <div className="command-suggestions">
        <CommandButton onClick={() => void send('Why was this held?')}>
          Why was this held?
        </CommandButton>
        <CommandButton onClick={() => void send('What evidence is still unverified?')}>
          Unverified evidence
        </CommandButton>
        <span>Assistance cannot authorize actions.</span>
      </div>
    </section>
  );
}
