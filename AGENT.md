# Open Link Token Agent Registry

This file is the repo-level registry for Open Link Token's custom agent architecture. It defines which instruction layer to use, which agent owns which surface, and how documentation work should be handed off.

## Instruction Stack

| Layer                                    | Role                                         | Notes                                                                                                                                                                                      |
| ---------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `.github/copilot-instructions.md`        | Repo-wide runtime guidance for coding agents | Primary source for Open Link Token-specific rules, architecture, workflow, verification, and PR expectations. `docs/dev-guide-development.md` already points AI coding agents here.        |
| `.github/instructions/*.instructions.md` | Focused supplemental rules                   | Use for topic-specific detail such as Java, Python, Open Link Token architecture/parity, security, PRs, and commenting. Keep durable rule detail here instead of duplicating it in agents. |
| `.github/agents/*.agent.md`              | Narrow specialist agents                     | Use these to route work by surface or task type. Agents should stay concise, explicit, and strongly scoped.                                                                                |
| `.github/skills/*`                       | Process workflows                            | Use skills for how to work (planning, debugging, TDD, co-authoring, etc.). Skills guide execution; agents define ownership.                                                                |

## Agent Registry

| Agent                   | Owns                                                    | Use For                                                                       | Handoff                                                                                                                      |
| ----------------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `orchestrator`          | Routing and review sequencing                           | Mixed or unclear requests; selecting the right specialist                     | Delegates to the owning specialist, then uses `code-reviewer` as an optional follow-up when repo-specific validation matters |
| `java-coder`            | `lib/java/**` implementation work                       | Java code changes, Java tests, ServiceLoader updates, Maven/Checkstyle work   | Coordinates parity-sensitive changes with `python-coder`; hands readiness review to `code-reviewer`                          |
| `python-coder`          | `lib/python/**` and `tools/**/*.py` implementation work | Python code changes, Python tests, tool scripts, shared-venv-aware workflows  | Coordinates parity-sensitive changes with `java-coder`; hands readiness review to `code-reviewer`                            |
| `code-reviewer`         | Review concerns across repo changes                     | PR review, change review, verification/readiness checks                       | Sends doc-impact follow-up to the relevant doc owner                                                                         |
| `documentation-creator` | Root-level project-facing markdown                      | `README.md`, contributor-facing root docs, high-level project messaging       | Hands off `docs/**` and `pages/**` work                                                                                      |
| `docs-maintainer`       | `docs/**`                                               | Durable specs, developer/reference docs, behavior-aligned guidance            | Hands off repo-root summary content and site presentation                                                                    |
| `github-pages-content`  | `pages/**`                                              | GitHub Pages content, front matter, navigation, intra-site links, readability | Hands off durable reference/spec content and repo-root summaries                                                             |
| `agentic-workflows`     | `.github/workflows/**`, related gh-aw workflow docs     | gh-aw workflow authoring, debugging, upgrades, shared workflow components     | Uses gh-aw prompt routing for workflow-specific operations                                                                   |

## Documentation Ownership

| Surface                                           | Primary Owner           | Typical Content                                                             |
| ------------------------------------------------- | ----------------------- | --------------------------------------------------------------------------- |
| `README.md` and other root-level project markdown | `documentation-creator` | Overview, installation, usage, contributing, badges, top-level navigation   |
| `docs/**`                                         | `docs-maintainer`       | Durable specs, developer guides, reference docs, process docs               |
| `pages/**`                                        | `github-pages-content`  | Jekyll-rendered site pages, landing pages, section indexes, site navigation |

## Docs and Pages Handoff Rules

1. **Use the file path as the tiebreaker.** If the target file lives in `docs/`, `pages/`, or the repo root, route to that owner.
2. **Update the canonical surface first.** Durable behavior/reference changes belong in `docs/**`; public site presentation belongs in `pages/**`; project summary/orientation belongs in repo-root markdown.
3. **Coordinate cross-surface changes explicitly.**
   - Behavior or CLI change: `docs-maintainer` updates durable docs; `github-pages-content` updates public guidance if needed; `documentation-creator` updates root summaries only when entrypoints or top-level positioning changed.
   - New feature landing page or onboarding change: `github-pages-content` or `documentation-creator` leads depending on surface, with `docs-maintainer` updating durable details if behavior/reference changed.
4. **Do not collapse specialties.** Orchestrator routes; specialists own their surfaces.
5. **Use review as a follow-up step when appropriate.** After a specialist changes repo instructions, agent definitions, workflows, or behavior-adjacent docs, route the result through `code-reviewer` for repo-specific validation and verification expectations.

## Maintenance Guidance

- Keep agent files short, explicit, and surface-first.
- Put durable coding rules in `.github/copilot-instructions.md` or `.github/instructions/*.instructions.md`, not in every agent.
- When adding or removing an agent, update this registry and the orchestrator's routing map.
- When mirrored Java/Python behavior changes, make the orchestrator handoff explicit so both language agents stay aligned.
- If two agents seem to overlap, narrow the boundary by path and intended audience rather than adding duplicate guidance.
