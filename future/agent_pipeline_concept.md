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
agent_run(instructions: str) -> str
```

Launches a full autonomous read-only agent session. The agent has access to the workspace (file read, search, grep, glob, etc.) and will explore on its own. Returns the agent's written report.

`instructions` contains:
- The user's original query (what are we researching?)
- The specific research question for this agent (what should YOU focus on?)
- Output from previous-phase agents, if any (what did earlier agents find?)

**Parallelism helper:**
```python
parallel_runs(instructions: list[str]) -> list[str]
```

That's it. Everything else is just Python.

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
    framework = agent_run(f"""
        USER'S QUERY: {user_query}

        You have access to the workspace. Find and read the dataset.
        Explore it fully. Then define clear boundaries for each category.
        For ambiguous boundaries, state what goes WHERE and WHY.
        Give 2-3 examples per category from the actual data.
    """)

    # Phase 2: N parallel agents, each classifying ONE item
    # Each agent explores the dataset independently but focuses on ONE item
    items = extract_item_ids(framework)  # parse item IDs from the framework report
    results = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

        CLASSIFICATION FRAMEWORK (from a previous research agent):
        {framework}

        YOUR TASK: Focus on item {item_id}. Find it in the dataset, read it,
        and classify it. Use the framework above. You have access to the full
        dataset — read other items if you need reference points. Explain your
        reasoning. Flag if this is a borderline case.
        """
        for item_id in items
    ])

    # Phase 3: One audit agent checks everything for consistency
    audit = agent_run(f"""
        USER'S QUERY: {user_query}

        CLASSIFICATION FRAMEWORK:
        {framework}

        CLASSIFICATION RESULTS (from {len(items)} parallel research agents):
        {format_results(items, results)}

        YOUR TASK: You have access to the original dataset — go read it.
        Find items with similar wording that were classified differently.
        Find items that seem miscategorized. Flag systematic errors.
        Propose corrections with reasoning.
    """)

    return format_results(items, results) + "\n\n--- AUDIT ---\n" + audit
```

**Cost: 1 + N + 1 agent runs. Every classification decision gets a dedicated agent that can explore the full dataset.**

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
    orientation = agent_run(f"""
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
    # Each agent can explore the FULL codebase but is directed to focus on one file
    files = extract_file_list(orientation)  # parse file paths from orientation report
    deep_dives = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

        CODEBASE MAP (from a previous research agent):
        {orientation}

        YOUR TASK: Focus your investigation on: {filename}
        Read this file thoroughly. Then trace how it connects to the rest of
        the codebase — read other files as needed to understand data flow in
        and out. Answer the user's query specifically as it relates to this
        file. Cite specific line numbers and code.
        """
        for filename in files
    ])

    # Phase 3: Synthesis — one agent integrates all findings
    synthesis = agent_run(f"""
        USER'S QUERY: {user_query}

        CODEBASE MAP:
        {orientation}

        DEEP-DIVE REPORTS (from {len(files)} parallel research agents, one per file):
        {format_results(files, deep_dives)}

        YOUR TASK: You have access to the codebase — go verify anything that
        seems off. Synthesize the deep-dive reports into a complete answer.
        Identify cross-cutting patterns that span multiple files. Prioritize
        findings by severity/importance. Cite files and lines.
    """)

    return synthesis
```

**Cost: 1 + N_files + 1 agent runs. Every file gets a dedicated agent that can also read any other file to trace cross-file dependencies.**

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
    structure = agent_run(f"""
        USER'S QUERY: {user_query}

        Find and read the document in the workspace. Produce a structural overview:
        - What is this document about?
        - What are the major sections and what does each cover?
        - What are the key themes that span multiple sections?
        - Which sections are most relevant to the user's query?
    """)

    # Phase 2: N parallel agents, each focused on ONE section
    sections = extract_sections(structure)  # parse section names from structure report
    section_analyses = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

        DOCUMENT STRUCTURE (from a previous research agent):
        {structure}

        YOUR TASK: Focus on section: '{section_title}'
        Read this section deeply. You have access to the full document — read
        other sections if you need to follow cross-references. Extract specific
        facts, numbers, dates, names, conclusions. Answer the user's query as
        it relates to this section.
        """
        for section_title in sections
    ])

    # Phase 3: Synthesis
    final = agent_run(f"""
        USER'S QUERY: {user_query}

        DOCUMENT STRUCTURE:
        {structure}

        SECTION ANALYSES (from {len(sections)} parallel research agents):
        {format_results(sections, section_analyses)}

        YOUR TASK: You have access to the original document — go verify
        anything that needs it. Synthesize the section analyses into a
        final answer. Preserve specific details. Identify cross-section
        patterns. Structure your answer clearly.
    """)

    return final
```

**Cost: 1 + N_sections + 1 agent runs. Every section gets deep analysis from an agent that can also read the rest of the document.**

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
    criteria = agent_run(f"""
        USER'S QUERY: {user_query}

        Find and read all items to be compared in the workspace.
        Define 8-10 evaluation criteria with weights (must sum to 100%).
        The criteria should be relevant to the user's query and fair to
        all items. For each criterion, define what a score of 1, 5, and
        10 looks like.
    """)

    # Phase 2: N parallel agents, each deeply evaluating ONE item
    items = extract_item_names(criteria)  # parse from criteria report
    evaluations = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

        EVALUATION CRITERIA (from a previous research agent):
        {criteria}

        YOUR TASK: Focus your evaluation on: {item_name}
        Read it thoroughly. You can also read the other items for
        comparison. Evaluate against every criterion — score (1-10),
        specific evidence, and how it compares to what others offer.
        """
        for item_name in items
    ])

    # Phase 3: Cross-comparison and recommendation
    recommendation = agent_run(f"""
        USER'S QUERY: {user_query}

        EVALUATION CRITERIA:
        {criteria}

        INDIVIDUAL EVALUATIONS (from {len(items)} parallel research agents):
        {format_results(items, evaluations)}

        YOUR TASK: Build a comparison matrix. Identify where items differ
        most. Check for scoring inconsistencies — go read the original
        items if something seems off. Make a final recommendation with
        the top 3 reasons. Acknowledge the runner-up.
    """)

    return recommendation
```

**Cost: 1 + N_items + 1 agent runs. Each item gets a dedicated evaluator who can also inspect the competition. No recency bias.**

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
    rules = agent_run(f"""
        USER'S QUERY: {user_query}

        Find and read the dataset in the workspace. Examine it fully. Define
        validation rules based on:
        - Domain knowledge (what values are plausible?)
        - Internal consistency (what fields should agree with each other?)
        - Statistical norms (what's typical in this dataset?)
        For each rule, state what a violation looks like.
    """)

    # Phase 2: N parallel agents, each scrutinizing ONE record
    records = extract_record_ids(rules)  # parse from rules report
    validations = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

        VALIDATION RULES (from a previous research agent):
        {rules}

        YOUR TASK: Focus on record: {record_id}
        Find and read this record. You have access to the full dataset —
        read other records as baselines for what "normal" looks like.
        Apply every validation rule. For each: PASS/FAIL/SUSPECT with
        evidence and reasoning.
        """
        for record_id in records
    ])

    # Phase 3: Pattern analysis across all validations
    patterns = agent_run(f"""
        USER'S QUERY: {user_query}

        VALIDATION RULES:
        {rules}

        VALIDATION RESULTS (from {len(records)} parallel research agents):
        {format_results(records, validations)}

        YOUR TASK: Go read the original dataset to verify patterns. Look
        for SYSTEMATIC issues — failures clustered by source, date, or
        category. Records individually valid but collectively impossible.
        Top 3 most critical findings.
    """)

    return patterns
```

**Cost: 1 + N_records + 1 agent runs. Each record gets a dedicated agent who can compare against the full dataset.**

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
    hypotheses_report = agent_run(f"""
        USER'S QUERY: {user_query}

        Explore the workspace — read code, config, logs, anything relevant.
        Generate 5-7 specific hypotheses that could explain the issue.
        For each hypothesis, state:
        - What you'd expect to see in the code/logs if it's TRUE
        - What you'd expect to see if it's FALSE
        - Which specific files/areas to examine
    """)

    # Phase 2: N parallel agents, each evaluating ONE hypothesis
    hypotheses = parse_hypotheses(hypotheses_report)
    evaluations = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

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
    diagnosis = agent_run(f"""
        USER'S QUERY: {user_query}

        HYPOTHESIS EVALUATIONS (from {len(hypotheses)} parallel research agents):
        {format_results(hypotheses, evaluations)}

        YOUR TASK: Go verify the strongest findings in the codebase yourself.
        Which hypothesis has the strongest evidence? Could multiple be true
        simultaneously? Recommend a specific fix with concrete steps.
    """)

    return diagnosis
```

**Cost: 1 + N_hypotheses + 1 agent runs. Each hypothesis gets an independent investigator who explores the full workspace without anchoring bias.**

---

## The Universal Pattern

Every pipeline follows the same structure:

```
Phase 1: ORIENT     — one agent explores the workspace, builds a framework/map
Phase 2: DEEP-DIVE  — N parallel agents, each explores independently, each answers ONE question
Phase 3: SYNTHESIZE  — one agent receives all reports, verifies in the workspace, produces final answer
```

Key principles:

1. **Agents explore, they aren't fed.** No data loading, no file concatenation, no chunking. Each agent is an autonomous session with full workspace access. It finds what it needs.

2. **Only reports flow between phases.** The orchestration layer passes exactly one thing between phases: the text output of previous agents. An orientation report. A classification framework. A set of hypotheses. That's the only "context" — everything else the agent discovers on its own.

3. **Pipelines are task types, not scripts.** Each pipeline accepts the user's query as input. The same `codebase_analysis()` handles security reviews, bug hunts, and architecture questions. The user's query shapes the questions; the pipeline shapes the workflow.

4. **Compute is the currency.** Each agent run costs real time and resources. The return is depth and accuracy that a single run cannot achieve — the same way a team of specialists outperforms one generalist, even though the team costs more.

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
