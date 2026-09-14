# Decision records

Short notes recording decisions that extend or contradict the three design documents
(`functional_design.md`, `architecture.md`, `technical_design.md`).

The design documents describe the agreed design and should stay readable as a coherent whole.
When implementation forces a choice that those documents didn't anticipate — or that goes
against what they say — the reasoning goes here rather than being folded silently into them.

Write one when a decision would surprise someone who had read only the design documents, or
when it closes off an option those documents deliberately left open. Routine implementation
choices don't need one.

```bash
cp docs/decisions/template.md docs/decisions/0002-short-slug.md
```

Records are numbered sequentially and never renumbered. A record is never edited to reverse
its decision; instead a new record supersedes it and says so.

| # | Decision | Status |
| --- | --- | --- |
| [0001](0001-local-enforcement-of-main-protection.md) | Enforce main protection locally rather than on GitHub | Accepted |
| [0002](0002-manage-the-host-with-ansible.md) | Manage the host with Ansible, with secrets in ansible-vault | Accepted |
| [0003](0003-visual-direction-atelier-sage.md) | Visual direction: Atelier Sage | Accepted |
| [0004](0004-deliver-mail-directly-rather-than-through-a-smarthost.md) | Deliver mail directly rather than through a smarthost | Accepted |
