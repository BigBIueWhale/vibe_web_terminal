# agent_pipeline: Prompt-to-Program Compilation

## The Core Idea

Every complex LLM prompt can be decomposed into a Python script that runs multiple focused LLM calls. The script is the orchestration. The LLM is the compute unit. Python handles the logic.

**One primitive:**
```python
agent_report(prompt: str, ctx: list[str] = []) -> str
```

**One helper for parallelism:**
```python
parallel_reports(prompts: list[str], ctx: list[str] = []) -> list[str]
```

That's it. Everything else is just Python.

---

## Example 1: Requirements Classification (N items → N agents)

**User prompt:**
> "Classify these 110 safety requirements into 9 system functions with reasoning"

**Why a single LLM call fails:**
Decision fatigue after ~30 items. Starts keyword-matching instead of thinking. Internal inconsistencies (same sentence pattern classified differently). Boundary collapse between similar categories.

**Compiled script:**
```python
from agent_pipeline import agent_report, parallel_reports
import csv

# Load data
with open("110SafetyReq.txt") as f:
    reqs = list(csv.reader(f.readlines()))[1:]  # skip header

CATS = "NAV, STD, ENG, PTC, SUP, TxDATA, RxDATA, MNTR, PEA"

# Phase 1: One agent defines functional boundaries (shared reference for all)
boundaries = agent_report(
    "Define what each function IS and IS NOT responsible for: " + CATS +
    "\nSpecifically clarify: PTC prevents unintended activation; PEA performs activation."
)

# Phase 2: 110 parallel agents, each classifying exactly ONE requirement
results = parallel_reports(
    [f"Classify this ONE requirement: '{r[1]}'\nCategories: {CATS}\n"
     f"Format: CATEGORY | reasoning | which keyword might mislead a naive classifier"
     for r in reqs],
    ctx=[boundaries]
)

# Phase 3: One audit agent checks all 110 for internal consistency
audit = agent_report(
    "Find requirements with identical structure but different classifications.\n" +
    "\n".join(f"Req {reqs[i][0]}: {results[i]}" for i in range(len(reqs))),
    ctx=[boundaries]
)

# Phase 4: Write output
for i, r in enumerate(reqs):
    print(f"{r[0]},{results[i]}")
print(f"\n--- AUDIT ---\n{audit}")
```

**Compute: 1 + 110 + 1 = 112 LLM calls. Decision fatigue: zero.**

---

## Example 2: Code Review (file-by-file analysis)

**User prompt:**
> "Review my Python project for security vulnerabilities"

**Why a single LLM call fails:**
Can't fit all files in context. Skims over later files. Misses subtle cross-file issues. Gives generic advice instead of specific findings.

**Compiled script:**
```python
from agent_pipeline import agent_report, parallel_reports
import glob

# Discover all Python files
files = glob.glob("src/**/*.py", recursive=True)
file_contents = {}
for f in files:
    with open(f) as fh:
        file_contents[f] = fh.read()

# Phase 1: One agent defines what to look for (OWASP top 10, common Python pitfalls)
checklist = agent_report(
    "List the top 20 security vulnerabilities to check for in a Python web application. "
    "For each, give a 1-line description and a code pattern to search for."
)

# Phase 2: One agent per file, each doing a thorough security review
file_reviews = parallel_reports(
    [f"Review this file for security vulnerabilities.\nFile: {name}\n```python\n{code}\n```\n"
     f"For each finding: LINE_NUMBER | SEVERITY (high/medium/low) | DESCRIPTION | FIX"
     for name, code in file_contents.items()],
    ctx=[checklist]
)

# Phase 3: Cross-file analysis (receives ALL individual reviews)
cross_file = agent_report(
    "Review these individual file reports and identify CROSS-FILE vulnerabilities "
    "(e.g., SQL injection in one file consuming unsanitized input from another file).\n\n" +
    "\n\n".join(f"=== {name} ===\n{review}"
                for (name, _), review in zip(file_contents.items(), file_reviews)),
    ctx=[checklist]
)

# Phase 4: Executive summary
summary = agent_report(
    "Write a 1-page executive summary of this security review. "
    "Total files reviewed, critical findings count, top 3 priorities.",
    ctx=[cross_file] + file_reviews
)

print(summary)
```

**Compute: 1 + N_files + 1 + 1. Each file gets full attention. Cross-file issues caught separately.**

---

## Example 3: Bug Investigation (search → hypothesize → verify)

**User prompt:**
> "Users report login fails intermittently. Find the root cause."

**Why a single LLM call fails:**
Guesses instead of investigating. Can't read files or logs itself. Proposes generic solutions without evidence.

**Compiled script:**
```python
from agent_pipeline import agent_report, parallel_reports
import subprocess

# Phase 1: Generate hypotheses
hypotheses = agent_report(
    "Intermittent login failures in a web app. Generate 5 specific hypotheses, "
    "each with: HYPOTHESIS | WHAT_FILE_TO_CHECK | WHAT_PATTERN_TO_SEARCH_FOR"
)

# Phase 2: Gather evidence (read relevant files, search for patterns)
auth_code = open("src/auth.py").read()
session_code = open("src/session.py").read()
nginx_conf = open("nginx.conf").read()
recent_logs = subprocess.getoutput("tail -200 /var/log/app/auth.log")

evidence = {
    "auth.py": auth_code,
    "session.py": session_code,
    "nginx.conf": nginx_conf,
    "recent auth logs": recent_logs
}

# Phase 3: Each agent evaluates ONE hypothesis against ALL evidence
evaluations = parallel_reports(
    [f"Evaluate this hypothesis: {h}\n\n"
     f"Evidence available:\n" +
     "\n".join(f"--- {name} ---\n{content[:3000]}" for name, content in evidence.items()) +
     f"\n\nDoes the evidence SUPPORT or REFUTE this hypothesis? "
     f"Cite specific lines. Rate confidence: HIGH/MEDIUM/LOW."
     for h in hypotheses.strip().split("\n") if h.strip()],
    ctx=[]
)

# Phase 4: Synthesize — which hypothesis has the strongest evidence?
diagnosis = agent_report(
    "Based on these evaluated hypotheses, what is the most likely root cause? "
    "Recommend a specific fix with code changes.",
    ctx=evaluations
)

print(diagnosis)
```

**Compute: 1 + 5 + 1 = 7 LLM calls. Each hypothesis gets a fair, independent evaluation.**

---

## Example 4: Large Document Summarization (chunk → summarize → synthesize)

**User prompt:**
> "Summarize this 200-page PDF into a 2-page executive brief"

**Why a single LLM call fails:**
200 pages exceeds context window. Truncates. Loses details from later sections. Summary is shallow.

**Compiled script:**
```python
from agent_pipeline import agent_report, parallel_reports

# Load and chunk the document (e.g., by section or every 5 pages)
with open("report.txt") as f:
    full_text = f.read()

# Split into ~2000-word chunks (roughly 5 pages each)
words = full_text.split()
chunks = [" ".join(words[i:i+2000]) for i in range(0, len(words), 2000)]

# Phase 1: Summarize each chunk independently (parallel)
chunk_summaries = parallel_reports(
    [f"Summarize this section in 3-5 bullet points. "
     f"Preserve specific numbers, names, dates, and conclusions.\n\n{chunk}"
     for chunk in chunks],
    system="You are a precise summarizer. Never generalize — keep specifics."
)

# Phase 2: Identify key themes across all summaries
themes = agent_report(
    "These are summaries of consecutive sections of a report. "
    "Identify the 5-7 major themes that span multiple sections.\n\n" +
    "\n\n".join(f"Section {i+1}:\n{s}" for i, s in enumerate(chunk_summaries))
)

# Phase 3: Write the executive brief (sees themes + all section summaries)
brief = agent_report(
    "Write a 2-page executive brief for this report. Structure:\n"
    "1. Purpose & Scope (1 paragraph)\n"
    "2. Key Findings (5-7 bullets with specifics)\n"
    "3. Recommendations (3-5 actionable items)\n"
    "4. Conclusion (1 paragraph)\n\n"
    "Use the themes and section summaries below. Include specific numbers and dates.",
    ctx=[themes] + chunk_summaries
)

print(brief)
```

**Compute: N_chunks + 1 + 1. Every page gets read. Nothing truncated.**

---

## Example 5: Comparative Analysis (analyze independently → compare)

**User prompt:**
> "Compare these 4 vendor proposals and recommend one"

**Why a single LLM call fails:**
Recency bias (favors the last proposal read). Loses details from earlier proposals. Makes superficial comparisons.

**Compiled script:**
```python
from agent_pipeline import agent_report, parallel_reports
import os

# Load all proposals
proposals = {}
for f in os.listdir("proposals/"):
    with open(f"proposals/{f}") as fh:
        proposals[f] = fh.read()

# Phase 1: Define evaluation criteria
criteria = agent_report(
    f"We are evaluating {len(proposals)} vendor proposals. "
    "Define 8-10 evaluation criteria with weights (must sum to 100%). "
    "Include: cost, timeline, technical capability, risk, support."
)

# Phase 2: Each proposal evaluated independently against the SAME criteria
evaluations = parallel_reports(
    [f"Evaluate this vendor proposal against the criteria below.\n\n"
     f"PROPOSAL: {name}\n{content[:5000]}\n\n"
     f"For each criterion, give a score (1-10) and a one-line justification."
     for name, content in proposals.items()],
    ctx=[criteria]
)

# Phase 3: Cross-comparison (sees ALL evaluations side by side)
comparison = agent_report(
    "Compare these vendor evaluations side-by-side. "
    "Create a comparison matrix. Identify where vendors differ most. "
    "Flag any vendor scores that seem inconsistent with the evidence.",
    ctx=[criteria] + evaluations
)

# Phase 4: Final recommendation
recommendation = agent_report(
    "Based on the weighted criteria and cross-comparison, "
    "recommend ONE vendor. State the top 3 reasons. "
    "Acknowledge the strongest competitor and why they fell short.",
    ctx=[criteria, comparison]
)

print(recommendation)
```

**Compute: 1 + 4 + 1 + 1 = 7 calls. Each proposal gets the same rigorous criteria. No recency bias.**

---

## Example 6: Test Generation (function-by-function)

**User prompt:**
> "Generate unit tests for all public functions in auth.py"

**Compiled script:**
```python
from agent_pipeline import agent_report, parallel_reports
import ast, inspect

# Parse the source to find all public functions
with open("src/auth.py") as f:
    source = f.read()

tree = ast.parse(source)
functions = [
    node for node in ast.walk(tree)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and not node.name.startswith("_")
]

# Extract each function's source code
func_sources = {}
lines = source.split("\n")
for func in functions:
    end = func.end_lineno if hasattr(func, 'end_lineno') else func.lineno + 20
    func_sources[func.name] = "\n".join(lines[func.lineno - 1:end])

# Phase 1: One agent analyzes the module's purpose and dependencies
module_analysis = agent_report(
    f"Analyze this Python module. What does it do? What are its dependencies? "
    f"What test fixtures would be needed (mock DB, fake HTTP, etc.)?\n\n```python\n{source}\n```"
)

# Phase 2: One agent per function generates tests
test_code_parts = parallel_reports(
    [f"Write pytest unit tests for this function.\n\n"
     f"Function: {name}\n```python\n{code}\n```\n\n"
     f"Include: happy path, edge cases, error cases. Use mocks where needed.\n"
     f"Output ONLY the test code, no explanation."
     for name, code in func_sources.items()],
    ctx=[module_analysis]
)

# Phase 3: Combine and verify imports
final_tests = agent_report(
    "Combine these test functions into one valid pytest file. "
    "Add necessary imports, fixtures, and a conftest.py section if needed. "
    "Ensure no duplicate imports. Output only the final Python code.",
    ctx=[module_analysis] + test_code_parts
)

with open("tests/test_auth.py", "w") as f:
    f.write(final_tests)
print(f"Generated tests for {len(func_sources)} functions → tests/test_auth.py")
```

**Compute: 1 + N_functions + 1. Each function gets thoughtful, focused test generation.**

---

## Example 7: Data Validation (row-by-row for critical data)

**User prompt:**
> "Validate these 50 medical records for consistency and flag anomalies"

**Compiled script:**
```python
from agent_pipeline import agent_report, parallel_reports
import json

with open("records.json") as f:
    records = json.load(f)

# Phase 1: Define validation rules from domain knowledge
rules = agent_report(
    "Define 15 validation rules for medical records. Examples: "
    "age must match birth date, medication doses must be within safe range, "
    "blood pressure values must be physiologically plausible, etc."
)

# Phase 2: Each record validated independently
validations = parallel_reports(
    [f"Validate this medical record against the rules. "
     f"For each rule: PASS/FAIL/NA | detail.\n\n"
     f"Record ID: {r['id']}\n{json.dumps(r, indent=2)}"
     for r in records],
    ctx=[rules]
)

# Phase 3: Pattern analysis across all records
patterns = agent_report(
    "Analyze these validation results across all 50 records. "
    "Are there systematic patterns? (e.g., same doctor always has dose errors, "
    "records from Tuesday have missing fields). Flag systemic issues.",
    ctx=validations
)

print(patterns)
```

---

## Example 8: Codebase Search (the "find the needle" problem)

**User prompt:**
> "Where in this codebase is the rate limiting logic, and does it have any bypass vulnerabilities?"

**Compiled script:**
```python
from agent_pipeline import agent_report, parallel_reports
import glob

# Gather all source files
all_files = glob.glob("src/**/*.py", recursive=True) + glob.glob("src/**/*.js", recursive=True)

# Phase 1: Quick scan — which files MIGHT contain rate limiting?
file_list = "\n".join(all_files)
candidates = agent_report(
    f"Which of these files are most likely to contain rate limiting logic? "
    f"Pick the top 10 most likely. Consider filenames, common patterns.\n\n{file_list}\n\n"
    f"Output ONLY the file paths, one per line."
)

candidate_files = [f.strip() for f in candidates.strip().split("\n") if f.strip() in all_files]

# Phase 2: Read each candidate and search for rate limiting
file_analyses = parallel_reports(
    [f"Search this file for rate limiting logic. If found, extract:\n"
     f"1. The mechanism (token bucket, sliding window, fixed window, etc.)\n"
     f"2. The limits (requests per second/minute)\n"
     f"3. What happens when limit is exceeded\n"
     f"4. Any bypass conditions (admin users, internal IPs, etc.)\n"
     f"If NOT found, say 'NO RATE LIMITING IN THIS FILE'.\n\n"
     f"File: {name}\n```\n{open(name).read()}\n```"
     for name in candidate_files]
)

# Phase 3: Synthesize findings and analyze for vulnerabilities
analysis = agent_report(
    "Based on these file analyses, describe the complete rate limiting architecture. "
    "Then analyze for bypass vulnerabilities:\n"
    "- Can an attacker rotate IPs to bypass?\n"
    "- Are there unauthenticated endpoints without rate limiting?\n"
    "- Is the rate limit applied before or after authentication?\n"
    "- Can distributed attacks exhaust the limit store?\n",
    ctx=file_analyses
)

print(analysis)
```

---

## The Pattern

Every example follows the same structure:

```
Phase 1: SETUP     — one agent defines criteria/rules/boundaries (shared context)
Phase 2: WORKERS   — N parallel agents, each handling ONE atomic unit
Phase 3: AUDIT     — one agent cross-checks all results for consistency
Phase 4: OUTPUT    — one agent assembles the final deliverable
```

The number of LLM calls scales with the **size of the input**, not the complexity of the prompt. This is the right tradeoff: spend more compute, get less laziness.

## When NOT to Use This

- Simple questions ("What does this function do?") — one call is fine
- Creative tasks with no ground truth ("Write me a poem") — parallelism doesn't help
- Tasks with <5 items — overhead isn't worth it
- Real-time / interactive use — latency matters more than accuracy

## When This Dominates

- **N-item classification/review/validation** — eliminates decision fatigue
- **Large document analysis** — overcomes context window limits
- **Cross-file codebase analysis** — each file gets full attention
- **Comparative evaluation** — eliminates recency/order bias
- **Any task where the LLM takes shortcuts when not watched**
