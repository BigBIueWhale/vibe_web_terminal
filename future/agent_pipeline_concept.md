# agent_pipeline: Sacrifice Compute for Accuracy

## The Core Idea

A single LLM call on a complex task produces lazy, shallow results. The model skims, takes shortcuts, loses focus halfway through.

The fix: **N focused agents, each seeing everything, each answering one specific question.**

Every agent gets the full contents — the entire codebase, the entire document, all the data. Nothing is pre-filtered, chunked, or extracted. The only thing that differs between agents is the **research question** they're instructed to answer. This means each agent can follow references, discover cross-cutting concerns, and trace connections that a snippet-fed agent would miss.

The tradeoff is explicit: **spend N times the compute, get N times the depth.**

---

## The Primitive

```python
agent_report(question: str, material: str, briefing: str) -> str
```

- `question` — the specific research question this agent must answer
- `material` — the full, unabridged content (entire codebase, full document, all records)
- `briefing` — orientation context: what we're researching, why, what the user asked, what the material is

Every agent receives the same `material` and `briefing`. Only the `question` changes.

**Parallelism helper:**
```python
parallel_reports(questions: list[str], material: str, briefing: str) -> list[str]
```

That's it. Everything else is just Python.

---

## Pipeline Type 1: N-Item Classification

**Accepts:** a user query about classifying/categorizing a dataset

**Example invocation:**
> `classify("Classify these 110 safety requirements into 9 system functions with reasoning")`

**Why a single LLM call fails:**
Decision fatigue after ~30 items. Keyword-matching replaces thinking. Internal inconsistencies. Boundary collapse between similar categories.

**The pipeline:**

```python
def classify(user_query: str):
    # Load the full dataset — every agent will see ALL of it
    material = load_material()  # e.g., read the CSV, the spec, everything

    briefing = f"""
    USER'S RESEARCH QUESTION: {user_query}

    WHAT YOU'RE LOOKING AT: A dataset of items that need classification.
    The full dataset is provided below so you can see patterns, compare
    similar items, and understand the overall structure.
    """

    # Phase 1: One agent defines the classification framework
    framework = agent_report(
        question=(
            "Read the entire dataset. Define clear boundaries for each category. "
            "For ambiguous boundaries, state what goes WHERE and WHY. "
            "Give 2-3 examples per category from the actual data."
        ),
        material=material,
        briefing=briefing,
    )

    # Phase 2: N parallel agents, each classifying ONE item
    # Each agent sees the FULL dataset (for comparison) but is asked about ONE item
    items = extract_item_ids(material)
    results = parallel_reports(
        questions=[
            f"Focus on item: {item_id}\n"
            f"Classify this ONE item. You can see the full dataset — use other items "
            f"as reference points. Explain your reasoning. Flag if this item is a "
            f"borderline case and what the runner-up category would be."
            for item_id in items
        ],
        material=material,
        briefing=briefing + f"\n\nCLASSIFICATION FRAMEWORK:\n{framework}",
    )

    # Phase 3: One audit agent checks everything for consistency
    audit = agent_report(
        question=(
            "Review all classification results below. Find items with similar "
            "wording that were classified differently. Find items that seem "
            "miscategorized. Flag systematic errors. Propose corrections.\n\n"
            + format_results(items, results)
        ),
        material=material,
        briefing=briefing + f"\n\nCLASSIFICATION FRAMEWORK:\n{framework}",
    )

    return format_results(items, results) + "\n\n--- AUDIT ---\n" + audit
```

**Compute: 1 + N + 1. Every classification decision is made by an agent that can see all the other items for comparison.**

---

## Pipeline Type 2: Codebase Analysis

**Accepts:** any user query about understanding, reviewing, or investigating a codebase

**Example invocations:**
> `codebase_analysis("Review this project for security vulnerabilities")`
> `codebase_analysis("Where is the rate limiting logic and does it have bypass vulnerabilities?")`
> `codebase_analysis("Users report login fails intermittently. Find the root cause.")`

**Why a single LLM call fails:**
Can't fit all files. Skims later files. Misses cross-file data flows. Gives generic advice instead of specific findings.

**The pipeline:**

```python
def codebase_analysis(user_query: str):
    # Load EVERYTHING — every agent sees the full codebase
    material = load_all_source_files()  # concatenated, with file headers

    briefing = f"""
    USER'S RESEARCH QUESTION: {user_query}

    WHAT YOU'RE LOOKING AT: The complete source code of a software project.
    Every source file is included below. You have full visibility into the
    architecture, data flow, dependencies, and configuration.
    """

    # Phase 1: Orientation — one agent maps the territory
    orientation = agent_report(
        question=(
            "Survey the entire codebase. Produce a structural map:\n"
            "- What does this project do?\n"
            "- What are the major components/modules?\n"
            "- What are the entry points?\n"
            "- What are the key data flows?\n"
            "- Which files are most relevant to the user's query?"
        ),
        material=material,
        briefing=briefing,
    )

    # Phase 2: N parallel deep-dive agents
    # Each agent sees the FULL codebase but investigates ONE specific angle
    files = extract_file_names(material)
    deep_dives = parallel_reports(
        questions=[
            f"Focus your investigation on: {filename}\n"
            f"You have the complete codebase — use other files to understand "
            f"how data flows into and out of this file. Answer the user's "
            f"question specifically as it relates to this file. Trace any "
            f"cross-file dependencies you find. Cite specific line references."
            for filename in files
        ],
        material=material,
        briefing=briefing + f"\n\nCODEBASE MAP:\n{orientation}",
    )

    # Phase 3: Synthesis — one agent with all deep-dive results
    synthesis = agent_report(
        question=(
            "You have the individual file analyses below. Now answer the "
            "user's question with a complete, cross-cutting analysis. "
            "Identify patterns that span multiple files. Prioritize findings "
            "by severity/importance. Be specific — cite files and lines.\n\n"
            + format_results(files, deep_dives)
        ),
        material=material,
        briefing=briefing + f"\n\nCODEBASE MAP:\n{orientation}",
    )

    return synthesis
```

**Compute: 1 + N_files + 1. Every file gets an agent's full attention AND that agent can see all the other files for cross-referencing.**

---

## Pipeline Type 3: Document Analysis

**Accepts:** any user query about understanding, summarizing, or extracting from a large document

**Example invocations:**
> `document_analysis("Summarize this 200-page report into a 2-page executive brief")`
> `document_analysis("What are the key risk factors mentioned across all sections?")`
> `document_analysis("Does this contract contain any unusual liability clauses?")`

**Why a single LLM call fails:**
Document exceeds context window. Even if it fits, attention degrades over long inputs. The model skims later sections. Details are lost.

**The pipeline:**

```python
def document_analysis(user_query: str):
    # Load the full document — every agent sees ALL of it
    material = load_document()

    # Identify natural sections (chapters, headings, etc.)
    sections = identify_sections(material)

    briefing = f"""
    USER'S RESEARCH QUESTION: {user_query}

    WHAT YOU'RE LOOKING AT: A complete document with {len(sections)} sections.
    The full text is provided below. You can see the entire document to
    understand context, cross-references, and how sections relate to each other.
    """

    # Phase 1: One agent reads the whole thing and maps its structure
    structure = agent_report(
        question=(
            "Read the entire document. Produce a structural overview:\n"
            "- What is this document about?\n"
            "- What are the major sections and what does each cover?\n"
            "- What are the key themes that span multiple sections?\n"
            "- Which sections are most relevant to the user's query?"
        ),
        material=material,
        briefing=briefing,
    )

    # Phase 2: N parallel agents, each focused on ONE section
    # Each agent sees the FULL document but deeply analyzes one section
    section_analyses = parallel_reports(
        questions=[
            f"Focus your analysis on section: '{section_title}'\n"
            f"You have the full document for context, but deeply analyze this "
            f"section in relation to the user's query. Extract specific facts, "
            f"numbers, dates, names, conclusions. Note any references to or "
            f"from other sections."
            for section_title in sections
        ],
        material=material,
        briefing=briefing + f"\n\nDOCUMENT STRUCTURE:\n{structure}",
    )

    # Phase 3: Synthesis — one agent assembles the final answer
    final = agent_report(
        question=(
            "Using the section analyses below, produce the final answer to "
            "the user's query. Preserve specific details (numbers, dates, "
            "names). Identify cross-section patterns. Structure your answer "
            "clearly.\n\n"
            + format_results(sections, section_analyses)
        ),
        material=material,
        briefing=briefing + f"\n\nDOCUMENT STRUCTURE:\n{structure}",
    )

    return final
```

**Compute: 1 + N_sections + 1. Every section gets deep analysis from an agent that can see the full document for context.**

---

## Pipeline Type 4: Comparative Evaluation

**Accepts:** any user query about comparing, ranking, or choosing between multiple items

**Example invocations:**
> `comparative_eval("Compare these 4 vendor proposals and recommend one")`
> `comparative_eval("Which of these 3 architectural approaches is best for our scale?")`

**Why a single LLM call fails:**
Recency bias (favors the last item read). Loses details from earlier items. Makes superficial comparisons. Inconsistent criteria application.

**The pipeline:**

```python
def comparative_eval(user_query: str):
    # Load ALL items — every agent sees everything
    material = load_all_items()  # all proposals, designs, options, etc.

    items = extract_item_names(material)

    briefing = f"""
    USER'S RESEARCH QUESTION: {user_query}

    WHAT YOU'RE LOOKING AT: {len(items)} items to compare: {', '.join(items)}.
    All items are provided in full below. You can see every item to make
    fair, informed comparisons.
    """

    # Phase 1: One agent defines evaluation criteria
    criteria = agent_report(
        question=(
            "Read all items. Define 8-10 evaluation criteria with weights "
            "(must sum to 100%). The criteria should be relevant to the "
            "user's query and fair to all items. For each criterion, define "
            "what a score of 1, 5, and 10 looks like."
        ),
        material=material,
        briefing=briefing,
    )

    # Phase 2: N parallel agents, each deeply evaluating ONE item
    # Each agent sees ALL items (for fair comparison) but focuses on one
    evaluations = parallel_reports(
        questions=[
            f"Focus your evaluation on: {item_name}\n"
            f"You can see all items — use the others as reference points for "
            f"relative scoring. Evaluate this item against every criterion. "
            f"For each: score (1-10), specific evidence from the item, and "
            f"how it compares to what the other items offer."
            for item_name in items
        ],
        material=material,
        briefing=briefing + f"\n\nEVALUATION CRITERIA:\n{criteria}",
    )

    # Phase 3: Cross-comparison and recommendation
    recommendation = agent_report(
        question=(
            "Review all evaluations below. Build a comparison matrix. "
            "Identify where items differ most. Check for scoring inconsistencies. "
            "Make a final recommendation with the top 3 reasons. Acknowledge "
            "the runner-up and why they fell short.\n\n"
            + format_results(items, evaluations)
        ),
        material=material,
        briefing=briefing + f"\n\nEVALUATION CRITERIA:\n{criteria}",
    )

    return recommendation
```

**Compute: 1 + N_items + 1. Each item is evaluated by an agent who can see all the others for fair comparison. No recency bias.**

---

## Pipeline Type 5: Data Validation

**Accepts:** any user query about validating, auditing, or checking consistency of a dataset

**Example invocations:**
> `data_validation("Validate these 50 medical records for consistency and flag anomalies")`
> `data_validation("Check these financial transactions for duplicates and errors")`

**Why a single LLM call fails:**
Attention spread thin across many records. Misses subtle patterns. Applies rules inconsistently to later records.

**The pipeline:**

```python
def data_validation(user_query: str):
    # Load ALL records — every agent sees the full dataset
    material = load_dataset()

    records = extract_records(material)

    briefing = f"""
    USER'S RESEARCH QUESTION: {user_query}

    WHAT YOU'RE LOOKING AT: A dataset of {len(records)} records.
    The complete dataset is provided below. You can see all records to
    identify patterns, spot outliers, and understand what "normal" looks like.
    """

    # Phase 1: One agent defines validation rules from the data itself
    rules = agent_report(
        question=(
            "Examine the entire dataset. Define validation rules based on:\n"
            "- Domain knowledge (what values are plausible?)\n"
            "- Internal consistency (what fields should agree?)\n"
            "- Statistical norms (what's typical in this dataset?)\n"
            "For each rule, state what a violation looks like."
        ),
        material=material,
        briefing=briefing,
    )

    # Phase 2: N parallel agents, each scrutinizing ONE record
    # Each agent sees ALL records (to know what "normal" looks like)
    validations = parallel_reports(
        questions=[
            f"Focus on record: {record_id}\n"
            f"You have the full dataset — use other records as baselines. "
            f"Apply every validation rule. For each: PASS/FAIL/SUSPECT. "
            f"If FAIL or SUSPECT, explain what's wrong and what the expected "
            f"value should be based on the other records."
            for record_id in records
        ],
        material=material,
        briefing=briefing + f"\n\nVALIDATION RULES:\n{rules}",
    )

    # Phase 3: Pattern analysis across all validations
    patterns = agent_report(
        question=(
            "Review all validation results below. Look for SYSTEMATIC issues:\n"
            "- Are failures clustered by source, date, or category?\n"
            "- Are there records that are individually valid but collectively impossible?\n"
            "- What are the top 3 most critical findings?\n\n"
            + format_results(records, validations)
        ),
        material=material,
        briefing=briefing + f"\n\nVALIDATION RULES:\n{rules}",
    )

    return patterns
```

**Compute: 1 + N_records + 1. Each record is validated by an agent who can see the entire dataset for comparison.**

---

## Pipeline Type 6: Hypothesis Investigation

**Accepts:** any user query about debugging, diagnosing, or root-cause analysis

**Example invocations:**
> `investigate("Users report login fails intermittently. Find the root cause.")`
> `investigate("Why is the API response time spiking every 30 minutes?")`

**Why a single LLM call fails:**
Guesses instead of systematically investigating. Anchors on the first plausible explanation. Doesn't evaluate evidence for and against each hypothesis.

**The pipeline:**

```python
def investigate(user_query: str):
    # Load ALL evidence — logs, code, config, everything relevant
    material = load_all_evidence()

    briefing = f"""
    USER'S RESEARCH QUESTION: {user_query}

    WHAT YOU'RE LOOKING AT: All available evidence — source code, configuration
    files, logs, and any other relevant material. Everything is provided below
    so you can trace cause and effect across the full system.
    """

    # Phase 1: One agent generates hypotheses from the full evidence
    hypotheses_report = agent_report(
        question=(
            "Examine all the evidence. Generate 5-7 specific hypotheses that "
            "could explain the user's issue. For each hypothesis, state:\n"
            "- What you'd expect to see if it's TRUE\n"
            "- What you'd expect to see if it's FALSE\n"
            "- Which specific parts of the evidence to examine"
        ),
        material=material,
        briefing=briefing,
    )

    hypotheses = parse_hypotheses(hypotheses_report)

    # Phase 2: N parallel agents, each evaluating ONE hypothesis
    # Each agent sees ALL evidence but focuses on proving/disproving ONE theory
    evaluations = parallel_reports(
        questions=[
            f"Your job: evaluate this ONE hypothesis: {hypothesis}\n"
            f"You have ALL the evidence. Systematically examine it:\n"
            f"- What evidence SUPPORTS this hypothesis? (cite specific lines)\n"
            f"- What evidence CONTRADICTS it?\n"
            f"- What evidence is MISSING that would confirm or rule it out?\n"
            f"- Confidence: HIGH / MEDIUM / LOW with justification"
            for hypothesis in hypotheses
        ],
        material=material,
        briefing=briefing,
    )

    # Phase 3: Diagnosis — weigh all evaluations
    diagnosis = agent_report(
        question=(
            "Review all hypothesis evaluations below. Which hypothesis has "
            "the strongest evidence? Could multiple hypotheses be true "
            "simultaneously? Recommend a specific fix with concrete steps.\n\n"
            + format_results(hypotheses, evaluations)
        ),
        material=material,
        briefing=briefing,
    )

    return diagnosis
```

**Compute: 1 + N_hypotheses + 1. Each hypothesis gets a fair, independent, evidence-based evaluation with full visibility.**

---

## The Universal Pattern

Every pipeline follows the same structure:

```
Phase 1: ORIENT     — one agent surveys the full material, builds a framework
Phase 2: DEEP-DIVE  — N parallel agents, each sees EVERYTHING, each answers ONE question
Phase 3: SYNTHESIZE  — one agent integrates all findings into a final answer
```

Key principles:

1. **Full context, narrow focus.** Every agent gets the complete material. The only thing that varies is the question. An agent reviewing `auth.py` can see `session.py` too — and might notice the critical bug is actually in how they interact.

2. **Briefing-first.** Every agent is told: what we're researching, why, what the material is, and where things are. No agent starts cold.

3. **Pipelines are task types, not scripts.** Each pipeline accepts the user's query as input. The same `codebase_analysis()` pipeline handles security reviews, bug hunts, and architecture questions. The user's query shapes the questions; the pipeline shapes the workflow.

4. **Compute is the currency.** Each agent call costs time and tokens. The return is depth and accuracy that a single call cannot achieve — the same way a team of specialists outperforms one generalist, even though the team costs more.

## When NOT to Use This

- Simple questions ("What does this function do?") — one call is fine
- Creative tasks with no ground truth ("Write me a poem") — parallelism doesn't help
- Tasks with <5 items — overhead isn't worth it
- Real-time / interactive use — latency matters more than accuracy

## When This Dominates

- **N-item classification/review/validation** — eliminates decision fatigue
- **Large document analysis** — every section gets deep attention with full-document context
- **Cross-file codebase analysis** — each file gets an agent who can see all files
- **Comparative evaluation** — eliminates recency/order bias
- **Root-cause investigation** — each hypothesis gets independent, unbiased evaluation
- **Any task where the LLM takes shortcuts when overwhelmed by volume**
