---
name: remember
description: "Use when the user wants to persist a lesson learned, convention, or best practice. Syntax: `/remember [>domain [scope]] lesson`"
user-invokable: true
---

# Remember

Persist lessons learned by enhancing existing instructions, skills, or memory files — in that priority order.

## Syntax

```text
/remember [>domain [scope]] lesson content
```

- `>domain` — Optional. Target domain (e.g., `>python`, `>git-workflow`)
- `scope` — Optional. `global`, `user`, `workspace` / `ws` (default)
- Everything else is the lesson content

**Scope directories:**

| Scope              | Directory                                |
| ------------------ | ---------------------------------------- |
| `global` / `user`  | `vscode-userdata:/User/prompts/`         |
| `workspace` / `ws` | `<workspace-root>/.github/instructions/` |

**Examples:**

```text
/remember >python workspace prefer list comprehensions over map/filter
/remember >shell-scripting use arrays instead of word-splitting
/remember avoid over-escaping in sed commands
```

**Use the todo list** to track progress through the process steps.

## Process

### 1. Parse Input

Extract from the user message:

- **Domain** — text after `>` if present
- **Scope** — `global` (default) or `workspace`/`ws`
- **Lesson** — the remaining content

### 2. Discover Existing Knowledge

Search for files that already cover the lesson's domain. Check **all three tiers** in the appropriate scope:

**Tier 1 — Skills** (workspace scope only):

```text
<workspace-root>/.github/skills/*/SKILL.md
```

**Tier 2 — Instructions:**

```text
# Workspace
<workspace-root>/.github/instructions/*.instructions.md

# Global
vscode-userdata:/User/prompts/*.instructions.md
```

**Tier 3 — Memory files:**

```text
# Workspace
<workspace-root>/.github/instructions/*-memory.instructions.md
<workspace-root>/.github/instructions/memory.instructions.md

# Global
vscode-userdata:/User/prompts/*-memory.instructions.md
vscode-userdata:/User/prompts/memory.instructions.md
```

Read the top ~30 lines of each candidate to understand its domain and `applyTo` scope.

### 3. Match to Existing File

Find the best home for the lesson using this priority:

| Priority | Target                              | When                                              |
| -------- | ----------------------------------- | ------------------------------------------------- |
| 1        | Existing skill `SKILL.md`           | Lesson fits an existing skill's domain            |
| 2        | Existing `.instructions.md`         | Lesson fits an existing instruction file's domain |
| 3        | Existing `*-memory.instructions.md` | Lesson fits an existing memory file's domain      |
| 4        | New `*-memory.instructions.md`      | No existing file covers this domain               |

When uncertain about classification, ask the user.

### 4. Read Target File

Read the full target file to:

- Understand its structure and conventions
- Check for redundancy (skip if already covered)
- Find the right insertion point

### 5. Write the Lesson

**If enhancing an existing skill or instruction file:**

- Add the lesson as a new section, subsection, bullet, or code example that fits the file's existing structure
- Do not reorganize or rewrite existing content
- Keep additions minimal and focused

**If enhancing an existing memory file:**

- Add the lesson under a new `##` heading
- Follow the file's existing style

**If creating a new memory file:**

- Use this structure:

```markdown
---
description: <general domain description>
applyTo: "<glob pattern>"
---

# <Domain Name> Memory

<One-line tagline describing the domain's patterns.>

## <Lesson Title>

<Lesson content>
```

### 6. Confirm

Report what was done:

```text
✅ Remembered: <short lesson summary>
📄 File: <relative path to modified/created file>
🎯 Action: Enhanced existing <skill|instruction|memory> / Created new memory file
```

## Writing Guidelines

- Extract **general patterns** from specific instances
- Be concrete — include code examples when relevant
- Use positive framing ("use X" not "don't use Y")
- Keep entries succinct and scannable
- Avoid duplicating content already in the target file
