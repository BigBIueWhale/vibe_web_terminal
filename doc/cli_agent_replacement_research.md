# Replacing Mistral Vibe CLI: The Full Investigation

Mistral Vibe CLI gets stuck every second. That's not hyperbole — it stalls constantly,
rate-limits halt execution with unhelpful error messages, the interface lags after a few
minutes of use, and resuming a session at 64% of a 200K context window takes several
minutes while eating an entire CPU core. It needs to go.

The replacement must run **Devstral Small 2 (the 24B parameter model from Mistral AI)
locally on Ollama**, on an **air-gapped network**, inside Docker containers served through
this project's web terminal. No cloud fallbacks. No phoning home. No "works great with
our hosted API" marketing that falls apart the moment you go offline.

This document is the full record of how that replacement was chosen.

---

## The Candidates

Four contenders were evaluated:

1. **Cline CLI 2.0** — the terminal version of the popular VS Code extension
2. **KiloCode CLI 1.0 (Kilo CLI)** — terminal agent from the KiloCode project
3. **OpenAI Codex CLI** — OpenAI's Rust-based terminal coding agent
4. **OpenCode CLI** — the community-driven open-source coding agent (MIT licensed)

A fifth option, **staying on Mistral Vibe CLI**, was rejected outright due to the
constant stalling that prompted this investigation.


---

## Round 1: Cline CLI 2.0 vs KiloCode CLI 1.0

### The Initial Mistake

The first round of research accidentally focused on the **VS Code extensions** instead
of the **terminal CLIs**. This matters because the VS Code extensions and the terminal
CLIs are different products with different codebases, different bugs, and different
maturity levels. Everything below is about the terminal CLIs specifically.

### What Cline CLI 2.0 Actually Is

Cline CLI 2.0 was rebuilt from the ground up but uses the **same Cline core** as the
VS Code extension — meaning it inherits the same agentic loop and the same bugs. It
was announced in late January / early February 2026.

Key features:
- Interactive TUI mode and non-interactive mode (`-y`/`-yolo` for CI/CD)
- Agent Client Protocol (`-acp` flag for Zed, Neovim, Emacs integration)
- Parallel agent instances
- Install: `npm install -g cline`

**License situation is problematic.** The code on GitHub is Apache 2.0, but the official
VS Code extension (and by extension, the CLI distributed by Cline Bot Inc.) comes with
Terms of Service that grant Cline Bot Inc. extensive rights to your prompts, source code,
and responses. This conflict is tracked in GitHub issue #3510 on the cline/cline
repository. On an air-gapped network where code privacy presumably matters, this is a
red flag. You can fork the repo and build your own extension freely under Apache 2.0,
but the official distribution carries the ToS baggage.

**Stability is concerning.** Cline has a persistent, long-standing pattern of
freezing after terminal command execution:
- GitHub issue #531: Execute command just freezes
- GitHub issue #1146: Executing terminal commands hangs Cline
- GitHub issue #1404: Hanging after command execution from any tasks
- GitHub issue #3187: Cline freezes when running commands
- GitHub issue #4049: Cline freezes after running a command
- GitHub issue #5613: Task execution loop stops after git command completes
- GitHub issue #6708: Unresponsive with large terminal output
- GitHub issue #9112 (filed February 4, 2026): "Cline always lags and becomes frozen
  in the latest version" — buttons become unclickable, streams finish but nothing
  happens for 30+ seconds

**Local model support is poor.** Cline's own documentation describes Ollama
compatibility as causing "widespread user frustration" with tool-calling failures.
Users consistently encounter `[ERROR] You did not use a tool in your previous response!`
loops. The Cline GitHub issue #4362 specifically tracks this as a known problem.

### What KiloCode CLI 1.0 Actually Is

KiloCode CLI 1.0 launched on February 5, 2026 — making it literally days old at the
time of this investigation. It is built on top of **OpenCode** (an MIT-licensed
terminal coding agent with 95,000+ GitHub stars and 650+ contributors), with KiloCode's
own additions layered on top.

The latest version on npm is **1.0.16** (published February 5, 2026). The version
history shows 7 releases on February 3 alone (1.0.4 through 1.0.13), which is typical
"just launched, fixing fast" velocity.

KiloCode's additions over upstream OpenCode:
- `@kilocode/kilo-gateway` — routes API calls through KiloCode's servers / OpenRouter
- `@kilocode/kilo-telemetry` — PostHog analytics (phc_GK2Pxl0HPj5ZPfwhLRjXrtdz8eD7e9MKnXiFrOqnB6z pointed at us.i.posthog.com), enabled by default
- Kilo Pass credit/billing system
- Migration layer from KiloCode VS Code extension
- Kilo for Slack integration

**Every single one of these additions is useless on an air-gapped network.** The
gateway can't reach KiloCode's servers. The telemetry can't phone home. The billing
system has no billing server. The Slack integration has no Slack.

**License is clean.** MIT for the OpenCode foundation, Apache 2.0 for KiloCode's layer.
KiloCode also has its own Terms of Service at kilo.ai/terms, but since you'd be running
it offline with no account, it's largely irrelevant.

**Known CLI-specific bugs:**
- GitHub issue #4998: Any model creates empty files via `write_to_file` but reports
  success (version 0.20.0)
- GitHub issue #5251: No indication of activity after checkpoints — appears frozen for
  30+ seconds, then suddenly resumes (version 0.24.0)
- GitHub issue #3323: Empty model field in CLI API requests
- GitHub issue #927: Local models fail to invoke tools, context truncated to 4,096
  tokens instead of the model's actual limit, XML tool tags not recognized — leads to
  infinite loops

### The Realization

If KiloCode CLI is just OpenCode with added telemetry, a gateway to servers we can't
reach, and a billing system we can't use — **why not just use OpenCode directly?**

This eliminated both Cline CLI 2.0 and KiloCode CLI 1.0 from consideration and moved
the investigation to OpenCode versus OpenAI Codex CLI.


---

## Round 2: OpenAI Codex CLI vs OpenCode CLI

### OpenAI Codex CLI

OpenAI Codex CLI is a Rust-based (97.6% Rust) terminal coding agent, open-sourced under
Apache 2.0. It has 30,000+ GitHub stars and 285+ contributors. It is primarily designed
as a frontend for OpenAI's GPT-5-Codex model family.

**The dealbreaker: OpenAI Codex CLI is actively deprecating the Chat Completions API.**

Per GitHub discussion #7782 on the openai/codex repository, OpenAI announced they are
removing support for the `/v1/chat/completions` protocol in favor of their proprietary
**Responses API**. The deprecation warning is already live, and in February 2026 it will
transition to a **hard error**.

This is fatal for local model use because:
- Ollama only speaks Chat Completions
- vLLM only speaks Chat Completions
- llama.cpp only speaks Chat Completions
- LM Studio only speaks Chat Completions
- Every single local model provider speaks Chat Completions
- The Responses API is an OpenAI-only protocol that no local provider implements

Building on OpenAI Codex CLI for local Devstral Small 2 on Ollama would be building on
a foundation that is actively being pulled out from under you.

**Tool calling with local models is already broken even before the deprecation:**
- GitHub issue #7517: Tool call streaming broken in version 0.64.0 with local LLM
  providers — each streaming chunk treated as a separate tool call instead of
  accumulating into one
- GitHub issue #5488: Not using tool calls properly with local LLM on Windows
- GitHub issue #7275: Tool call protocol validation errors with third-party
  OpenAI-compatible providers — Codex's conversation history management doesn't
  maintain protocol compliance
- Multiple users report they cannot get any self-hosted model working (Qwen3, gpt-oss,
  etc.)

**Stability is also rough:**
- GitHub issue #7187: Hangs indefinitely on any prompt ("Working..." forever)
- GitHub issue #7278: Codex 5.1 hangs during operation
- GitHub issue #10828: Ends turn unexpectedly — stops mid-task
- GitHub issue #10511: Randomly exits after latest update
- GitHub issue #6512: Hangs indefinitely when out of credits (no error surfaced)
- OpenAI Developer Community post titled "Codex is rapidly degrading — please take
  this seriously"

**Verdict: OpenAI Codex CLI is the wrong tool for local Devstral Small 2 on Ollama.**
It was built for OpenAI's models. Local support is a second-class citizen that is
being actively deprecated.


### OpenCode CLI

OpenCode CLI (current version 1.1.49, released February 3, 2026) is a community-driven,
MIT-licensed terminal coding agent with 95,000+ GitHub stars and 650+ contributors. It
is built in TypeScript and runs on the Bun runtime. It uses the Vercel AI SDK and
models.dev for provider integration, supporting 75+ LLM providers including local models.

**Devstral-specific fixes have already shipped.** Version 1.1.48 (January 31, 2026)
includes "Ensure Mistral ordering fixes also apply to Devstral" — fixing the message
ordering issue where Mistral/Devstral models require an assistant message between tool
results and subsequent user messages. The older GitHub issue #856 ("Devstral toolcalling
format not supported") was also closed after system prompt improvements enabled
Devstral to output compatible tool-calling formats.

**Air-gapped operation is natively supported** through environment variables:
- `OPENCODE_DISABLE_MODELS_FETCH=true` — prevents all network calls to models.dev
  (confirmed in source code at `packages/opencode/src/flag/flag.ts` and
  `packages/opencode/src/provider/models.ts`)
- `OPENCODE_MODELS_PATH=/path/to/models.json` — use a local snapshot of the model
  database instead of fetching from the internet
- A bundled `models-snapshot` is compiled into the binary as a fallback when neither
  the cache nor the network is available
- `OPENCODE_DISABLE_AUTOUPDATE=true` — prevents update checks
- `OPENCODE_DISABLE_LSP_DOWNLOAD=true` — prevents LSP binary downloads

**No telemetry in upstream OpenCode.** The PostHog telemetry that KiloCode CLI ships
is entirely KiloCode's addition — it does not exist in the upstream OpenCode codebase.
All telemetry-related code in the KiloCode fork is marked with `// kilocode_change`
comments.

**License is MIT.** No Terms of Service traps, no data rights grants.

**Chat Completions is the primary protocol and is not being deprecated.** OpenCode uses
`@ai-sdk/openai-compatible` as its default SDK for local providers. This speaks Chat
Completions natively, which is exactly what Ollama speaks.

**Auto-compaction is built in.** The compaction system at
`packages/opencode/src/session/compaction.ts` respects the model's `limit.context` from
the provider configuration and automatically triggers summarization when approaching
that limit — similar to our project's `auto_compact_threshold = 95000` in the Vibe
configuration.

**Ollama integration works via `ollama launch opencode`** (Ollama 0.15+) for zero-config
setup, or through manual configuration in `~/.config/opencode/opencode.json`:

```json
{
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "http://172.17.0.1:11434/v1"
      },
      "models": {
        "devstral-vibe": {
          "tool_call": true,
          "limit": { "context": 104000, "output": 16384 },
          "temperature": true
        }
      }
    }
  }
}
```

The context limit set here is respected by the compaction system. The model's
`limit.context` value flows through to `session/compaction.ts:33` where it governs when
auto-compaction triggers.


---

## The Bugs That Still Matter

OpenCode CLI is the clear winner, but it is not without problems. Here is an honest
accounting of every known stability issue, assessed for relevance to our specific setup
(Linux Docker containers, Ollama on docker0 bridge, Devstral Small 2, air-gapped).

### CRITICAL: Empty `tool_calls: []` Hang (GitHub issue #10630)

**Status:** OPEN (version 1.1.36, January 23, 2026)

When a local model returns a response with an empty `tool_calls: []` array (which
Ollama and vLLM sometimes produce), OpenCode enters a state where it waits forever for
tool execution results that will never arrive. First query works fine. Second and
subsequent queries hang with no response. The GPU shows utilization (the model is
ready), but OpenCode is stuck in a wait loop.

This bug has **6+ duplicate issues** (#4255, #7185, #7524, #7486, #5187, #7083) filed
over the past several months and is assigned to maintainer rekram1-node but unresolved.

**Risk for our setup:** HIGH. This is a systemic bug affecting all local model
providers. However, there are two potential mitigations:

1. Our custom Devstral Modelfile with explicit `TEMPLATE` configuration controls the
   tool-call format at the model level. If the model never returns empty
   `tool_calls: []` (either returning actual tool calls or omitting the field entirely),
   the bug should not trigger.

2. Our Docker container architecture means a hung OpenCode session does not kill the
   whole system. Users can Ctrl+C and restart within their container.

### MEDIUM: Random Hangs After Instructions (GitHub issue #2940)

**Status:** OPEN (originally filed October 2025 on version 0.14.0, still reported in
2026 versions)

OpenCode occasionally stops responding after receiving instructions — no "generating"
or "working" indicator appears. The `/compact` command sometimes fixes it, but usually
requires Ctrl+C. Suspected root cause is the internal LSP (Language Server Protocol)
process consuming CPU.

**Risk for our setup:** MEDIUM. This is intermittent and affects all providers (cloud
and local). It is not specific to Ollama or Devstral. The Ctrl+C workaround is
functional if inelegant.

### NOT RELEVANT: WSL2 Freezing (GitHub issue #11537)

**Status:** CLOSED/FIXED (February 1, 2026)

Root cause was `systemd-timesyncd` in WSL2 corrupting JavaScript timeout mechanisms.
Fix: `sudo systemctl disable systemd-timesyncd`. We run native Linux in Docker, not
WSL2. Not applicable.

### NOT RELEVANT: Windows Startup Hang (GitHub issue #11657)

**Status:** OPEN (February 1, 2026)

Windows-only issue caused by npm commands during startup. We run Linux. Not applicable.

### NOT RELEVANT: Zen Provider Hanging (GitHub issue #10088)

**Status:** OPEN (version 1.1.31, January 22, 2026)

Affects the cloud-based OpenCode Zen provider only. We use local Ollama. Not applicable.

### NOT RELEVANT: Ollama 4K Context Default (GitHub issue #5694)

**Status:** OPEN (version 1.0.164, December 2025)

Ollama defaults to 4K context, which is unusable for agentic coding. Our project
explicitly sets `num_ctx = 104000` in the Ollama model configuration and uses the
bartowski text-only GGUF of Devstral Small 2 to fit the full 104K context within 32GB
of GPU VRAM. This problem is already solved.


---

## How Our Project Already Solves the Hard Problems

This project (Vibe Web Terminal) was built to address real LLM deployment problems. Many
of the issues that make other tools struggle with local Devstral Small 2 are already
handled:

| Problem | Our Solution |
|---|---|
| Ollama defaults to 4K context | `num_ctx = 104000` in Ollama configuration |
| Ollama KV cache invalidation bug | Requires Ollama v0.14.0+ where the Go pointer receiver bug is fixed (documented in `doc/ollama_kv_cache_bug_investigation.md`) |
| Vision encoder wastes VRAM | Uses bartowski's text-only GGUF — saves ~10GB, allowing full 104K context in ~29GB on a 32GB GPU |
| Tool call JSON formatting | Custom Devstral Modelfile with proper `TEMPLATE` for Mistral tool-call format |
| Cache eviction from subagents | Subagents routed to separate provider (Mistral Cloud API or second Ollama instance) |
| Context overflow | `auto_compact_threshold = 95000` with graceful summarization before hitting the 104K limit |
| Rate limiting (Mistral Vibe CLI) | Eliminated — local Ollama has no rate limits |
| Interface lag (Mistral Vibe CLI) | Eliminated — ttyd + xterm.js is lightweight |
| Slow session resume (Mistral Vibe CLI) | Docker containers persist independently, no 615KB session files to reload |

The transition from Mistral Vibe CLI to OpenCode CLI should preserve all of these
solutions. The Ollama configuration, Modelfile, context window settings, and Docker
architecture remain unchanged. Only the CLI agent running inside each container changes.


---

## Final Comparison Matrix

| Criterion | Mistral Vibe CLI | Cline CLI 2.0 | KiloCode CLI 1.0 | OpenAI Codex CLI | OpenCode CLI |
|---|---|---|---|---|---|
| **License** | Apache 2.0 | Apache 2.0 + ToS data grab | MIT + Apache 2.0 | Apache 2.0 | **MIT, no ToS** |
| **Devstral tool calling** | Native | Poor Ollama compat | Broken on local (#927) | Broken (#7517) | **Fixed in v1.1.48** |
| **Chat Completions API** | Supported | Supported | Supported | **Being removed Feb 2026** | Supported |
| **Air-gapped support** | Works offline | Possible | Possible | Designed for cloud | **Native flags exist** |
| **Telemetry** | None | ToS data rights | PostHog (enabled by default) | Phones home to OpenAI | **None** |
| **Stalling/hanging** | Constant | Persistent freeze pattern | Loops, context drift | Hangs, random exits | Intermittent (#2940) |
| **Maturity** | ~2 months | New CLI, old core | 8 days old | 1+ years | **1.5 years, 95K stars** |
| **Local model focus** | Devstral-only | Afterthought | OpenCode underneath | Afterthought | **Primary design goal** |
| **Community** | Mistral-backed | 5M installs (VS Code) | 250K installs (VS Code) | 30K stars, OpenAI-backed | **95K stars, 650 contributors** |


---

## The Decision

**OpenCode CLI is the replacement for Mistral Vibe CLI.**

The reasoning:

1. **It is the only tool where Devstral-specific fixes have already shipped** (version
   1.1.48, January 31, 2026 — Mistral message ordering fix).

2. **It speaks the right protocol.** Chat Completions is the primary API, which is
   exactly what Ollama speaks. Unlike OpenAI Codex CLI, this protocol is not being
   deprecated.

3. **Air-gapped operation is a first-class concern**, not an afterthought.
   `OPENCODE_DISABLE_MODELS_FETCH`, `OPENCODE_MODELS_PATH`, and bundled model snapshots
   exist specifically for environments without internet access.

4. **No telemetry, no ToS traps, no data rights grants.** MIT licensed. The code is the
   contract.

5. **The remaining bugs are manageable.** The empty `tool_calls: []` hang (#10630) is
   the most serious risk, but our custom Devstral Modelfile and Docker container
   architecture provide mitigation. The intermittent random hang (#2940) is a nuisance,
   not a blocker.

6. **KiloCode CLI is literally OpenCode with bloat added.** Every KiloCode addition
   (gateway, telemetry, billing, Slack) is useless on an air-gapped network. Using
   OpenCode directly gives us the same foundation without the dead weight.

7. **OpenAI Codex CLI is on a collision course with our requirements.** The Responses
   API migration will break Ollama compatibility entirely. It is the wrong horse to bet
   on for local model use.

8. **Cline CLI has a data rights problem and a stability problem.** The ToS grants
   Cline Bot Inc. rights to your source code, and the freezing-after-terminal-commands
   pattern has been reported continuously since issue #531 through to issue #9112 (filed
   two days before this investigation).

9. **The project's existing infrastructure transfers cleanly.** The Ollama configuration,
   bartowski text-only Devstral GGUF, 104K context window, custom Modelfile, subagent
   separation, and Docker container architecture all remain unchanged. Only the CLI
   binary inside each container changes.


---

## Remaining Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Empty `tool_calls: []` hang (#10630) | High for local models generally; uncertain for our specific Modelfile | Custom Devstral `TEMPLATE` may prevent empty arrays; Docker isolation limits blast radius; Ctrl+C recovery |
| Random hang after instructions (#2940) | Medium, intermittent | `/compact` sometimes fixes it; Ctrl+C and restart within container; tmux session persists |
| Bun runtime dependency | Low (Bun is stable) | Must ensure Bun installs cleanly in Docker image; pin version |
| OpenCode project governance changes | Low | MIT license means we can fork if needed; 650+ contributors provide resilience |
| Devstral Small 2 model updates break tool format | Low | Custom Modelfile pins the template; bartowski GGUF versioned independently |


---

## References

### OpenCode CLI
- GitHub repository: https://github.com/opencode-ai/opencode (also mirrored at https://github.com/anomalyco/opencode)
- Version 1.1.48 release (Devstral fix): https://github.com/anomalyco/opencode/releases/tag/v1.1.48
- Ollama integration documentation: https://docs.ollama.com/integrations/opencode
- Ollama + OpenCode setup guide: https://github.com/p-lemonish/ollama-x-opencode

### Bug Tracker References
- OpenCode #2940 — Random hangs: https://github.com/anomalyco/opencode/issues/2940
- OpenCode #10630 — Local LLM hangs on second query: https://github.com/anomalyco/opencode/issues/10630
- OpenCode #11537 — WSL2 freezing (FIXED): https://github.com/anomalyco/opencode/issues/11537
- OpenCode #5694 — Ollama not agentic: https://github.com/anomalyco/opencode/issues/5694
- OpenCode #856 — Devstral tool format (FIXED): https://github.com/anomalyco/opencode/issues/856
- OpenCode #7488 — Mistral message ordering (FIXED in v1.1.48): https://github.com/anomalyco/opencode/issues/7488
- OpenAI Codex #7782 — Chat Completions deprecation: https://github.com/openai/codex/discussions/7782
- OpenAI Codex #7517 — Tool call streaming broken: https://github.com/openai/codex/issues/7517
- Cline #3510 — License vs ToS conflict: https://github.com/cline/cline/issues/3510
- Cline #4362 — Poor Ollama compatibility: https://github.com/cline/cline/issues/4362
- Cline #9112 — Latest version freezing: https://github.com/cline/cline/issues/9112
- KiloCode #927 — Local models fail tools: https://github.com/Kilo-Org/kilocode/issues/927
- KiloCode #4998 — Empty files bug: https://github.com/Kilo-Org/kilocode/issues/4998

### Devstral Small 2
- Mistral AI announcement: https://mistral.ai/news/devstral-2-vibe-cli
- HuggingFace model card: https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512
- Ollama model page: https://ollama.com/library/devstral

### KiloCode CLI Source Code Analysis
- KiloCode CLI repository: https://github.com/Kilo-Org/kilo
- Telemetry client (PostHog): `packages/kilo-telemetry/src/client.ts`
- Provider system: `packages/opencode/src/provider/provider.ts`
- Air-gap flags: `packages/opencode/src/flag/flag.ts`
- Model fetching: `packages/opencode/src/provider/models.ts`

### Market Context
- Kilo CLI 1.0 launch (VentureBeat): https://venturebeat.com/orchestration/kilo-cli-1-0-brings-open-source-vibe-coding-to-your-terminal-with-support
- Cline CLI 2.0 announcement: https://cline.bot/blog/announcing-cline-cli-2-0
- Tembo 2026 CLI tools comparison: https://www.tembo.io/blog/coding-cli-tools-comparison
- OpenAI Codex CLI: https://github.com/openai/codex
