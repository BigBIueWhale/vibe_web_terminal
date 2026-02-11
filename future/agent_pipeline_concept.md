# agent_pipeline: Sacrifice Compute for Accuracy

A single agent run on a complex task produces lazy, shallow results. It skims, takes shortcuts, loses focus halfway through. Give it 110 items to classify and it keyword-matches after the first 30.

The fix: **N autonomous agent runs, each exploring the same workspace, each answering one specific research question.** Each run is a full agent session with workspace access — read files, search, grep, glob. You don't feed it content. You give it a question and it goes and finds things on its own.

The tradeoff: **spend N times the compute, get N times the depth.**

---

## Two Primitives

**Read-only agent** — the common type. Used for all research, analysis, and synthesis. Cannot modify the workspace.

```python
agent_run(instructions: str) -> Path    # returns path to report file
parallel_runs(instructions: list[str]) -> list[Path]
```

**Worker agent** — for file conversion only. Can read, write, and delete files. Runs once at the start to convert PDFs/Word/Excel into text so research agents can grep and search them.

```python
agent_work(instructions: str) -> Path
```

Context from previous agents is delivered in two ways: **inlined** in the prompt (small, essential framing) or as **file paths** the agent reads itself (large output from N parallel agents).

---

## The Example: Requirement Classification

> `classify("Classify these 110 safety requirements into the 9 system functions defined in the SRS, with reasoning")`

**Why a single agent fails:** Decision fatigue after ~30 items. Starts keyword-matching instead of reasoning. Classifies "shall prevent unintended activation" under Activation instead of Protection. Same sentence structure gets different categories depending on where it appears in the list.

```python
def classify(user_query: str):

    # ── Phase 0: Convert workspace to text ──────────────────────────
    agent_work("""
        Find every file in the workspace that is not already plain text,
        markdown, CSV, or source code. Convert each to markdown:

        - PDF/Word → Markdown. Preserve all headings, tables, lists,
          numbering, and cross-references. Use page numbers as section markers.
        - Excel → CSV (UTF-8) or Markdown tables. Preserve sheet names as headers.
        - Images → Markdown. Transcribe all visible text. Describe layout.

        Same folder, same base filename, new extension. Delete originals
        after conversion. Write a manifest of what you converted.

        CRITICAL: Do not summarize. Do not skip. The converted file must
        contain every word the original contained.
    """)

    # ── Phase 1: Build the classification framework ─────────────────
    framework_path = agent_run(f"""
        CONTEXT: You are the first agent in a multi-agent research pipeline.
        Your output will be used by {"{N}"} parallel agents who will each classify
        one requirement. Your framework must be precise enough that two
        independent agents would classify the same borderline requirement
        the same way.

        USER'S QUERY: {user_query}

        INSTRUCTIONS:
        1. Find and read the requirements dataset in the workspace.
        2. Find and read the SRS or any document that defines the system
           functions / categories.
        3. For each category, write:
           - A 2-3 sentence definition of what this function IS responsible for
           - A 2-3 sentence definition of what it is NOT (common confusions)
           - 3 example requirements from the actual dataset that clearly belong here
           - The keywords that MISLEAD naive classifiers (e.g., "activate" appears
             in both Protection and Activation requirements — explain the difference)
        4. For every pair of categories that could be confused, write a
           disambiguation rule. Example: "If the requirement prevents something
           from happening, it's Protection (PTC), not Activation (PEA), even if
           it mentions the word 'activate'."

        OUTPUT FORMAT:
        Write your framework as a structured document. It will be inlined into
        the prompt of every downstream agent, so be concise but unambiguous.
    """)

    # ── Phase 2: N parallel agents, one per requirement ─────────────
    items = extract_item_ids(framework_path)

    result_paths = parallel_runs([
        f"""
        CONTEXT: You are one of {len(items)} parallel research agents. Each agent
        classifies exactly one requirement. You have access to the full workspace —
        the dataset, the SRS, everything. You are not limited to the information
        below; go read the source material to resolve any ambiguity.

        USER'S QUERY: {user_query}

        CLASSIFICATION FRAMEWORK (produced by a prior research agent):
        {framework_path.read_text()}

        YOUR ASSIGNMENT: Classify requirement {item_id}.

        INSTRUCTIONS:
        1. Find requirement {item_id} in the dataset. Read it carefully.
        2. Read the surrounding requirements (before and after) for context —
           requirements near each other often belong to the same function.
        3. Identify which category it belongs to using the framework above.
        4. If it's borderline between two categories, apply the disambiguation
           rules from the framework. If no rule covers this case, flag it.

        OUTPUT FORMAT (strict):
        REQUIREMENT: [copy the exact text]
        CATEGORY: [one category code]
        CONFIDENCE: HIGH | MEDIUM | LOW
        REASONING: [2-3 sentences explaining why this category and not the
                     most likely alternative]
        BORDERLINE: [if LOW/MEDIUM confidence, name the runner-up category
                      and what would tip the balance]
        """
        for item_id in items
    ])

    # ── Phase 3: Audit for consistency ──────────────────────────────
    # Framework inlined (small). N classification reports passed as file paths (large).
    audit_path = agent_run(f"""
        CONTEXT: You are the final agent in a multi-agent classification pipeline.
        {len(result_paths)} parallel agents each independently classified one
        requirement. Your job is quality control. You have access to the full
        workspace — the original dataset, the SRS, everything.

        USER'S QUERY: {user_query}

        CLASSIFICATION FRAMEWORK:
        {framework_path.read_text()}

        CLASSIFICATION REPORTS: Each file below contains one agent's classification
        of one requirement. Read all of them.
        {chr(10).join(str(p) for p in result_paths)}

        INSTRUCTIONS:
        1. Read every classification report.
        2. Find INCONSISTENCIES:
           - Requirements with near-identical wording classified into different categories
           - Requirements that contradict the disambiguation rules in the framework
           - Requirements marked LOW confidence — do you agree with the agent's choice?
        3. Find SYSTEMATIC ERRORS:
           - Is one category suspiciously over- or under-represented?
           - Did multiple agents misapply the same disambiguation rule?
           - Are there requirements that don't fit ANY category?
        4. Go back to the original dataset and SRS to verify your findings.

        OUTPUT FORMAT:
        SUMMARY: [total classified, breakdown by category, count of LOW confidence]

        INCONSISTENCIES FOUND:
        - [requirement ID]: classified as [X], should be [Y] because [reason]
        ...

        SYSTEMATIC ISSUES:
        - [description of pattern]
        ...

        FINAL VERDICT: [is the overall classification trustworthy, or does a
        specific subset need reclassification?]
    """)

    return audit_path
```

**Cost: 1 worker + 1 + 110 + 1 = 113 agent runs. Decision fatigue: zero. Every requirement gets a dedicated agent who can read the full dataset and SRS for context.**

---

## The Pattern Generalizes

The structure is always the same:

```
Phase 0: CONVERT    — worker agent makes workspace searchable (if needed)
Phase 1: ORIENT     — one read-only agent explores, builds a framework
Phase 2: DEEP-DIVE  — N parallel read-only agents, each answers ONE question
Phase 3: SYNTHESIZE  — one read-only agent reads all reports, checks consistency
```

Other applications: codebase security review (one agent per file), document analysis (one agent per section), vendor comparison (one agent per proposal), data validation (one agent per record), root-cause investigation (one agent per hypothesis). The pipeline shape stays the same — only the prompts change.
