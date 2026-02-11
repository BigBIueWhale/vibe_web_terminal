# Pipeline: Find Inconsistencies Between Requirements

```python
def find_inconsistencies(user_query: str):

    # ── Phase 0: Make workspace searchable ───────────────────────
    agent_work("""
        Convert all non-text files to markdown. Preserve everything.
        Delete originals. Same folder, same name, new extension.
    """)

    # ── Phase 1: Map the requirements landscape ─────────────────
    map_path = agent_run(f"""
        USER'S QUERY: {user_query}

        Read every requirements document in the workspace. Produce:
        1. A numbered list of every requirement (ID + one-line summary)
        2. For each requirement, list which other requirements it
           references, constrains, or could conflict with
        3. Group requirements that touch the same subsystem, parameter,
           or interface
        4. Flag any parameter that appears with different values in
           different requirements (e.g., timeout = 5s vs timeout = 10s)
    """)

    # ── Phase 2: One agent per requirement ──────────────────────
    req_ids = extract_requirement_ids(map_path)

    report_paths = parallel_runs([
        f"""
        USER'S QUERY: {user_query}

        REQUIREMENTS MAP (from a prior agent):
        {map_path.read_text()}

        YOUR ASSIGNMENT: Examine requirement {req_id} for inconsistencies
        with the rest of the requirements set.

        Go read the full requirements documents. Check for:
        - CONTRADICTIONS: another requirement demands the opposite
        - CONFLICTS: two requirements that can't both be satisfied
        - DUPLICATES: same intent, different wording (risk of diverging)
        - VALUE MISMATCHES: same parameter, different numbers
        - DANGLING REFERENCES: mentions something not defined elsewhere
        - SCOPE OVERLAPS: ambiguous which requirement governs a scenario

        For each finding, cite both requirement IDs and quote the
        conflicting text. Rate severity: CRITICAL / MAJOR / MINOR.
        If no issues found, say so — don't invent problems.
        """
        for req_id in req_ids
    ])

    # ── Phase 3: Deduplicate and prioritize ─────────────────────
    final_path = agent_run(f"""
        USER'S QUERY: {user_query}

        REQUIREMENTS MAP:
        {map_path.read_text()}

        INCONSISTENCY REPORTS: {len(report_paths)} agents each examined one
        requirement. Read all their reports:
        {chr(10).join(str(p) for p in report_paths)}

        Many agents will have found the same inconsistency from opposite
        sides (A conflicts with B, B conflicts with A). Your job:
        1. Deduplicate — merge findings about the same pair/group
        2. Verify — go read the actual requirements to confirm each finding
        3. Prioritize — rank by severity and number of agents that flagged it
        4. Summarize — group by type (contradiction, duplicate, value mismatch, etc.)

        Discard anything that doesn't hold up when you check the source.
    """)

    return final_path
```

**Cost: 1 worker + 1 + N_requirements + 1 agent runs.**

Each requirement gets a dedicated investigator who reads the full set looking for conflicts. The synthesis agent deduplicates (since A-conflicts-with-B and B-conflicts-with-A will both be reported) and verifies against source.
