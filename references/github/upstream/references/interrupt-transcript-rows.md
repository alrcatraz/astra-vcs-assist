# Interrupt & synthetic transcript rows: who sees them

Hermes writes **synthetic assistant rows** for several internal events (interrupt
close, redirect checkpoint, batch-timeout abort, compression handoff). Two facts
about these rows cause recurring bugs; both are about *audience*, not content.

## Rule 1 — `display_kind="hidden"` hides from the UI, NOT from the model

A hidden row is filtered at **transcript projection** (CLI/web renderers drop it).
It is **still sent to the provider**: the pre-request projection substitutes the
row's `api_content` sidecar back into `content`, so the model reads it as its own
prior-turn text on every subsequent call.

Consequence: **a short natural-language phrase in that slot gets echoed verbatim.**
The model, seeing "Operation interrupted" positioned as its own last turn, learns to
answer ordinary instructions with exactly that string (`finish_reason=stop`, 2-3
output tokens) — and each echo re-persists, raising the phrase's density in the
window and reinforcing the loop. The fix is **never** to hide it harder; it is to put
something the model has no reason to *say* there — a structural, self-describing
label (`[interrupt: no assistant output for this turn]`) — mirroring how the codebase
already bars the redirect scaffold from assistant text and replaces runaway-repetition
partials with a description instead of replaying them.

### Diagnosing an echo loop

When a user reports the agent answering with a fixed phrase:

1. **Separate the writers by shape.** Group persisted rows by exact length/content:
   the system-synthesised spelling (e.g. trailing period) vs the model's imitation
   (often the same words minus punctuation). They are different producers — do not
   conflate them; a fix aimed at one leaves the other.
2. **Density decides whether the model imitates.** Compare the count of the phrase
   inside the current send window across sessions. A session where the phrase sits
   near ~10% of recent turns reproduces it; the same total count spread outside the
   window does not. "Some sessions have it, some don't" is explained by recency
   concentration, not by a per-session defect.
3. **Check the API-call log line, not just the DB row.** `reason=text_response(finish_reason=stop)`
   with tiny `out=N` means the MODEL emitted it; an exit reason naming an interrupt
   means the SYSTEM wrote it. Same visible text, opposite root cause, and only the
   log distinguishes them.
4. **Fix the writer, then retire old rows.** Changing the constant only affects
   newly-written rows; already-persisted ones keep replaying the old spelling, so a
   projection-side filter must also neutralise/retire rows carrying superseded
   spellings — but see Rule 2 before dropping anything.

## Rule 2 — you cannot freely DROP a synthetic row: role alternation

Synthetic closes exist to satisfy strict providers' role-alternation rules. A
transcript ending on a raw `tool` message makes the next user message land as
`tool → user`, which Gemini/Claude answer by hallucinating a continuation and
ignoring prior context (the user perceives "lost context").

So when a projection filter removes hidden placeholder rows:

- **Dropping is safe** when neighbours stay valid (e.g. between two user turns —
  sequence repair merges those).
- **Dropping is unsafe** when it would recreate `tool → user`. `repair_message_sequence`
  deliberately does NOT fix that pair (it treats `assistant(tool_calls)/tool/user` as
  legal), so the violation survives to the provider.
- Correct handling for the unsafe case: **keep the row, rewrite its text** to the
  current neutral label. Rewrite to a value that is NOT itself in the hazard set, or
  the filter re-triggers every call.

Prove both branches in tests: legacy-row-between-users drops; legacy-row-after-a-
tool-result is kept-and-neutralised; a row carrying the *current* label is left
untouched (that assertion is what keeps the empty-message re-heal guard intact).

## Pitfalls hit while fixing this class

- **A half-fix looks complete.** Hiding the row from the UI satisfies the visible
  symptom (no bubble) and passes local review, but leaves the model-visible copy
  untouched — the actual echo bug survives. Before calling an interrupt-text fix
  done, ask about *both* audiences: does the user still see it, does the model still
  read it?
- **Existing tests may pin the literal string, not the behaviour.** When you change a
  placeholder wording, assertions like `assert content == "[old phrase]"` break for
  the wrong reason. Re-point them at the constant so they assert the contract
  (durable row stays empty+hidden, wire copy carries the neutral payload, never the
  scaffold) rather than one chosen spelling. Determine which such failures are yours
  via the two-sided baseline first — some fail identically without your change
  (environment gaps); claiming all of them as regressions wastes a cycle.
- **The commit that fixes the writer and the commit that decouples the assertions are
  two logical changes.** Implementation changes behaviour; the test change alters what
  the tests lock onto. Keep them separate so a reviewer can revert either alone.
