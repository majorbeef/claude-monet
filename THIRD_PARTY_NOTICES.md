# Third-party notices

monet is an adaptation of apple-pi for Claude Code. It carries apple-pi's skills and roles (modified) and reimplements a few of its mechanisms in Python.

## apple-pi

- Source: <https://github.com/z3z1ma/apple-pi>
- Imported commit: `4c70e80688b5ec3ca279bc523f743bdb72aa9963`
- License: MIT (see `LICENSE`)
- Original notice: `Copyright (c) 2026 apple-pi contributors`
- Adapted paths: `skills/` (all but `distill`, `reflect`, `interrogate` and `promote` copied and modified; `interrogate` and `promote` from apple-pi's `prompts/`; `distill` and `reflect` from its notebook prompts), `agents/` (from `roles/`, without `coordinator`), `lib/monet.py` (ledger behavior ported from `components/shared/src/ledger-files.ts`; notebook and distillation prompts from `components/notebook/`), `hooks/reflect.py` (from `components/notebook/src/hooks/learning-cycle.ts`).
- Changes: Pi tools, the organization runtime (mail, channels, hiring), browser sign-off pages, `pi_exec`, and the wiki were replaced with Claude Code subagents, `AskUserQuestion`, plain files, and the `monet-*` commands.


## Review page libraries (bundled in `lib/web/vendor/`)

- marked `12.0.2` (<https://github.com/markedjs/marked>): MIT, `Copyright (c) 2018+, MarkedJS` and `Copyright (c) 2011-2018, Christopher Jeffrey`. Full license in `lib/web/vendor/LICENSE.marked`.
- DOMPurify `3.1.6` (<https://github.com/cure53/DOMPurify>): `Apache-2.0 OR MPL-2.0`, `Copyright (c) Cure53 and other contributors`. Full license in `lib/web/vendor/LICENSE.dompurify`.
- Mermaid `10.9.1` (<https://github.com/mermaid-js/mermaid>, MIT) is not bundled; the page loads it from jsDelivr only for documents with a diagram.

The review page's design follows apple-pi's `sign_off_document` (`components/browser-pages/`); its code is new.

The notices below are carried over from apple-pi for the parts of its work that monet retains.

## pi-observational-memory

- Source: <https://github.com/elpapi42/pi-observational-memory>
- Imported commit: `37986b6faa1e39eb5aa1d03a4ca6379ecaf3148d`
- Local path: `components/notebook/`; integration in `extensions/context.ts`
- License: MIT
- Original notice: `Copyright (c) 2026 pi-observational-memory contributors`

## mattpocock/skills → engineering workflows and disciplines

- Source: <https://github.com/mattpocock/skills>
- Imported commit: `6654f6b60cd9d5be8b54c6fafe44346dabeb3b76`
- Author named by the source package: Matt Pocock
- Local paths: `prompts/interrogate.md`, `skills/interrogate-to-design/`, `skills/to-spec/`, `skills/to-tickets/`, `skills/implement/`, `skills/improve-codebase-architecture/`, `skills/wayfinder/`, `skills/prototype/`, `skills/diagnosing-bugs/`, `skills/research/`, `skills/tdd/`, `skills/resolving-merge-conflicts/`, `skills/domain-modeling/`, `skills/codebase-design/`, `skills/code-review/SKILL.md`, `roles/code-review-specialist.md` (smell baseline), `skills/handbook-writing/`
- License: MIT
- Original notice: `Copyright (c) 2026 Matt Pocock`
- apple-pi retains the implemented engineering methods while adapting task artifacts, reusable context, agents, review reconciliation, and Git authority to its own harness. Task artifacts live freely inside their governing ledger bundle; reusable LLM-derived documentation lives under `.wiki/`.
- Source-path accounting: upstream `grilling` and `grill-with-docs` map to the explicit `/interrogate` prompt and human-only `interrogate-to-design` skill; `to-spec` keeps upstream synthesis and seam confirmation while defaulting publication to a semantically governing live ledger bundle; `to-tickets` keeps upstream tracer bullets, blockers, frontier, quiz, and expand–contract guidance while defaulting one file per ticket to that bundle; `implement` keeps upstream's settled-work → TDD → feedback → review → commit loop while composing Apple Pi's adopted TDD/review contracts, authority boundaries, and explicit assignments to peers for selected parallel tickets; `improve-codebase-architecture` keeps upstream's hot-spot survey, deletion test, visual report, candidate selection, and design interrogation while mapping domain context to `.wiki/` and composing installed skills through explicit package references; `wayfinder` keeps upstream's destination-first map, fog, frontier, decision-ticket types, and one-ticket-per-session loop while storing `map.md` plus `decisions/` in a governing ledger bundle, resolving research through the installed research skill, treating file claims as advisory, and requiring operator-backed execution authority rather than trusting agent-authored Notes; upstream `code-review` is consolidated into Apple Pi's `code-review`; `ask-matt` first mapped to a built-in consultant; second opinions now go to role peers; `setup-matt-pocock-skills` maps to package installation and loader validation; issue-tracker-oriented `triage` is outside Apple Pi's tracker-free task-bundle model; and `wizard` maps to native skill discovery plus explicit `/skill:` invocation. `handbook-writing` adapts `writing-for-agents` (commit `321658273cb1d20b76026717d027d505790106d4`) and its invocation rule, extended to roles and the organization's processes.

## obra/superpowers → retained apple-pi fundamentals

- Source: <https://github.com/obra/superpowers>
- Imported commit: `b36e0829c6d0140e93cfef2ca599b1b07d4a7797`
- Author named by the source package: Jesse Vincent
- Local paths: `skills/completion-verification/`, `skills/workspace-isolation/`, `skills/task-closure/`, `skills/handbook-writing/`
- License: MIT
- Original notice: `Copyright (c) 2025 Jesse Vincent`
- These retained skills express Apple Pi's verification, isolation, integration-authority, and skill-authoring fundamentals. apple-pi retains maintenance responsibility for the adapted paths.

## z3z1ma/10x → ledger foundation

- Source: <https://github.com/z3z1ma/10x>
- Reviewed and adapted commit: `4616e5c07d6f9b82fb299ef18446280ab6f1e09d`
- Author and copyright holder named by the source: Alexander M. Butler
- Local paths: `components/shared/src/ledger-system-prompt.ts`, `docs/ledger.md`, `README.md`, `AGENTS.md`, `skills/completion-verification/`, `skills/task-closure/`, and `.ledger/history/202608202254-strengthen-ledger-workflow/research/ten-x-ledger-philosophy.md`
- License: MIT
- Original notice: `Copyright (c) 2026 Alexander M. Butler`
- apple-pi adapts 10x's durable-judgment concepts—authority and provenance, evidence limits, adversarial review, proportional task records, retrospective compounding, and instruction evaluation—into its open-ended task bundles, verification, and closure procedures. It does not import `.10x/`, the separate record hierarchy, or the autoresearch Python runtime.

## MIT license applying to the imported works

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

