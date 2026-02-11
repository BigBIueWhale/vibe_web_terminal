# agent_pipeline: Sacrifice Compute for Accuracy

## The Core Idea

A single agent run on a complex task produces lazy, shallow results. The agent skims, takes shortcuts, loses focus halfway through.

The fix: **N autonomous agent runs, each exploring the same workspace, each answering one specific research question.**

Each agent run is a full autonomous session — it can read files, search code, explore the filesystem, follow references. You don't feed it content. You give it a question and it **goes and finds things on its own.** The only additional input an agent receives (beyond what it discovers through its own tools) is **the output from previous-phase agents** — an orientation report, a classification framework, a set of hypotheses.

The orchestration layer does no data loading, no file reading, no chunking. It just routes questions and passes reports between phases.

The tradeoff is explicit: **spend N times the compute, get N times the depth.**

---

## The Primitive

```python
agent_run(instructions: str) -> Path
```

Launches a full autonomous read-only agent session. The agent has access to the workspace (file read, search, grep, glob, etc.) and will explore on its own. Writes its report to a file and **returns the file path.**

**Parallelism helper:**
```python
parallel_runs(instructions: list[str]) -> list[Path]
```

That's it. Everything else is just Python.

---

## Context Delivery: Inline vs File Reference

Agent outputs are files. When passing context from one phase to the next, the orchestrator chooses **per-context** how to deliver it:

**Inline** — read the file, embed the text directly in the prompt:
```python
framework_path = agent_run(...)
# Small output from 1 agent — inline it
instructions = f"""
    CLASSIFICATION FRAMEWORK:
    {framework_path.read_text()}
"""
```

**File reference** — just give the filename, the agent reads it itself:
```python
result_paths = parallel_runs(...)  # 110 reports
# Large output from N agents — give filenames, agent reads them
instructions = f"""
    CLASSIFICATION RESULTS: Read the {len(result_paths)} report files:
    {chr(10).join(str(p) for p in result_paths)}
"""
```

**When to use which:**

| Context | Delivery | Why |
|---|---|---|
| Framework from 1 agent | **Inline** | Small, agent needs it immediately to understand its task |
| Orientation/map from 1 agent | **Inline** | Small, provides essential framing |
| N reports from parallel agents | **File ref** | Too large to inline; agent reads what it needs |
| Aggregated results for audit | **File ref** | Could be massive; agent can search/scan selectively |
| User's original query | **Inline** | Always small, always essential |

The rule of thumb: **inline what's small and essential to framing the task. File-reference what's large or what the agent might only need to selectively read.**

---

## Pipeline Type 1: N-Item Classification

**Accepts:** a user query about classifying/categorizing a dataset

**Example invocation:**
> `classify("Classify these 110 safety requirements into 9 system functions with reasoning")`

**Why a single agent run fails:**
Decision fatigue after ~30 items. Keyword-matching replaces thinking. Internal inconsistencies. Boundary collapse between similar categories.

**The pipeline:**

```python
def classify(user_query: str):

    # Phase 1: One agent explores the data and defines the classification framework
    framework_path = agent_run(f"""
        USER'S QUERY: {user_query}

        You have access to the workspace. Find and read the dataset.
        Explore it fully. Then define clear boundaries for each category.
        For ambiguous boundaries, state what goes WHERE and WHY.
        Give 2-3 examples per category from the actual data.
    """)

    # Phase 2: N parallel agents, each classifying ONE item
    # Framework is inlined (small, essential). Each agent explores the dataset on its own.
    items = extract_item_ids(framework_path)
    result_paths = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

        CLASSIFICATION FRAMEWORK (from a previous research agent):
        {framework_path.read_text()}

        YOUR TASK: Focus on item {item_id}. Find it in the dataset, read it,
        and classify it. Use the framework above. You have access to the full
        dataset — read other items if you need reference points. Explain your
        reasoning. Flag if this is a borderline case.
        """
        for item_id in items
    ])

    # Phase 3: One audit agent checks everything for consistency
    # Framework inlined (small). 110 classification reports passed as file references (large).
    audit_path = agent_run(f"""
        USER'S QUERY: {user_query}

        CLASSIFICATION FRAMEWORK:
        {framework_path.read_text()}

        CLASSIFICATION RESULTS: {len(result_paths)} parallel agents each classified
        one item. Read their reports:
        {chr(10).join(str(p) for p in result_paths)}

        YOUR TASK: Read the classification reports above, then go read the
        original dataset. Find items with similar wording that were classified
        differently. Find items that seem miscategorized. Flag systematic errors.
        Propose corrections with reasoning.
    """)

    return audit_path
```

**Cost: 1 + N + 1 agent runs. Framework inlined to every worker (small, essential). 110 results passed as files to the auditor (large, selectively read).**

---

## Pipeline Type 2: Codebase Analysis

**Accepts:** any user query about understanding, reviewing, or investigating a codebase

**Example invocations:**
> `codebase_analysis("Review this project for security vulnerabilities")`
> `codebase_analysis("Where is the rate limiting logic and does it have bypass vulnerabilities?")`
> `codebase_analysis("Users report login fails intermittently. Find the root cause.")`

**Why a single agent run fails:**
Even an autonomous agent loses focus over a large codebase. It skims later files. Anchors on the first thing it finds. Misses cross-file data flows because it stops exploring too early.

**The pipeline:**

```python
def codebase_analysis(user_query: str):

    # Phase 1: Orientation — one agent maps the territory
    orientation_path = agent_run(f"""
        USER'S QUERY: {user_query}

        Explore the entire codebase. Produce a structural map:
        - What does this project do?
        - What are the major components/modules?
        - What are the entry points?
        - What are the key data flows?
        - List every source file you find and its purpose.
        - Which files are most relevant to the user's query and why?
    """)

    # Phase 2: N parallel deep-dive agents, one per file
    # Orientation inlined (small, essential framing for where to look)
    files = extract_file_list(orientation_path)
    deep_dive_paths = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

        CODEBASE MAP (from a previous research agent):
        {orientation_path.read_text()}

        YOUR TASK: Focus your investigation on: {filename}
        Read this file thoroughly. Then trace how it connects to the rest of
        the codebase — read other files as needed to understand data flow in
        and out. Answer the user's query specifically as it relates to this
        file. Cite specific line numbers and code.
        """
        for filename in files
    ])

    # Phase 3: Synthesis
    # Orientation inlined (small). Deep-dive reports passed as files (large).
    synthesis_path = agent_run(f"""
        USER'S QUERY: {user_query}

        CODEBASE MAP:
        {orientation_path.read_text()}

        DEEP-DIVE REPORTS: {len(deep_dive_paths)} parallel agents each investigated
        one file. Read their reports:
        {chr(10).join(str(p) for p in deep_dive_paths)}

        YOUR TASK: Read the deep-dive reports, then go verify anything that
        seems off in the actual codebase. Synthesize into a complete answer.
        Identify cross-cutting patterns that span multiple files. Prioritize
        findings by severity/importance. Cite files and lines.
    """)

    return synthesis_path
```

**Cost: 1 + N_files + 1 agent runs. Every file gets a dedicated investigator. The synthesis agent reads all reports from disk, can verify in the codebase.**

---

## Pipeline Type 3: Document Analysis

**Accepts:** any user query about understanding, summarizing, or extracting from a large document

**Example invocations:**
> `document_analysis("Summarize this 200-page report into a 2-page executive brief")`
> `document_analysis("What are the key risk factors mentioned across all sections?")`
> `document_analysis("Does this contract contain any unusual liability clauses?")`

**Why a single agent run fails:**
Attention degrades over long documents. The agent skims later sections. Cross-references are missed. Details are lost.

**The pipeline:**

```python
def document_analysis(user_query: str):

    # Phase 1: One agent reads and maps the document's structure
    structure_path = agent_run(f"""
        USER'S QUERY: {user_query}

        Find and read the document in the workspace. Produce a structural overview:
        - What is this document about?
        - What are the major sections and what does each cover?
        - What are the key themes that span multiple sections?
        - Which sections are most relevant to the user's query?
    """)

    # Phase 2: N parallel agents, each focused on ONE section
    # Structure inlined (small, essential for knowing where your section fits)
    sections = extract_sections(structure_path)
    section_paths = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

        DOCUMENT STRUCTURE (from a previous research agent):
        {structure_path.read_text()}

        YOUR TASK: Focus on section: '{section_title}'
        Read this section deeply. You have access to the full document — read
        other sections if you need to follow cross-references. Extract specific
        facts, numbers, dates, names, conclusions. Answer the user's query as
        it relates to this section.
        """
        for section_title in sections
    ])

    # Phase 3: Synthesis
    # Structure inlined. Section analyses passed as files.
    final_path = agent_run(f"""
        USER'S QUERY: {user_query}

        DOCUMENT STRUCTURE:
        {structure_path.read_text()}

        SECTION ANALYSES: {len(section_paths)} parallel agents each analyzed
        one section. Read their reports:
        {chr(10).join(str(p) for p in section_paths)}

        YOUR TASK: Read the section analyses, then go verify in the original
        document as needed. Synthesize into a final answer. Preserve specific
        details. Identify cross-section patterns. Structure your answer clearly.
    """)

    return final_path
```

**Cost: 1 + N_sections + 1 agent runs. Every section gets a dedicated analyst. Synthesis agent reads all section reports from disk.**

---

## Pipeline Type 4: Comparative Evaluation

**Accepts:** any user query about comparing, ranking, or choosing between multiple items

**Example invocations:**
> `comparative_eval("Compare these 4 vendor proposals and recommend one")`
> `comparative_eval("Which of these 3 architectural approaches is best for our scale?")`

**Why a single agent run fails:**
Recency bias — the agent favors whatever it read last. Inconsistent criteria application across items. Superficial comparisons.

**The pipeline:**

```python
def comparative_eval(user_query: str):

    # Phase 1: One agent surveys all items and defines evaluation criteria
    criteria_path = agent_run(f"""
        USER'S QUERY: {user_query}

        Find and read all items to be compared in the workspace.
        Define 8-10 evaluation criteria with weights (must sum to 100%).
        The criteria should be relevant to the user's query and fair to
        all items. For each criterion, define what a score of 1, 5, and
        10 looks like.
    """)

    # Phase 2: N parallel agents, each deeply evaluating ONE item
    # Criteria inlined (small, essential for consistent scoring)
    items = extract_item_names(criteria_path)
    eval_paths = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

        EVALUATION CRITERIA (from a previous research agent):
        {criteria_path.read_text()}

        YOUR TASK: Focus your evaluation on: {item_name}
        Read it thoroughly. You can also read the other items for
        comparison. Evaluate against every criterion — score (1-10),
        specific evidence, and how it compares to what others offer.
        """
        for item_name in items
    ])

    # Phase 3: Cross-comparison and recommendation
    # Criteria inlined. Individual evaluations passed as files.
    recommendation_path = agent_run(f"""
        USER'S QUERY: {user_query}

        EVALUATION CRITERIA:
        {criteria_path.read_text()}

        INDIVIDUAL EVALUATIONS: {len(eval_paths)} parallel agents each evaluated
        one item. Read their reports:
        {chr(10).join(str(p) for p in eval_paths)}

        YOUR TASK: Read the evaluation reports. Build a comparison matrix.
        Identify where items differ most. Check for scoring inconsistencies —
        go read the original items if something seems off. Make a final
        recommendation with the top 3 reasons. Acknowledge the runner-up.
    """)

    return recommendation_path
```

**Cost: 1 + N_items + 1 agent runs. Each evaluator gets criteria inlined for consistency. Final agent reads all evaluations from disk.**

---

## Pipeline Type 5: Data Validation

**Accepts:** any user query about validating, auditing, or checking consistency of a dataset

**Example invocations:**
> `data_validation("Validate these 50 medical records for consistency and flag anomalies")`
> `data_validation("Check these financial transactions for duplicates and errors")`

**Why a single agent run fails:**
Attention spread thin across many records. Inconsistent rule application. Misses subtle patterns in later records.

**The pipeline:**

```python
def data_validation(user_query: str):

    # Phase 1: One agent explores the dataset and defines validation rules
    rules_path = agent_run(f"""
        USER'S QUERY: {user_query}

        Find and read the dataset in the workspace. Examine it fully. Define
        validation rules based on:
        - Domain knowledge (what values are plausible?)
        - Internal consistency (what fields should agree with each other?)
        - Statistical norms (what's typical in this dataset?)
        For each rule, state what a violation looks like.
    """)

    # Phase 2: N parallel agents, each scrutinizing ONE record
    # Rules inlined (small, essential for consistent validation)
    records = extract_record_ids(rules_path)
    validation_paths = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

        VALIDATION RULES (from a previous research agent):
        {rules_path.read_text()}

        YOUR TASK: Focus on record: {record_id}
        Find and read this record. You have access to the full dataset —
        read other records as baselines for what "normal" looks like.
        Apply every validation rule. For each: PASS/FAIL/SUSPECT with
        evidence and reasoning.
        """
        for record_id in records
    ])

    # Phase 3: Pattern analysis across all validations
    # Rules inlined. Validation reports passed as files.
    patterns_path = agent_run(f"""
        USER'S QUERY: {user_query}

        VALIDATION RULES:
        {rules_path.read_text()}

        VALIDATION RESULTS: {len(validation_paths)} parallel agents each validated
        one record. Read their reports:
        {chr(10).join(str(p) for p in validation_paths)}

        YOUR TASK: Read the validation reports, then go read the original
        dataset to verify patterns. Look for SYSTEMATIC issues — failures
        clustered by source, date, or category. Records individually valid
        but collectively impossible. Top 3 most critical findings.
    """)

    return patterns_path
```

**Cost: 1 + N_records + 1 agent runs. Rules inlined to every validator for consistency. All validation reports passed as files to pattern analyzer.**

---

## Pipeline Type 6: Hypothesis Investigation

**Accepts:** any user query about debugging, diagnosing, or root-cause analysis

**Example invocations:**
> `investigate("Users report login fails intermittently. Find the root cause.")`
> `investigate("Why is the API response time spiking every 30 minutes?")`

**Why a single agent run fails:**
Anchors on the first plausible explanation. Stops exploring once it has "an answer." Doesn't systematically evaluate evidence for and against each theory.

**The pipeline:**

```python
def investigate(user_query: str):

    # Phase 1: One agent explores everything and generates hypotheses
    hypotheses_path = agent_run(f"""
        USER'S QUERY: {user_query}

        Explore the workspace — read code, config, logs, anything relevant.
        Generate 5-7 specific hypotheses that could explain the issue.
        For each hypothesis, state:
        - What you'd expect to see in the code/logs if it's TRUE
        - What you'd expect to see if it's FALSE
        - Which specific files/areas to examine
    """)

    # Phase 2: N parallel agents, each evaluating ONE hypothesis
    # Hypotheses report inlined (small, and each agent needs to see
    # its own hypothesis plus the others for context)
    hypotheses = parse_hypotheses(hypotheses_path)
    eval_paths = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

        ALL HYPOTHESES (from a previous research agent):
        {hypotheses_path.read_text()}

        YOUR TASK: Evaluate this ONE hypothesis: {hypothesis}

        Explore the workspace — read code, config, logs, anything relevant.
        Systematically look for evidence:
        - What SUPPORTS this hypothesis? (cite specific files and lines)
        - What CONTRADICTS it?
        - What's MISSING that would confirm or rule it out?
        - Confidence: HIGH / MEDIUM / LOW with justification
        """
        for hypothesis in hypotheses
    ])

    # Phase 3: Diagnosis — weigh all evaluations
    # Hypotheses inlined (small). Evaluation reports passed as files.
    diagnosis_path = agent_run(f"""
        USER'S QUERY: {user_query}

        HYPOTHESES:
        {hypotheses_path.read_text()}

        HYPOTHESIS EVALUATIONS: {len(eval_paths)} parallel agents each investigated
        one hypothesis. Read their reports:
        {chr(10).join(str(p) for p in eval_paths)}

        YOUR TASK: Read the evaluation reports. Go verify the strongest
        findings in the codebase yourself. Which hypothesis has the strongest
        evidence? Could multiple be true simultaneously? Recommend a specific
        fix with concrete steps.
    """)

    return diagnosis_path
```

**Cost: 1 + N_hypotheses + 1 agent runs. Each investigator explores independently. Diagnosis agent reads all evaluation reports from disk and verifies.**

---

## The Universal Pattern

Every pipeline follows the same structure:

```
Phase 1: ORIENT     — one agent explores the workspace, builds a framework/map
Phase 2: DEEP-DIVE  — N parallel agents, each explores independently, each answers ONE question
Phase 3: SYNTHESIZE  — one agent reads all reports, verifies in the workspace, produces final answer
```

Key principles:

1. **Agents explore, they aren't fed.** No data loading, no file concatenation, no chunking. Each agent is an autonomous session with full workspace access. It finds what it needs.

2. **Only reports flow between phases.** The orchestration layer passes exactly one thing between phases: the file output of previous agents. An orientation report. A classification framework. A set of hypotheses.

3. **Context delivery is a choice.** Small, essential framing (a framework, a set of criteria) is inlined in the prompt — the agent has it immediately. Large bodies of work (N parallel reports) are passed as file references — the agent reads them from disk, selectively if needed. This keeps prompts focused while allowing massive volumes of prior-agent output.

4. **Pipelines are task types, not scripts.** Each pipeline accepts the user's query as input. The same `codebase_analysis()` handles security reviews, bug hunts, and architecture questions. The user's query shapes the questions; the pipeline shapes the workflow.

5. **Compute is the currency.** Each agent run costs real time and resources. The return is depth and accuracy that a single run cannot achieve — the same way a team of specialists outperforms one generalist, even though the team costs more.

## When NOT to Use This

- Simple questions ("What does this function do?") — one agent run is fine
- Creative tasks with no ground truth ("Write me a poem") — parallelism doesn't help
- Tasks with <5 items — overhead isn't worth it
- Real-time / interactive use — latency matters more than accuracy

## When This Dominates

- **N-item classification/review/validation** — eliminates decision fatigue
- **Large document analysis** — every section gets a dedicated investigator
- **Cross-file codebase analysis** — each file gets an agent who can also explore the rest
- **Comparative evaluation** — eliminates recency/order bias
- **Root-cause investigation** — each hypothesis gets an independent, unbiased investigator
- **Any task where a single agent takes shortcuts because the job is too big**
