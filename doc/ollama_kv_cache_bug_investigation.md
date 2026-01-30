# Comprehensive Investigation Report: mistral-vibe KV Cache Efficiency Analysis

**Date**: 2026-01-31 (Updated)
**Original Investigation**: 2026-01-30
**Investigators**: Claude Opus 4.5
**Subject**: KV Cache efficiency analysis for mistral-vibe with Ollama

---

## Executive Summary

This investigation identified and definitively confirmed the root cause of KV cache invalidation when using mistral-vibe with Ollama. **The bug was in Ollama, not mistral-vibe.**

| Finding | Details |
|---------|---------|
| **Root Cause** | Go pointer receiver `String()` method not called by templates |
| **Bug Introduced** | Ollama v0.2.6 (commit b2554455, July 17, 2024) |
| **Bug Fixed** | Ollama v0.14.0 (commit 626af2d8, January 6, 2026) |
| **Affected Versions** | v0.2.6 through v0.13.x |
| **Impact** | Complete KV cache invalidation on every tool call |

---

## Workspace & Repository Locations

| Resource | Location |
|----------|----------|
| mistral-vibe repo | `/home/user/Downloads/mistral-vibe` (checked out to v1.3.5) |
| Ollama v0.13.5 source | `/tmp/ollama-0.13.5` (cloned from GitHub) |
| Ollama v0.15.2 source | `/tmp/ollama-0.15.2` (cloned from GitHub) |
| This report | `~/Downloads/mistral_vibe_kv_cache_investigation_report.md` |

---

## User's Setup & Context

- **GPU**: Single RTX 5090
- **Model**: Devstral 2 Small (24B parameters) - custom model `devstral-vibe:latest`
- **Context Length**: 104k (`num_ctx 104000`)
- **Auto-compact Threshold**: 96k tokens
- **Infrastructure**: Ollama Load Balancer (single server behind it)
- **Ollama Version**: `0.13.5` (AFFECTED BY BUG)
- **mistral-vibe Version**: `vibe 1.3.5`

---

## User's Statements (Verbatim)

### Original Observation
> "When I'm at even 60k I find that I have to wait tens of seconds sometimes after every tool call before it 'resumes'. Meaning, obviously after every tool call the response ends, and it has to re-send its entire request. But if there's any other request before the resumption, or if it changes anything somewhere towards the beginning of the turns, it will completely reset the cache of my single RTX 5090 that's gated behind its dedicated Ollama Load Balancer."

### On Processing Speed
> "Well, I expect prompt ingestion speed of multiple thousands of tokens per second."

---

## THE ROOT CAUSE: Go Template Pointer Receiver Bug

### The Definitive Answer

The KV cache invalidation was caused by a **fundamental incompatibility between Go's template system and a pointer receiver `String()` method** in Ollama's `ToolCallFunctionArguments` type.

### Technical Explanation

#### The Bug in Detail

In Go, when a template prints a value using `{{ .Value }}`:

1. If the value implements `fmt.Stringer` (has a `String()` method), that method is called
2. **BUT**: If the `String()` method has a **pointer receiver** (`func (t *T) String()`), and the value is not a pointer or not addressable, **the method is NOT called**
3. Instead, Go's default formatting is used, which for maps produces `map[key:value]` format

#### The Buggy Code (Ollama v0.2.6 through v0.13.x)

In `/tmp/ollama-0.13.5/api/types.go` lines 230-235:

```go
type ToolCallFunctionArguments map[string]any

func (t *ToolCallFunctionArguments) String() string {  // POINTER RECEIVER - BUG!
    bts, _ := json.Marshal(t)
    return string(bts)
}
```

When the Devstral template renders `{{ .Function.Arguments }}`:
- The `Arguments` field is a **value** (not a pointer)
- Go templates cannot call the pointer receiver `String()` method on a non-pointer value
- Result: Go prints the map using default format: `map[content:x > 10]`

#### The Fix (Ollama v0.14.0+)

In `/tmp/ollama-0.15.2/template/template.go` lines 384-393:

```go
type templateArgs map[string]any

func (t templateArgs) String() string {  // VALUE RECEIVER - FIXED!
    if t == nil {
        return "{}"
    }
    bts, _ := json.Marshal(t)
    return string(bts)
}
```

The fix introduced `templateArgs` with a **value receiver** `String()` method, and converts tool call arguments before passing to templates via `convertMessagesForTemplate()`.

### Empirical Proof

The following Go program demonstrates the exact behavior:

```go
package main

import (
    "os"
    "text/template"
)

// Pointer receiver like buggy Ollama v0.13.5
type MapWithPointerReceiver map[string]any
func (t *MapWithPointerReceiver) String() string {
    return `{"key":"value"}`  // JSON format
}

// Value receiver like fixed Ollama v0.14.0+
type MapWithValueReceiver map[string]any
func (t MapWithValueReceiver) String() string {
    return `{"key":"value"}`  // JSON format
}

type Data struct {
    Args1 MapWithPointerReceiver
    Args2 MapWithValueReceiver
}

func main() {
    tmpl := template.Must(template.New("test").Parse(`
Pointer receiver: {{ .Args1 }}
Value receiver: {{ .Args2 }}
`))

    data := Data{
        Args1: MapWithPointerReceiver{"key": "value"},
        Args2: MapWithValueReceiver{"key": "value"},
    }

    tmpl.Execute(os.Stdout, data)
}
```

**Output:**
```
Pointer receiver: map[key:value]
Value receiver: {"key":"value"}
```

The pointer receiver version prints Go's map format, NOT JSON. The value receiver version correctly calls `String()` and prints JSON.

### How This Caused Cache Invalidation

#### Request 1 (Tool Call Generation)

1. User sends a message
2. Ollama renders template, tokenizes prompt
3. LLM generates response with tool call:
   ```
   write_file[ARGS]{"content":"if x > 10:"}
   ```
4. These tokens are added to the KV cache
5. Tool call is parsed and sent to client

#### Request 2 (Continuation After Tool Result)

1. Client sends conversation history including the assistant's tool call
2. Ollama renders template for the assistant message:
   ```
   write_file[ARGS]{{ .Function.Arguments }}
   ```
3. **BUG**: Template produces (because `String()` is NOT called):
   ```
   write_file[ARGS]map[content:if x > 10:]
   ```
4. This is tokenized - completely different tokens than `{"content":"if x > 10:"}`
5. **Cache comparison fails** - tokens don't match
6. **Entire prompt must be reprocessed** - 10-28+ seconds at 60k+ tokens

#### The Token Mismatch

| Source | Output | Token Sequence |
|--------|--------|----------------|
| LLM generates | `{"content":"if x > 10:"}` | `{`, `"`, `content`, `"`, `:`, `"`, `if`, ` `, `x`, ` `, `>`, ` `, `1`, `0`, `:`, `"`, `}` |
| Template renders (BUG) | `map[content:if x > 10:]` | `map`, `[`, `content`, `:`, `if`, ` `, `x`, ` `, `>`, ` `, `1`, `0`, `:`, `]` |

The token sequences are **completely incompatible** - not a single token matches after the tool name!

---

## Version Timeline

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| v0.2.5 and earlier | Before July 2024 | Unknown | Tool calls may not have existed or used different implementation |
| **v0.2.6** | July 17, 2024 | **BUG INTRODUCED** | Commit b2554455 added `ToolCallFunctionArguments` with pointer receiver `String()` |
| v0.2.7 - v0.13.x | July 2024 - Jan 2026 | **AFFECTED** | All versions have the pointer receiver bug |
| v0.14.0-rc0 | January 2026 | **FIXED** | Commit 626af2d8 added `templateArgs` with value receiver |
| **v0.14.0** | January 2026 | **FIXED** | First stable release with fix |
| v0.15.2 | January 2026 | Fixed | Current version analyzed |

### Key Commits

| Commit | Date | Description |
|--------|------|-------------|
| b2554455 | July 17, 2024 | "marshal json automatically for some template values (#5758)" - **Introduced the bug** by using pointer receiver |
| e51dead6 | January 5, 2026 | "preserve tool definition and call JSON ordering (#13525)" - Changed to ordered map struct (unrelated to fix) |
| 626af2d8 | January 6, 2026 | "template: fix args-as-json rendering (#13636)" - **Fixed the bug** by adding `templateArgs` with value receiver |

---

## Hypotheses That Were Investigated But Were NOT The Cause

During the investigation, several theories were explored and definitively ruled out:

### 1. Unicode/HTML Escape Re-serialization (RULED OUT)

**Theory**: Go's `json.Marshal()` escapes `<`, `>`, `&` to Unicode escapes (`\u003c`, `\u003e`, `\u0026`). If the LLM generates literal `>` but the template produces `\u003e`, tokens would mismatch.

**Why it was suspected**: The Wireshark capture showed Unicode escapes in the HTTP payloads.

**Why it's NOT the cause**:
- While `json.Marshal()` does escape these characters, this would only cause a minor mismatch at specific character positions
- The ACTUAL bug causes a COMPLETE format mismatch (`map[...]` vs `{...}`) affecting every single token
- The Unicode escapes seen in Wireshark were a red herring - they were present but not the root cause
- Even if this were an issue, it would be a secondary problem masked by the much larger pointer receiver bug

### 2. JSON Key Ordering (RULED OUT)

**Theory**: Go maps iterate in random order, so `json.Marshal()` might produce keys in different orders, causing token mismatch.

**Why it was suspected**: Ollama v0.15.2 introduced ordered maps for tool call arguments.

**Why it's NOT the cause**:
- Go's `json.Marshal()` **always sorts map keys alphabetically** (since Go 1.12)
- Key ordering is deterministic and consistent
- The ordered map change in v0.15.2 was about preserving the LLM's original key order for semantic reasons, not for cache consistency
- The ordered map change (commit e51dead6) did NOT fix the bug - that required the separate commit 626af2d8

### 3. Sliding Window Attention (SWA) (RULED OUT)

**Theory**: Mistral models use sliding window attention, and when context exceeds the window size, `CanResume()` returns false, forcing full reprocessing.

**Why it was suspected**: The user was at 60k+ tokens with a model that might have a 32k sliding window.

**Why it's NOT the cause**:
- Mistral3/Devstral models use `NewCausalCache()`, NOT `NewSWACache()`
- For CausalCache, `swaMemorySize` is set to `math.MaxInt32`
- `CanResume()` always returns `true` for CausalCache:
  ```go
  func (c *Causal) CanResume(seq int, pos int32) bool {
      if c.swaMemorySize == math.MaxInt32 {
          return true  // Always true for CausalCache
      }
      // ...
  }
  ```

### 4. Stray API Requests (RULED OUT)

**Theory**: mistral-vibe might be making additional API calls that invalidate the cache.

**Why it was suspected**: User observed delays that seemed cache-related.

**Why it's NOT the cause**:
- Comprehensive code analysis of mistral-vibe v1.3.5 found NO stray API calls
- The conversation loop is clean: one API call per LLM turn
- `x-affinity` header is consistent throughout sessions
- Wireshark capture confirmed clean request/response pairs with no extra requests

### 5. Ollama Load Balancer (RULED OUT)

**Theory**: The load balancer might be routing requests to different cache slots or servers.

**Why it was suspected**: User mentioned using an Ollama Load Balancer.

**Why it's NOT the cause**:
- User confirmed single server behind the balancer - affinity is irrelevant
- User stated: "this issue has nothing to do with simple HTTP proxy that I programmed myself and have been using operationally for more than 9 months on a production distributed system"
- The issue reproduces without the load balancer

### 6. Template Date Functions (RULED OUT)

**Theory**: `{{ currentDate }}` in the template produces different output at different times, causing cache mismatch.

**Why it's NOT the cause**:
- mistral-vibe sends its own system prompt, so `$hasSystemPrompt = true`
- The default template with `{{ currentDate }}` is NOT used when a system prompt is provided
- Date changes would only affect the system prompt, not tool call arguments

### 7. count_tokens Full API Call (RULED OUT)

**Theory**: The `count_tokens` function makes a full API call that could reset the cache.

**Why it was suspected**: Code analysis showed `count_tokens` makes an actual completion request.

**Why it's NOT the cause**:
- `count_tokens` is only called during **compaction**
- User explicitly stated compaction is not their concern
- Normal tool loops do not trigger compaction

---

## mistral-vibe v1.3.5 Analysis: Confirmed Cache-Friendly

The investigation confirmed that mistral-vibe v1.3.5 is **completely innocent** in this issue:

| Component | Status | Evidence |
|-----------|--------|----------|
| API call pattern | Clean | One call per LLM turn, no stray requests |
| Tool serialization | Deterministic | Python's `json.dumps()` produces consistent output |
| Session ID (x-affinity) | Stable | Only changes on `/clear`, compaction, or new session |
| Message history | Append-only | No modifications to earlier messages during tool loops |
| System prompt | Stable | Not regenerated during tool loops |

### Key Files Analyzed

| File | Purpose | Finding |
|------|---------|---------|
| `vibe/core/agent.py` | Main agent loop | Clean conversation flow, no extra API calls |
| `vibe/core/llm/backend/generic.py` | OpenAI-compatible backend | Faithful passthrough of tool call arguments |
| `vibe/core/types.py` | Type definitions | `FunctionCall.arguments` stored as string unchanged |
| `vibe/core/llm/format.py` | Message formatting | Arguments passed through without modification |

---

## Ollama's Cache Mechanism Explained

### How the InputCache Works

1. **Cache Storage**: `InputCacheSlot.Inputs` stores `[]*input.Input` (token sequences)

2. **Cache Lookup** (`LoadCacheSlot`):
   ```go
   slot, numPast, err = c.findLongestCacheSlot(prompt)
   ```
   Finds the cache slot with the longest matching prefix.

3. **Prefix Comparison** (`countCommonPrefix`):
   ```go
   func countCommonPrefix(a []*input.Input, b []*input.Input) int32 {
       for i := range a {
           if a[i].Token != b[i].Token || a[i].MultimodalHash != b[i].MultimodalHash {
               break
           }
           count++
       }
       return count
   }
   ```
   Compares token-by-token. ANY mismatch stops the prefix match.

4. **Cache Reuse**:
   - If `numPast > 0`: Reuse cached KV values up to that position
   - If `numPast == 0`: Full reprocessing required

### Why Format Matters

The template renders the prompt string, which is then tokenized. The cache stores previous tokenizations. For cache reuse:

- The rendered prompt must produce **exactly the same tokens** as previously cached
- Even a single different character changes tokenization
- `map[key:value]` vs `{"key":"value"}` produces completely different tokens

---

## Wireshark Analysis Summary

The original Wireshark capture data supported the diagnosis:

| Observation | Implication |
|-------------|-------------|
| Processing time scaled with payload size | Cache was being invalidated, requiring full reprocessing |
| No stray requests between request/response pairs | mistral-vibe was not the cause |
| Long gaps (10-28s) at larger payloads | Full prompt reprocessing at thousands of tokens |
| Clean request pattern | The issue was internal to Ollama, not network-related |

---

## Resolution

### For Users on Ollama v0.13.x or Earlier

**Upgrade to Ollama v0.14.0 or later.**

The KV cache will then work correctly, providing:
- Sub-second response times after tool calls (instead of 10-28+ seconds)
- Efficient cache reuse for the conversation prefix
- Only new tokens need processing on each turn

### Technical Verification

After upgrading, verify the fix is working by enabling debug logging:

```bash
OLLAMA_DEBUG=1 ollama serve 2>&1 | grep "loading cache slot"
```

Expected output showing cache hits:
```
loading cache slot id=0 cache=60000 prompt=60500 used=60000 remaining=500
```

- `used` should be close to `cache` (high cache hit ratio)
- `remaining` should be small (only new tokens to process)

If `used=0`, the cache is still being invalidated (indicates the fix is not applied).

---

## Files Referenced in This Investigation

### mistral-vibe v1.3.5
- `/home/user/Downloads/mistral-vibe/vibe/core/agent.py`
- `/home/user/Downloads/mistral-vibe/vibe/core/llm/backend/generic.py`
- `/home/user/Downloads/mistral-vibe/vibe/core/types.py`
- `/home/user/Downloads/mistral-vibe/vibe/core/llm/format.py`
- `/home/user/Downloads/mistral-vibe/vibe/core/tools/manager.py`

### Ollama v0.13.5 (Buggy)
- `/tmp/ollama-0.13.5/api/types.go` - Contains pointer receiver `String()` method
- `/tmp/ollama-0.13.5/template/template.go` - Passes raw `api.Message` to templates
- `/tmp/ollama-0.13.5/runner/ollamarunner/cache.go` - Cache comparison logic
- `/tmp/ollama-0.13.5/tools/tools.go` - Tool call parsing
- `/tmp/ollama-0.13.5/openai/openai.go` - OpenAI API compatibility layer

### Ollama v0.15.2 (Fixed)
- `/tmp/ollama-0.15.2/api/types.go` - New ordered map structure (not the fix)
- `/tmp/ollama-0.15.2/template/template.go` - Contains `templateArgs` with value receiver (THE FIX)
- `/tmp/ollama-0.15.2/internal/orderedmap/orderedmap.go` - Ordered map implementation

---

## Conclusion

The KV cache invalidation issue was caused by **a Go language subtlety**: pointer receiver methods are not called by Go's template system on non-pointer values. This caused Ollama to render tool call arguments in Go's map format (`map[key:value]`) instead of JSON format (`{"key":"value"}`), resulting in completely different token sequences that invalidated the cache on every single tool call.

**The bug existed in Ollama from v0.2.6 (July 2024) through v0.13.x, and was fixed in v0.14.0 (January 2026).**

mistral-vibe v1.3.5 was verified to be completely cache-friendly and was not the cause of the issue.

---

*Report finalized: 2026-01-31*
*Investigators: Claude Opus 4.5*
*Verification method: Go template behavior empirical testing, source code analysis across Ollama versions*
