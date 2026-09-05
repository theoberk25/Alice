# Local semantic gateway

`LocalLLMProvider` exposes health, model metadata, decision/evidence summaries, clarification generation, agent-response summaries, and informational intent parsing. `OllamaProvider` routes through native commands. The configured model is an installed Ollama model, not a hardcoded 70B dependency.

The Rust client sends `/api/chat` with streaming disabled, a constrained JSON format, bounded output, and `think:false`. Only `message.content` is parsed; `message.thinking` and provider envelopes never reach the renderer. React validates the output with strict Zod objects and checks referenced evidence IDs against the selected record. Private-reasoning markers are rejected as an additional display safeguard. These checks cannot certify the factual correctness of arbitrary prose; generated text remains assistance, visually separate from structured evidence.

Allowed intents are `EXPLAIN_DECISION`, `SUMMARIZE_EVIDENCE`, `SUMMARIZE_CONTEXT`, `REQUEST_CLARIFICATION`, `RESEARCH`, and `UNKNOWN`. Unknown keys, authorization verbs, and mismatched decision IDs are rejected. The model has no tools or path to `submit_action`. It cannot manufacture a native verification grant, alter upstream decisions, or override policy.

The initial automatic clarification does not depend on the model. If a model is available, the gateway can generate additional questions and summarize agent responses. The original text remains available as an agent claim. Ollama outage produces a concise structured fallback and never disables the four explicit technician controls.

API behavior follows [Ollama chat documentation](https://docs.ollama.com/api/chat). No external model API or OpenAI API credential is used.

## Ollama grammar compatibility

The native gateway removes `minLength` and `maxLength` recursively from the JSON Schema sent to Ollama for constrained sampling. The installed runner rejected the generated `char{1,3000}` grammar and crashed, returning HTTP 500 for automatic agent summaries. Types, enum choices, required fields and additional-property restrictions remain in the sampling schema. The original strict Zod schemas still enforce string lengths, evidence references and allowed output after inference; native output-size limits remain in place. This changes sampling compatibility, not application validation or authorization.

Identical operational errors are displayed once rather than stacked repeatedly. The live native regression test now supplies the same bounded string fields that exposed the crash, instead of an unbounded simplified schema.
