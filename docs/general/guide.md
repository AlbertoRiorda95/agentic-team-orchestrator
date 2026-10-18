
# 1. Core concepts {#concetti-di-base}


## Before you start: do you really need this? {#ti-serve-davvero}

An honest question before everything else: for one person working on a medium-sized web app, **Claude Code used well in a single session already gives you most of the value**. The architectures in this guide add real benefits, but only in a few specific cases, and they come with a setup and coordination cost.

**Where the gain is real:**

-   **Work that moves forward while you are away** (architectures C, D, E, F). You create five tasks in the evening and find five PRs in the morning. It is not better quality, it is throughput: it matters if your limit is the time you spend at the terminal.
-   **Review from an independent context.** An agent that reviews or attacks code it did not write (the designer in review, the security agent, the review in CI) finds things the author does not see.
-   **Per-role protections.** A devops agent that cannot apply anything, a security agent that cannot change code or leave its scope. In a single session the rules apply to everything, or to nothing.

**Where the gain is doubtful:**

-   **The "specialists".** The model is the same: a role does not know more about frontend, it just has a narrower scope and more precise instructions. It is discipline, not expertise.
-   **The savings.** Using several models saves 10--20% in the best case (section 2.8); coordination, on the other hand, costs extra tokens, and agent teams use 2.5--4 times as much as a single session.
-   **Overall speed.** More agents produce more PRs, but there is still one person reviewing them. And parallel work brings problems a single session does not have: frontend and backend drifting apart, concurrent tasks, waiting for CI. A good part of sections 3.7, 8.5 and 5.6 exists to handle them.

**What really improves the results, with any architecture:**

1.  A good spec before the code, iterated with you (the design studio, section 3.2).
2.  Small tasks with clear acceptance criteria.
3.  An API contract and tests that make the build fail when something does not add up.
4.  CI as an independent check: build, tests, licenses, vulnerabilities (section 5.6).
5.  Written project rules and hooks on dangerous commands.

### The recommended path

1.  **Plain Claude Code, plus the core of the template.** Copy the template and let `SETUP.md` fill it in (section 5.2), but keep only: `AGENTS.md` and `CLAUDE.md`, the design studio and ready specs before implementation, the project CI, the infrastructure-command hook, and two agents: the designer for reviews and the security agent on request. You work in one session, one task at a time, with PRs going through your CI. It is architecture A stripped down to the essentials.
2.  **Add roles only when one session is not enough:** when the context fills up on tasks that touch many parts, or when you want a separate review systematically.
3.  **Move to C or E only if you have the problem they solve:** you want work to progress while you are away, you have many independent tasks to run in parallel, or several people work together and need a shared board.
4.  **Decide with numbers.** Build the same feature both ways, with the method in section 10.6, and compare your time, the cost and the rework. If the difference is not obvious, you do not need the extra complexity yet.

The rest of the guide describes all the architectures, because knowing how far you can go helps you choose; but the recommended starting point is the first step above.

## 1.1 What you are about to build {#cosa-stai-costruendo}

The goal is a team of specialized agents (designer, frontend, backend and devops for everyday work, plus optimizer and security to call when needed) that work on the same repository, collaborate with each other and hand their work back to you as merge requests. The final code always stays under your control.

The guide is split into two parts.

| Part | Chapters | What it is for |
|---|---|---|
| I. Understand | 1–4 | the core concepts, the six possible architectures, the agents, how to improve the project over time |
| II. Build | 5–11 | the common preparation, then a step-by-step chapter for each architecture, with the commands to run |
| Appendices | 12–14 | security and limits, a five-day adoption plan, references |

If you are short on time: read chapters 1 and 2, pick an architecture, then follow chapter 5 and the chapter of the architecture you chose. Chapters 3 and 4 are for when you write the agents and when you want to improve them.


## 1.2 Three ways to make several agents work {#tre-meccanismi}

Claude Code offers three different ways to make several agents work together. Picking the wrong one is the most common mistake, so it is worth clarifying them right away.

**Subagents.** Specialized agents that live *inside* a single session. Each has its own context window, its own system prompt and its own set of tools. The main agent invokes them, they work in isolation and return a summarized result. They do not talk to each other on their own: coordination always goes through the main agent. They are cheap and they are the foundation of everything.

**Agent teams.** Here each member is a *complete, independent Claude Code session*. One session acts as team lead, the others as teammates. They share a task list and a mailbox: they message each other directly, claim tasks, challenge each other's conclusions. It is exactly the "the frontend gets feedback from the designer" model you described. It costs much more in tokens, because each teammate is its own instance, and it is still an experimental feature disabled by default.

**Agent SDK.** Claude Code used as a library, in Python or TypeScript. It is for when orchestration has to happen outside the terminal: a service that listens to your dashboard, starts agents, collects their output and writes back the task status. It is the basis of architecture F.


## 1.3 Harness, model and gateway {#harness-modello-gateway}

A model reachable through an API is not yet an agent. To work on a repository it needs a loop that plans, acts and verifies, tools to read and edit files and run commands, an environment to run in and access to Git. This layer is called the **harness**. Claude Code is Claude's harness; OpenCode and Codex are harnesses that also work with models from other providers.

An agent system therefore has three layers, plus an optional one:

    ┌──────────────────────────────────────────────┐
    │ DASHBOARD          you create the task,       │
    │ issues, Multica,   assign it to an agent,     │
    │ your dashboard     follow its status          │
    └───────────────────────┬──────────────────────┘
                            │ queue, status, comments
    ┌───────────────────────▼──────────────────────┐
    │ HARNESS            the agentic loop:          │
    │ Claude Code        tools, sandbox, Git        │
    │ OpenCode · Codex                              │
    └───────────────────────┬──────────────────────┘
                            │ model calls
    ┌───────────────────────▼──────────────────────┐
    │ GATEWAY            optional: one endpoint,    │
    │ (LiteLLM)          budgets, logs, fallback    │
    └───┬────────────┬────────────┬────────────┬───┘
     Anthropic    OpenAI      Google      local model

- **Dashboard:** where you create tasks and assign them. It can be your issue tracker, a dedicated tool like Multica, or a page of your own.
- **Harness:** where the agent actually works. It runs on a machine: your computer, a GitHub Actions runner, a server.
- **Model:** the real computation always happens on the provider's servers. The harness machine only does light work (reading files, running `git` and the tests), so you do not need powerful hardware, unless you want to host a model yourself.
- **Gateway:** a single entry point in front of several providers. Useful when you use several models and want budgets, keys and logs in one place.

Separating the layers is what makes it possible to change model by editing one line of configuration instead of redoing the project.


## 1.4 The tools for extending Claude Code {#strumenti}

Claude Code is extended through a few mechanisms. It is worth knowing all of them before choosing an architecture, because each one has a cost in tokens or in maintenance.

| Tool | What it is | How much it weighs |
|---|---|---|
| `CLAUDE.md` | project instructions, loaded into every session and every subagent | re-read at every step: keep it short |
| Agent (subagent) | a file in `.claude/agents/` with role prompt, tools, model and permissions | the description is always in context, the rest only when the agent starts |
| Skill | a folder with a `SKILL.md`: instructions and materials for a task | the description is always in context, the body only when needed |
| Hook | commands Claude Code runs on an event, for example before a command or when a task closes | no tokens: it is a check that runs regardless |
| Permissions | allow, ask and deny rules on tools and commands | no tokens |
| MCP server | a connection to external tools: browser, tracker, database | each server adds tool descriptions to the context |
| Plugin | a package bundling agents, skills, commands, hooks and MCP servers | the sum of what it contains |
| Mod | a change to Claude Code's interface and behavior, written in TypeScript | useful only when you work interactively |

The most important difference is between instructions and controls. A line in the prompt is a request the model usually follows. A hook, a permission or a platform rule is enforced in every case. The protections in this guide always belong to the second group.


## 1.5 Where the tokens go {#dove-vanno-i-token}

Every time the agent takes a step (reads a file, runs a test, writes code) the model re-reads the whole conversation so far. A typical task takes 20–30 steps, so the context is paid for many times over. Three practical rules follow:

- **Caching greatly lowers the cost of what has already been read.** In Claude Code it is on by default: re-reading cached text costs 5 to 10% of the input price, depending on the model.
- **Whatever enters every session is paid at every step of every agent.** `CLAUDE.md`, agent and skill descriptions, MCP server tools: keep them short and install only what you need.
- **The model's reasoning and the code it writes are paid as output,** which costs 5 to 20 times the input. That is why the reasoning level per role is one of the most effective levers.

Estimates for a whole project are in section 2.8, the levers for reducing spend in section 4.6.


## 1.6 The control principle {#principio-di-controllo}

The cornerstone of the architecture: **agents write only to branches**. No agent is allowed to push to `main`, to merge or to approve an MR. This is enforced on the platform side (branch protection), not in the prompt.

In one sentence: **agents propose, you decide**. It holds for every architecture in this guide, and it is achieved with three tools: branch protection and approvals on the platform, permissions and hooks in Claude Code, credentials that never reach real environments. The concrete steps are in section 5.5; the full checklist is in appendix 12.1.


# 2. The possible architectures {#architetture}

The architectures differ in three choices: where you create and assign tasks, where the agents run and which models they use. The six in this guide go from the simplest to the most customized. Each has a step-by-step chapter in the second part.


## 2.1 Overview {#panoramica}

            ┌──────────────────────────────────────────────┐
            │   DASHBOARD  (GitLab issues / GitHub Project │
            │   / Linear / custom dashboard)               │
            │   You create the task and assign it a role   │
            └───────────────────┬──────────────────────────┘
                                │  webhook / label / polling
                                ▼
            ┌──────────────────────────────────────────────┐
            │   ORCHESTRATOR                               │
            │   Claude Code (team lead)  or                │
            │   an Agent SDK service                       │
            └──────────────────┬───────────────────────────┘
                               │
       ┌──────────┬────────────┼────────────┬──────────────┐
       │          │            │            │              │
    ┌──▼─────┐┌───▼────┐┌──────▼───┐┌───────▼───┐┌─────────▼───┐
    │designer││frontend││ backend  ││ optimizer ││   devops    │
    └──┬─────┘└───┬────┘└──────┬───┘└───────┬───┘└─────────┬───┘
       └──────────┴────────────┼────────────┴──────────────┘
                               │
              task list, mailbox or comments
                               │
                               ▼
            ┌──────────────────────────────────────────────┐
            │   GIT  →  dedicated branch  →  MR/PR         │
            │   You review, comment, merge. Only you.      │
            └──────────────────────────────────────────────┘

| | Task board | Where the agents run | Models | Do the agents talk? | Setup | Guide |
|---|---|---|---|---|---|---|
| **A.** Claude Code with subagents | none: you coordinate | your computer | Claude | no, everything goes through you | a few hours | chapter 6 |
| **B.** Agent teams | the team's task list | your computer | Claude | yes, through a mailbox | half a day | chapter 7 |
| **C.** GitHub or GitLab, Claude only | the repository's issues | the CI runners | Claude | through comments | half a day | chapter 8 |
| **D.** Multi-model GitHub Actions | the repository's issues | GitHub runners | any, via API | through comments | one day | chapter 9 |
| **E.** Self-hosted Multica | the Multica board | a server of yours | any, via API | through the board | two or three days | chapter 10 |
| **F.** Orchestrator with the Agent SDK | your own dashboard or a tracker | a server of yours | Claude | as you design it | two or three days | chapter 11 |

The architectures can be combined. A stays useful on your computer even when C or D work in CI, and the preparation in chapter 5 applies to all of them.


## 2.2 A — Claude Code on your computer, with subagents {#arch-a}

The roles are subagents inside a Claude Code session on your computer. You give a task, the main agent hands it to the right role, the subagent works in a separate context and returns a summary.

- **Pros:** cheap, up and running in a few hours, works with a Claude subscription and leaves you in control of every step.
- **Cons:** it works only while the computer is on and you are present; the agents do not talk to each other, coordination goes through you; it uses only Claude.
- **When to choose it:** always, to start. It is the basis of all the others: the agent files written here are reused everywhere.


## 2.3 B — Agent teams {#arch-b}

With agent teams each role becomes an independent Claude Code session. One session acts as the lead, the others as teammates; they share a task list and a mailbox, message each other directly and review each other's work. It is the "the frontend gets feedback from the designer" model.

- **Pros:** real collaboration between roles, without going through you.
- **Cons:** it uses 2.5 to 4 times the tokens of architecture A, because each teammate is a separate instance; it is an experimental feature, disabled by default; it runs only on your computer and only with Claude.

- **When to choose it:** if the work is sequential, touches the same files or has many dependencies, a single session with the subagents of architecture A is more effective and costs a fraction. Teams pay off when there is real parallel exploration: multi-perspective review, independent modules, debugging with competing hypotheses.


## 2.4 C — GitHub or GitLab, Claude only {#arch-c}

The dashboard is your issue tracker. You put a label like `agent:backend` on an issue, a CI workflow starts Claude Code on a runner, the agent works on a branch, opens the merge request and comments on the issue with what it did. You review, comment with `@claude` to ask for fixes, and merge.

- **Pros:** board, notifications, permissions and history are already there; agents work even with your computer off; review happens where you already do it.
- **Cons:** Claude only; every task is a new session, so coordination between roles goes through comments and issue dependencies; GitLab has no native trigger on comments and needs a small webhook.
- **When to choose it:** when you want to assign a task and find it done, with no infrastructure to manage.


## 2.5 D — Multi-model GitHub Actions {#arch-d}

If you do not have a server, GitHub can act both as the board and as the machine the agents run on. As seen in section 1.3, **the model does not run on the runner.** When an agent uses Claude, DeepSeek or GPT via API, the computation happens on the provider's servers. The runner only executes the harness: it reads files, edits code, runs `git` and the tests. For a web app a standard GitHub Actions machine is enough.

    Issue + label agent:<role>              board: GitHub Issues and Projects
              │
              ▼
    GitHub Actions workflow ──► GitHub-hosted runner (ubuntu-latest)
                                    ├─ Claude Code action → Anthropic API
                                    └─ OpenCode action    → DeepSeek, Mistral, OpenAI API, …
                                                             (directly or via LiteLLM)
              │
              ▼
    Branch + pull request ──► your review ──► merge

It is architecture C, extended to several harnesses and several models. The variants differ only in how the agents reach the models: direct keys, LiteLLM on a server of yours, or a hosted gateway (section 9.4).

|                      | Variant 1: direct keys            | Variant 2: LiteLLM on a server                |
|------------------------|------------------------|------------------------|
| Provider keys | in GitHub secrets, one per role   | only on the server; GitHub holds only virtual keys |
| Budget per role     | in each provider's console       | in one place, per virtual key           |
| Costs and logs          | separate per provider                | unified                                       |
| Revoking an agent  | one key per provider              | one virtual key                             |
| Extra cost         | none                               | a small server, about €6 a month            |
| Maintenance         | none                               | server updates and backups               |
| When to choose it    | to start, with two or three providers | when providers or roles grow           |

- **Pros:** free choice of models, no computer or server of yours needed (variant 1), almost zero infrastructure cost.
- **Cons:** agents that do not use Claude Code lose Claude Code's hooks and permissions: the protections must be rebuilt (section 3.9); with variant 2 you have a server to maintain.
- **When to choose it:** when you want to try other models on some roles while keeping GitHub as the board.


## 2.6 E — Self-hosted Multica {#arch-e}

A dedicated board, hosted by you, where agents appear as team members: you assign them to an issue as you would a colleague, they pick up the work, update the status and report blockers. A daemon on a server of yours runs the installed harnesses (Claude Code, OpenCode, Codex and others).

- **Pros:** a board designed for agents, multi-model, everything under your control.
- **Cons:** an always-on server to maintain; a young tool that changes fast.
- **When to choose it:** when you have a server and want a single view over agents running on different harnesses.

Tools of this kind compared:

|             | Multica                                                            | OpenHands                               | GitHub Agent HQ                  |
|------------------|------------------|------------------|------------------|
| What it is       | an issue board where agents are team members                    | an agent with a web interface              | issue assignment inside GitHub |
| Models     | those of the harnesses you install; with OpenCode, any provider | any model supported by LiteLLM | Copilot, Claude, Codex           |
| Self-hosted | yes                                                                 | yes                                      | no                               |
| GitLab      | through the daemon's Git credentials                              | native integration                     | no                               |
| Maturity    | young, evolving fast                                          | mature                                  | a GitHub service                  |

Chapter 10 follows **Multica**, because it is the closest to the "I create the task, assign it, the agent starts" model. Vibe Kanban, which used to be the reference in this space, is not recommended for a new project: the company developing it shut down in April 2026 and the project continues as community-maintained open source.

The commands are taken from the projects' documentation as of October 2026: compare them with the current READMEs before running them.


## 2.7 F — Orchestrator with the Agent SDK {#arch-f}

A service written by you, with Claude's Agent SDK, that takes tasks from a queue (your own dashboard or an existing tracker), starts the agent of the right role, follows its progress and updates the task with the result and the cost.

- **Pros:** total control over queues, priorities, retries, where the work runs and what gets recorded.
- **Cons:** it is your code to write and maintain; it uses Claude.
- **When to choose it:** when architectures C and E are not enough, for example because you need priorities, automatic retries or execution on your own infrastructure.

Compared with the other two forms of task dashboard:

|                           | Issues (architecture C)                    | Tracker via MCP (section 11.1)                | Orchestrator (section 11.2)   |
|------------------|------------------|------------------|------------------|
| Initial work           | a few hours                      | half a day           | 2--3 days |
| Needs your own backend      | no                             | no (but needs a trigger) | yes          |
| Control over queues and retries | limited                       | limited                 | total      |
| Graphical dashboard         | GitHub Projects / GitLab board | the tracker's       | yours         |
| Maintenance cost     | almost zero                    | low                    | yours         |

The advice: start with issues, and move to the orchestrator only when you have a concrete reason --- typically when you need a queue with priorities, automatic retries, or execution on your own infrastructure.


## 2.8 How much it costs {#quanto-costa}

The estimates refer to a medium-sized web app, about 10,000 lines of code: five or six pages, authentication, CRUD on a few entities, two integrations with external services, tests. List prices as of October 2026, one month of work.

### The assumptions

-   **Work:** about 60 tasks plus 10 of rework and iterations on comments, so 70 in total. One pull request per task, checked by the project CI and, if you enable it, by an automatic review with Claude.
-   **Turns:** 25 turns per task on average. Weaker models use about 30% more, because they get more tool calls wrong.
-   **An average turn:** about 55,000 input tokens, of which 48,000 read from cache, and 2,500 output tokens.
-   **Runners:** in architectures C and D about one runner minute per agent turn, tests included; an AI review takes 5. The project CI about 8--10 minutes per run, a few runs per PR.

From these assumptions comes the cost of one turn per model:

| Model                                   | Cost per turn |
|-------------------------------------------|-----------------|
| Claude Opus 5.5                           | \$0.095        |
| Claude Sonnet 5.5                         | \$0.052        |
| GPT-6 Sol                                 | \$0.049        |
| DeepSeek V4 Pro, with cache discount   | \$0.025        |
| DeepSeek V4 Pro, without cache discount | \$0.083        |
| Mistral Large 4, with cache discount   | \$0.013        |
| Mistral Large 4, without cache discount | \$0.043        |

For Sonnet 5.5, GPT-6 Sol, DeepSeek and Mistral the cache rates are not clearly published: I assumed 10% of the input price, as for the other models. For DeepSeek and Mistral the difference matters a lot, which is why they appear twice: every turn re-reads about 48,000 tokens it has already seen, and without a discount those tokens are paid at full price. Mistral has the lowest list price, but without a cache discount it costs more per turn than DeepSeek with the discount. Before choosing, check each provider's price list for whether and how much it discounts cached tokens.

### Agent token cost by model assignment

Backend and devops stay on Opus in every case, as recommended in section 3.8. These figures are only the agents' work, paid via API; the automatic review in CI and runner minutes are separate items, in the next table.

| Assignment              | Frontend  | Optimizer | Agent tokens |
|---------------------------|-----------|-----------|--------------------|
| Claude only               | Sonnet    | Opus      | about \$135   |
| Balanced                | GPT-6 Sol | DeepSeek  | about \$120   |
| Budget, cache on   | DeepSeek  | DeepSeek  | about \$110   |
| Budget, no cache    | DeepSeek  | DeepSeek  | about \$170   |
| Budget Mistral, cache on | Mistral | Mistral | about \$100 |
| Budget Mistral, no cache  | Mistral | Mistral | about \$130 |
| Mixed                     | DeepSeek  | Mistral   | about \$110   |
| All Opus, for comparison | Opus      | Opus      | about \$165   |

In total about 100--115 million tokens go through, almost all of them input.

### Comparing the architectures

Three items not to be confused:

-   **Agent tokens:** the development work. With a subscription (architectures A and B) it is included in the plan; elsewhere it is the table above.
-   **AI review in CI:** the `claude-review.yml` workflow, which has Claude review every PR. It is **optional**: about \$30 a month via API (70 PRs × 8 turns on Sonnet), zero if you remove it or configure it with the subscription token (`claude_code_oauth_token`), which however uses up your plan's quota.
-   **CI minutes:** the runners that execute the project CI (build, tests, licenses, vulnerabilities, section 5.6) and, in architectures C and D, the agents themselves. Free on public repositories; on private ones, beyond the 2,000 minutes included in GitHub's Free plan, \$0.006 per minute.

| Architecture | Where the agents run | Agent tokens | AI review in CI | CI minutes | Infrastructure | Monthly total | Your setup time |
|---|---|---|---|---|---|---|---|
| A. Claude Code on your computer | your computer | Max 5x (\$100) or 20x (\$200) subscription | 0 or \~\$30 | \~2,500 min: \$0--5 | none | \$100--235 | a few hours |
| B. Agent teams | your computer | Max 20x (\$200), or \$400--650 via API | 0 or \~\$30 | \~2,500 min: \$0--5 | none | \$200--685 | half a day |
| C. GitHub Actions, Claude only | GitHub runners | about \$135 | 0 or \~\$30 | \~4,500 min: \$0--30 | none | \$135--195 | half a day |
| D. Multi-model, direct keys | GitHub runners | \$100--170 | 0 or \~\$30 | \~4,500 min: \$0--30 | none | \$100--230 | one day |
| D. Multi-model, hosted gateway | GitHub runners | as above, plus \~5.5% | 0 or \~\$30 | \~4,500 min: \$0--30 | none | \$105--240 | one day |
| D. Multi-model, LiteLLM on a server | GitHub runners; the gateway on the server | \$100--170 | 0 or \~\$30 | \~4,500 min: \$0--30 | server \~\$7 | \$105--240 | one or two days |
| E. Self-hosted Multica | a server of yours, or your PC | \$100--170 | 0 or \~\$30 | \~2,500 min: \$0--5 | server €15--25 (0 on your PC) | \$100--230 | two or three days |
| F. Orchestrator with the Agent SDK | a server of yours | about \$135 | 0 or \~\$30 | \~2,500 min: \$0--5 | server €6--25 | \$140--195 | two or three days |

Notes on the table:

-   **CI minutes.** The project CI takes about 8--10 minutes per run and runs several times per PR (every push) and on `main`: about 2,500 minutes a month, a little over the 2,000 free ones. In architectures C and D you add about 1,750--2,000 runner minutes for the agents' work and 350 for the AI review, if enabled: about 4,500 in total, i.e. \$15--30 on a private repository. On GitLab what counts is your plan's compute minutes, or nothing with your own runner.
-   **Architecture A.** It is the only one without non-Claude models and without automatic work while the laptop is off. Subscription limits are not published in tokens: with Opus on the main roles, Pro is not enough for such an intense month, Max 5x probably is. The total goes from \$100 (Max 5x, no AI review via API) to \$235 (Max 20x, review via API, minutes over the quota).
-   **Security.** It is not in the figures because it runs only on request: a full assessment costs about \$3--4 on Opus, a re-test of only the findings less than \$1. The fixes it produces are normal tasks, already included in the rework.
-   **Architecture B.** Teams multiply consumption by 2.5--4 compared with architecture A: with a subscription you need Max 20x, via API the estimate rises to \$400--650 a month.

### What the numbers say

1.  **Tokens are almost all of the cost.** CI minutes and servers weigh a few dollars a month, at most around thirty in architectures C and D on a private repository. Choose the architecture for convenience and control, not for the cost of the infrastructure.
2.  **Multi-model saves little here, 10--20% in the best case.** The spend is concentrated on backend and devops, which stay on Opus. A big saving would only come from moving the backend to a cheaper model, i.e. exactly where a mistake costs the most. With DeepSeek without a cache discount, multi-model even costs more than "Claude only"; with Mistral without a discount it roughly breaks even. The saving depends on the cache more than on the list price.
3.  **The variables that weigh the most are turns per task and rework.** A realistic range goes from half to double the figures in the table. Small tasks and clear specs matter more than the choice of model. To replace these estimates with numbers measured on your project, see section 10.6.
4.  **Recompute after ten tasks.** Take the real costs from the providers' consoles or from LiteLLM's logs, and replace the assumptions in this section with them.


## 2.9 How to choose {#come-scegliere}

- **Always start with A, or rather with its core** ("Before you start: do you really need this?", at the beginning of chapter 1). One or two weeks on your computer teach you where the agents go wrong, and those corrections apply to every architecture. Move to the others only when you have the problem they solve.
- **Do you want to assign tasks and find them done?** Move to C. It is the biggest convenience jump for the least work.
- **Do you want to try other models without a server?** D with direct keys (variant 1).
- **Providers and roles are growing, and you want budgets and logs in one place?** D with LiteLLM on a server (variant 2).
- **Do you have a server and want a board dedicated to agents?** E.
- **Do you need your own queues, priorities and retries?** F.
- **B** only for work with real parallel exploration, measuring the cost against A.


# 3. The agents {#agenti}


## 3.1 How an agent is defined {#definire-agente}

A subagent is a Markdown file with YAML frontmatter. The frontmatter configures it; the body of the file becomes the system prompt.

Only two fields are required: `name` and `description`. The other useful ones for our case are `tools` (allowlist), `disallowedTools` (denylist), `model`, `permissionMode`, `skills`, `mcpServers`, `hooks`, `memory` and `isolation`.

**Golden rule for the `description`:** Claude decides whom to delegate to by reading the descriptions of all the agents, and they take up context in every session. Keep them short and clearly distinct from each other; everything else goes in the body, which is loaded only when the agent actually starts.


## 3.2 Designer (UI/UX) {#agente-designer}

The designer does not write production code: it produces specs, tokens and feedback. We take away `Write` and `Edit` on source code and, if you want, give it a browser MCP so it can actually look at the pages.

``` {.sourceCode .markdown}
---
name: designer
description: UI/UX design, design system, accessibility. Writes specs and
  reviews the implemented interface. Does not write application code.
tools: Read, Grep, Glob, Write, WebFetch, SendMessage
model: sonnet
memory: project
color: purple
skills:
  - design-system
mcpServers:
  - playwright:
      type: stdio
      command: npx
      args: ["-y", "@playwright/mcp@latest"]
---

You are the team's product designer. Your output is a spec, not code.

## Two modes
- **Studio mode**, with the user, interactive: the large design work (the
  project design, a new feature). It follows `docs/roles/design-studio.md`
  and ends with a spec marked `ready: yes`.
- **Task mode**, inside a task or delegated by the lead: alignment reviews,
  small spec changes, reviews of the implemented interface. If a task needs
  more than a small change to a spec (a new flow, a new page, a redesign),
  stop and say that it needs a studio session; do not redesign inside a task.

## What you produce
For each feature, write `docs/design/<feature>.md` from
`docs/design/_spec-template.md`, with:
1. User goal and observable acceptance criteria.
2. Page structure: hierarchy, states (empty, loading, error, success),
   responsive behavior at the project's breakpoints.
3. Tokens to use, taken ONLY from `src/styles/tokens.css`. If you need a
   value that does not exist, propose it explicitly as a new token instead
   of writing a literal value.
4. Accessibility requirements: ARIA roles, focus order, minimum contrast
   4.5:1 for body text, touch targets of at least 44px.

## When you review the frontend's work
Use the Playwright tools to open the page in the states and at the
breakpoints you specified. Then send the frontend a message with a bullet
list, where every item has this shape:

  [BLOCKER|IMPORTANT|NICE-TO-HAVE] file:line — what is wrong — what to do

At most five items per review round: if there are more, keep the five most
severe and say so. Do not rewrite the code yourself.

## Alignment reviews
When the lead asks you to process an entry in `docs/alignment/`:
1. Read the entry and the change it points to.
2. Check it against the specs in `docs/design/` and update them if the change
   is acceptable.
3. Write under "Follow-up actions" one checkbox per affected role, with the
   files to touch.
4. Set `decision-needed: yes` and explain why when the change needs the
   user: a breaking API change, a visible UX change, a trade-off between
   roles.

## Memory
Update your project memory with recurring design decisions and with the
mistakes you see repeated, so you can anticipate them in later rounds.
```

The `memory: project` field creates a persistent directory in `.claude/agent-memory/designer/`, which can be versioned, where the agent accumulates knowledge from one session to the next.


### Two modes: studio and task {#design-studio}

Something you notice again and again working with Claude: the more iterations you do on the design, the more often the implementation task comes out right the first time. The problem is where those iterations happen. If they happen in MR comments, code review becomes a slow, expensive chat, and every round restarts an agent in CI. That is why the designer works in two modes.

-   **Studio, interactive, with you.** The bulk of the work: the project design and every new feature. Questions, alternatives with their trade-offs, drafts rewritten several times. It produces one thing only, the spec in `docs/design/<feature>.md`, with a readiness checklist and the breakdown into tasks. The procedure is in `docs/roles/design-studio.md`.
-   **Task, automatic.** Only targeted interventions: reviewing alignment entries, small changes to a spec, reviewing the implemented interface. If a task needs more, a new flow or page, the designer stops and asks for a studio session.

The handoff between the two modes is the spec file, not the conversation. The implementing agents read a small, stable spec instead of the history of the discussion: that is what makes them precise. `AGENTS.md` makes it a rule ("Specs before code"): an implementation task starts only from a spec with `ready: yes`, and if the spec does not cover something the agent stops and writes it down, instead of inventing. The issue template in the template has a field for it. The final part of the spec template:

``` {.sourceCode .markdown}
## Task breakdown
| # | Role | Task | Depends on |
|---|---|---|---|
| 1 | backend | ... | — |
| 2 | frontend | ... | 1 |
Team task possible: yes / no (roles: ...)

## Readiness checklist
- [ ] goal, users and out of scope agreed
- [ ] every flow has its error and edge cases
- [ ] every screen has empty, loading, error and success states
- [ ] contract changes written, breaking changes approved by the user
- [ ] acceptance criteria are observable
- [ ] task breakdown with roles and dependencies
- [ ] no open questions
```

**Where to do the studio.** In order of integration:

1.  **Claude Code or OpenCode on your computer.** `/design-studio <feature>` starts the session: in Claude Code it is a skill that starts only when you call it (`disable-model-invocation: true`), in OpenCode a command in `.opencode/commands/`. Both point to the same procedure in `docs/roles/design-studio.md`, so the result does not depend on the harness. When the project is created, `SETUP.md` enforces it: once configuration is done, if `docs/design/project.md` does not exist or is not ready, it opens a studio session for the project design (product and users, flows, screens, data model, first version of the API contract, non-functional requirements, visual direction, roadmap) and does not consider the setup finished until it is ready. You can skip it only by saying so explicitly, and in that case no implementation task can start.
2.  **A Claude Code session in the cloud** (claude.ai/code, the Code tab in the app, the desktop app choosing Cloud). Same command, same procedure, but it keeps running with your laptop closed and you can carry it on from your phone. It uses the subscription; it clones and pushes only on GitHub.
3.  **A project on claude.ai** for freer exploration, with the project documents uploaded. The move to the repository is manual: you, or a Claude Code session, commit the final spec.
4.  **The orchestrator's studio mode** (section 11.4): a chat in the dashboard, a button that checks the checklist and opens the design PR, and tasks created automatically after the merge.

In every case the studio session is where the best model pays off: that is where a better spec saves the most turns later.


## 3.3 Frontend {#agente-frontend}

``` {.sourceCode .markdown}
---
name: frontend
description: Implements and changes the user interface (components, client
  state, styles, component tests). Applies the designer's feedback.
tools: Read, Write, Edit, Grep, Glob, Bash, SendMessage
model: sonnet
color: blue
memory: project
skills:
  - design-system
hooks:
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./.claude/hooks/lint-frontend.sh"
---

You are the team's frontend developer.

## Boundaries
You work only under `src/ui/`, `src/components/`, `src/styles/`. You do not
touch `src/server/` or migrations: if you need a different endpoint, send a
message to `backend` and wait (in CI, write it in the MR as an alignment
entry); do not implement server-side code yourself.

## Non-negotiable rules
- No hand-written color, spacing or typography values: only variables from
  `tokens.css`.
- Every new component has a loading state and an error state.
- No network calls inside a presentational component: go through the layer
  in `src/api/`.
- API types come from the contract (generated), never written by hand.
- A change to a shared component, a route or a user flow is an alignment
  change: follow the procedure in `AGENTS.md`.
- Before declaring a task done: `npm run lint && npm run test`.

## Workflow
1. Read the designer's spec in `docs/design/`.
2. Implement.
3. Tell `designer` the feature is ready for review, saying which route to
   open and with which test data.
4. Apply the feedback. If you disagree with an item, reply with the
   technical reason instead of silently applying it: the designer can
   accept the objection.
```


## 3.4 Backend {#agente-backend}

``` {.sourceCode .markdown}
---
name: backend
description: APIs, data model, migrations, authentication, server-side
  integration tests.
tools: Read, Write, Edit, Grep, Glob, Bash, SendMessage
model: opus
color: green
memory: project
---

You are the team's backend developer.

## Boundaries
You work under `src/server/`, `migrations/`, `tests/integration/`. You do
not touch `src/ui/`.

## Non-negotiable rules
- Every endpoint validates its input at the edge before anything else.
- Migrations are additive and reversible: never DROP a column in the same
  migration that stops using it.
- No secrets, no keys, no connection strings in the code.
- Every new endpoint has at least one happy-path test and one error-path
  test.
- The API contract (see `AGENTS.md`) changes before or together with the
  code. When you change the shape of a response, follow the alignment
  procedure in `AGENTS.md`; in a team session also message `frontend`.

## Delivery
Write correct, readable code, not micro-optimized code: `optimizer` takes
care of optimization in a second pass. If you already know a spot will be
performance-critical, leave a `// PERF: <reason>` comment instead of
acting right away.
```


## 3.5 Optimizer {#agente-optimizer}

This is the case where it pays to separate the analysis phase from the editing phase. An agent that analyzes *and* rewrites tends to rewrite too much. Give it `Edit` but bind it to a narrow mandate, and make it work in an isolated worktree.

``` {.sourceCode .markdown}
---
name: optimizer
description: Analyzes existing code for performance, complexity and
  duplication, and applies targeted optimizations without changing
  observable behavior. Use it only when the user asks for it or a
  performance problem has been measured, never as a routine step.
tools: Read, Edit, Grep, Glob, Bash, SendMessage
model: opus
effort: high
isolation: worktree
color: orange
memory: project
---

You are the engineer who optimizes code that already works.

## Absolute constraint
Observable behavior does not change. Before touching anything, run the test
suite and record the result; at the end it must be identical. If a test was
already failing, say so and do not fix it yourself.

## Order of work
1. **Measure.** Do not optimize on intuition. Use the project's benchmarks
   or write a minimal one. Report the starting number.
2. **Classify** every proposed change as:
   - ALGORITHMIC — change in complexity (the most valuable)
   - I/O — N+1 queries, network round trips, repeated reads
   - ALLOCATION — avoidable copies and allocations in hot paths
   - READABILITY — duplication, overly long functions, opaque names
3. **Apply** only changes with a measured gain or an evident algorithmic
   reason. A gain under 5% does not justify making the code less readable:
   drop it and say so.
4. **Report** in a single message: number before, number after, list of
   changes, and what you decided NOT to do, with the reason.

## What you never do
You do not change public APIs, rewrite whole modules, add new dependencies,
or touch tests to make them pass.
```

The `isolation: worktree` field makes the agent work in a temporary copy of the repository on a separate Git worktree, which is cleaned up automatically if it produces no changes. It is the strongest guarantee that a refactoring gone wrong does not dirty your checkout.

**On request only.** In a typical web application most features have no performance problems, and backend and frontend already do the light cleanup. That is why the optimizer is not part of the standard sequence: you call it when a measurement shows a problem (a slow page, an N+1 query, a growing bundle) or when you want a performance review before a release. In the template it is listed among the on-request roles in `AGENTS.md`, together with security (section 3.10).


## 3.6 Devops {#agente-devops}

It is the role that needs the most caution of all, because it is the only one that touches things that can break something outside the repository: pipelines, images, infrastructure, deploys. The rule that governs it is clear-cut: **it describes the desired state, it does not apply it**. It writes the manifest, the chart, the Terraform module, the pipeline job --- and opens them in an MR. The pipeline applies them, after you have merged.

``` {.sourceCode .markdown}
---
name: devops
description: CI/CD pipelines, containers, infrastructure as code, deployment
  and observability. Writes configuration, never applies it to environments.
tools: Read, Write, Edit, Grep, Glob, Bash, SendMessage
model: opus
color: cyan
memory: project
permissionMode: default
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./.claude/hooks/block-infra-commands.sh"
---

You are the team's DevOps engineer.

## Boundaries
You work on: `.github/workflows/` (or `.gitlab-ci.yml` and `.gitlab/ci/`), `ci/`, `Dockerfile*`,
`compose*.yml`, `deploy/`, `charts/`, `infra/`, `Makefile`, `.dockerignore`.
You do not touch application code: if a code change is needed to make the
service deployable — an environment variable to read, a health endpoint —
ask `backend` or `frontend` for it with a message; do not implement it
yourself.

## The rule that comes before all others
You apply nothing to any environment. You write the configuration and
propose it in a merge request. In particular you never run: `terraform
apply`, `kubectl apply`, `kubectl delete`, `helm upgrade`, `helm install`,
`docker push`, `ansible-playbook` without `--check`, or any command that
writes to a cluster or a remote registry. If you think one is needed, write
it in the MR description and let a human decide.

## Non-negotiable rules
- **No secrets in files.** Never a key, token or password in a workflow, a
  Dockerfile or a manifest. Only references to the platform's secret
  manager. If you find a committed secret, stop immediately and report it
  without reproducing it in the message.
- **Pinned base images**, by digest when possible, never `:latest`.
- **Non-root containers**, read-only filesystem where the service allows it,
  no added capabilities without a written reason.
- **Every job has a timeout** and every pipeline has a concurrency control.
- **Every service has a healthcheck, resource limits and a rollback
  procedure documented** in the MR. A deployment without rollback is not
  ready.
- **Pipelines are deterministic**: locked dependencies, cache with an
  explicit key, no `curl | bash` from unverified sources.

## How you validate your work
Before opening the MR, run locally whatever can run without touching an
environment, and report the output:

    hadolint Dockerfile
    actionlint                       # or: gitlab-ci-local --list
    docker build --no-cache .        # local build, no push
    helm template ./charts/app       # render manifests, no install
    kubeconform -strict              # schema validation
    terraform validate && terraform fmt -check
    terraform plan -out=/dev/null    # plan only, never apply

If one of these tools is not installed in the project, say so instead of
silently skipping the check.

## What you write in the MR
Always these four items, in this order:
1. What changes in the infrastructure, in one sentence.
2. The diff of the `terraform plan` or of the rendered manifests, if
   relevant.
3. The blast radius if the change is wrong: what breaks, for whom, for how
   long.
4. How to roll back, command by command.

## Collaboration
- Ask `backend` for: required environment variables, ports, external
  dependencies, CPU and memory requirements, what the healthcheck must
  return.
- Ask `frontend` for: how the bundle is built, which variables are needed
  at build time and which at runtime.
- New or renamed environment variables, ports, health endpoints or
  deployment interfaces are alignment changes: follow the procedure in
  `AGENTS.md`.
- Tell `optimizer` about build times and image sizes when they get more
  than 20% worse: it is a performance problem like any other.
```

The `PreToolUse` hook is the safety net under the rule written in the prompt. The prompt is a request; the hook is a check that runs regardless.

``` {.sourceCode .bash}
#!/bin/bash
# .claude/hooks/block-infra-commands.sh
# Blocks commands that change real environments.

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[ -z "$CMD" ] && exit 0

FORBIDDEN='terraform[[:space:]]+apply|terraform[[:space:]]+destroy|kubectl[[:space:]]+(apply|delete|patch|rollout)|helm[[:space:]]+(install|upgrade|uninstall|rollback)|docker[[:space:]]+push|podman[[:space:]]+push|aws[[:space:]]+.*[[:space:]](create|delete|update)-|gcloud[[:space:]]+.*deploy'

if echo "$CMD" | grep -qE "$FORBIDDEN"; then
  echo "Blocked: this command changes a real environment." >&2
  echo "Write the configuration and propose it in an MR: the pipeline applies it after the merge." >&2
  exit 2
fi
exit 0
```

Remember `chmod +x`. Exiting with code 2 blocks the command and returns the message to the agent, which then knows why it stopped and what to do instead.

> **A note on the permission model.** Note that `devops` is the only agent in the guide with `permissionMode: default`, i.e. the one that asks for confirmation. If your lead runs in automatic mode the value is ignored anyway --- permissions are inherited from the parent --- but it is worth leaving it written: it documents the intent, and it applies when the agent starts as the main session with `claude --agent devops`.


## 3.7 The rules of engagement in CLAUDE.md {#regole-claude-md}

`CLAUDE.md` is loaded in every session and in every subagent. It is where you write how the team must work.

``` {.sourceCode .markdown}
# Project: <name>

## Stack
<frameworks, languages, build and test commands>

## Commands
- Test: `npm test`
- Lint: `npm run lint`
- Dev server: `npm run dev` (port 5173)

## How work is delegated in this project

Route by file boundary, not by topic:
- `src/ui/`, `src/components/`, `src/styles/` → frontend
- `src/server/`, `migrations/` → backend
- `docs/design/`, UI review → designer
- `.github/workflows/`, `.gitlab/ci/`, `ci/`, `Dockerfile*`, `deploy/`, `charts/`, `infra/` → devops
- Optimizing code that already works and is tested → optimizer

Two agents never edit the same file in the same round. If a task crosses
a boundary, split it into two tasks with an explicit dependency.

## Standard feature sequence
1. designer writes the spec in `docs/design/`
2. backend updates the API contract, if the feature changes it
3. backend and frontend implement in parallel, against that contract
4. designer reviews the implementation
5. frontend applies the feedback
6. devops updates pipeline, image and manifests if the feature needs it
7. the MR is opened

Not every feature involves every role. A style change does not need
devops; an infrastructure migration does not need the designer. Involve
only the roles the task actually touches.

## On-demand roles
These two roles are never part of the standard sequence. Delegate to them
only when the user asks explicitly.
- optimizer: when the user asks for an optimization or a measurement shows
  a performance problem. Only with green tests.
- security: when the user asks for a security assessment, typically once the
  application is complete or before a release. It reports findings; the
  owning roles fix them as separate tasks.

## API contract
The contract between frontend and backend is `docs/api/openapi.yaml`.
- backend owns it and updates it before or together with the code.
- frontend generates its API types from it and never hand-writes response
  types, so a mismatch becomes a build error.
- Removing or renaming a field, changing a type, a status code or an error
  shape is a breaking change: it is always an alignment change and needs the
  user's approval in the MR.

## Alignment changes
A change is an alignment change when another role relies on what you
changed: the API contract, the data model, a shared component or design
token, a route or user flow, an environment variable or port, the deployment
interface.

When you make one:
1. Copy `docs/alignment/_template.md` to
   `docs/alignment/<yyyy-mm-dd>-<task-id>.md` and fill it in, with
   `status: open`. One file per change, so parallel branches never conflict.
2. In the MR description add an `## Alignment impact` section that links the
   entry (write "none" when there is none). In CI also add the
   `alignment-needed` label to the MR.
3. Do not adapt other roles' code yourself.

What happens next depends on where you run:
- **Local session (Claude Code with subagents or agent teams):** the lead
  handles it right away. First designer reviews the change against the specs,
  updates `docs/design/` if needed and writes the follow-up actions per role
  in the entry. Then the lead delegates each action to its role. Finally the
  entry gets `status: resolved` and a short resolution. The lead stops and asks
  the user only when designer sets `decision-needed: yes` (for example a
  breaking API change or a visible UX change).
- **CI (GitHub Actions, GitLab CI, Multica):** agents never start other
  agents, except the coordinator of a team task (below). The entry and the
  label are the signal: the user reviews them and creates the alignment
  tasks, designer first, then the affected roles.

## Team tasks
A team task is one issue carried out by several roles in sequence on the same
branch, ending in one MR. The user asks for it explicitly: the `agent:team`
label on GitHub (with a `Roles: backend, frontend` line in the issue body),
`AI_FLOW_ROLES` on GitLab, or a request in a local session.
- A coordinator delegates only to the listed roles, in the listed order, and
  writes no code itself.
- Each role works within its own boundaries and commits and pushes before the
  next one starts.
- Alignment entries that concern listed roles are handled inside the task;
  the others stay open and are reported in the MR.
- Use team tasks for small, tightly coupled features. Larger work stays split
  into separate tasks, so that each MR remains reviewable.

## Specs before code
Implementation tasks start from a spec in `docs/design/` marked `ready: yes`
(see `docs/design/_spec-template.md`). The project design is
`docs/design/project.md`.
- If the task has no spec, the spec is not ready, or it does not cover what
  you are asked to do: stop, write what is missing in the issue or in your
  final message, and do not invent the missing design.
- Large design work happens in a studio session with the user
  (`docs/roles/design-studio.md`), not in MR comments. MR comments are code
  review.

## Branches and merge requests
- One branch per task, named `feat/<task-id>-<slug>` (in GitHub Actions, the
  branch the action creates for you).
- Before opening the MR, bring your branch up to date with `main` and run the
  tests again. Where you are not allowed to rebase (the Claude GitHub action),
  say in the MR that the branch must be updated before merging.
- Before opening the MR, check whether `main` changed the API contract or
  `docs/alignment/` since you started; if it did, adapt or report it.

## CI
Every MR runs the project CI: build, test, SBOM and license report, license
policy, vulnerabilities, secrets and misconfigurations (`ci/scan.sh`).
- A red CI is part of your task: fix the cause, never weaken the check. Do not
  edit `ci/scanners.env`, skip a test or add an ignore rule without the user's
  explicit approval in the MR.
- When you run outside CI (a local session, the Multica daemon, the
  orchestrator), wait for the checks after opening the MR (`gh pr checks
  --watch`, or `glab ci status` until the pipeline ends), fix what fails and
  push again. Agents that run inside CI jobs do not wait: the user or the
  orchestrator sends the failures back.

## Rules for everyone
- Small commits, messages in English, imperative mood.
- Nobody pushes to `main`. Nobody merges. Nobody closes an issue.
- If a requirement is ambiguous, stop and ask; do not guess.
```


### Contract and alignment changes {#allineamento}

Two agents working in parallel can break each other without Git noticing. The typical case: the backend renames a field, meanwhile the frontend writes the page against the old name, both MRs pass their own tests and have no conflicts, and the app breaks after the merge. The rules in `AGENTS.md` above tackle the problem from two sides.

**The contract before the code.** The interface between frontend and backend lives in a versioned file (`docs/api/openapi.yaml` in the template) owned by the backend. The frontend generates its types from it instead of writing them by hand, so a renamed field becomes a compile error in CI and not a runtime bug. Changes that break compatibility are listed and need your approval.

**Every change that affects others is declared.** When an agent changes something another role relies on (contract, data model, shared components or tokens, routes, environment variables, deploy interface), it writes an entry in `docs/alignment/`, one file per change, so parallel branches never conflict, and adds an `## Alignment impact` section to the MR. The entry template:

``` {.sourceCode .markdown}
---
status: open            # open | resolved
date: YYYY-MM-DD
author: <role that made the change>
task: <issue or task id>
mr: <link to the MR, if any>
breaking: no            # yes if another role's code stops working without changes
affects: []             # roles that must adapt, for example [frontend, devops]
decision-needed: no     # set by designer: yes if the user must decide
---

## What changed
<one or two sentences>

## What the others relied on (before → after)
<for example: GET /api/profile returns `fullName` → returns `firstName` and `lastName`>

## Follow-up actions
<!-- written by designer, one checkbox per affected role -->
- [ ] frontend: ...

## Resolution
<!-- filled in when status becomes resolved -->
```

What happens next depends on where the agents run:

-   **Locally (architectures A and B) alignment starts on its own.** The lead sees the open entry and first delegates to the designer, which compares the change with the specs, updates `docs/design/` and writes the actions for each role in the entry; then it delegates those actions to the roles involved and closes the entry. It stops to ask you something only if the designer marks `decision-needed: yes`, for example for a non-backward-compatible API change or a user-visible change. A hook reminds the lead of open entries after every delegation, so it does not depend only on its memory:

    ``` {.sourceCode .bash}
    #!/bin/bash
    # .claude/hooks/alignment-check.sh
    # After every delegation, reminds the lead of open alignment entries.
    DIR="${CLAUDE_PROJECT_DIR:-.}/docs/alignment"
    [ -d "$DIR" ] || exit 0
    OPEN=$(grep -l '^status: open' "$DIR"/*.md 2>/dev/null | grep -v '/_template.md$' | grep -v '/README.md$')
    [ -z "$OPEN" ] && exit 0
    echo "Open alignment entries:" >&2
    echo "$OPEN" | sed 's#^.*/docs/#  docs/#' >&2
    echo "Follow AGENTS.md > Alignment changes: designer first, then the affected roles; in CI, label the MR and stop." >&2
    exit 2
    ```

    In the template it is wired in `.claude/settings.json` as a `PostToolUse` hook on the delegation tool (`Agent`). With agent teams the reminder does not fire, because the lead does not delegate through that tool: there the instruction in `CLAUDE.md` applies.

-   **In CI (architectures C, D and E) agents do not start other agents**, except the coordinator of a team task you ask for (section 8.5). The entry in `docs/alignment/`, the section in the MR and the `alignment-needed` label are the signal: you review them and create the alignment tasks, first for the designer, then for the roles involved. It is a deliberate choice: in CI an agent that starts others multiplies costs and loops, and a change that breaks the contract is exactly the point where you want to decide.


## 3.8 Which model for which role {#modelli-per-ruolo}

Not every role needs the most capable model. The rule: **use the best model where a mistake costs the most, try cheaper models where the outcome can be verified and the damage of a mistake is contained.**

| Role | Recommended model | Alternative to try | Why |
|---|---|---|---|
| Backend | Claude Opus 5.5 | GPT-6 Astra, only as a trial | data, authentication and migrations: mistakes are costly |
| Devops | Claude Opus 5.5 | none | stays on Claude Code to keep hooks and permissions |
| Security | Claude Opus 5.5 | none | must reason about what is missing, not just what is there; runs only on request |
| Optimizer | Claude Opus 5.5 | DeepSeek V4 Pro, Mistral Large 4 | the outcome is measurable: timings before and after, green tests |
| Frontend | Claude Sonnet 5.5 | GPT-6 Sol, DeepSeek V4 Pro, Mistral Large 4 | follows a spec that is already written |
| Designer | Claude Sonnet 5.5 | none | must read screens and follow precise criteria |

List prices as of October 2026, in dollars per million tokens (input / output):

| Model | Price | Notes |
|---|---|---|
| Claude Opus 5.5 | 4 / 20 | |
| Claude Sonnet 5.5 | 2 / 10 | check the official page |
| GPT-6 Astra | 10 / 50 | costs more beyond 272,000 tokens of context |
| GPT-6 Sol | 2 / 10 | OpenAI's version for coding and agents |
| DeepSeek V4 Pro | 1.32 / 3.96 | open weights under the MIT license |
| Mistral Large 4 | 0.68 / 2.09 | released in October 2026: little experience with agents |

Other guidance:

- **Review in CI with a different model from the author.** If DeepSeek wrote the code, Claude reviews it, and vice versa.
- **Where the data ends up.** DeepSeek's official API processes data in China. For work or client code, use the same weights through a European or US provider, or host them yourself. Mistral is a European provider and processes data in the EU: for work code that is the main reason to prefer it.
- **DeepSeek or Mistral?** They are the two cheap alternatives for optimizer and frontend, and it is worth configuring both in LiteLLM (section 9.2) so you can move a role from one to the other by changing only the virtual key. DeepSeek has more track record as an agent; Mistral Large 4 is recent and has a lower list price. Mistral also has code-specialized models (the Devstral family) to try on the same roles. Decide by running the same task on both: PR delivered, turns used, cost (section 10.5).
- **Small open-weight models** (for example Qwen 3.8 27B) cannot handle the main roles; they are fine for small jobs like triaging issues or writing commit messages.
- **Benchmarks do not decide.** They are self-reported by the vendors or taken from different, non-comparable sources. What counts is the cost per delivered task on your code (section 10.5).

In Claude Code the model is set in each agent's frontmatter (`model: opus`, `model: sonnet`). To force a single model on all subagents and teammates:

``` {.sourceCode .json}
{
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet",
    "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1"
  }
}
```


## 3.9 Roles portable across harnesses {#ruoli-portabili}

The files in `.claude/agents/`, the `skills` field, hooks and agent teams are Claude Code features. If a role runs on another harness (architectures D and E), it must be made portable and protected again.


### One definition per role {#una-definizione}

Only Claude Code reads the files in `.claude/agents/`. OpenCode and Codex read `AGENTS.md` instead. To avoid writing each role twice, separate **what the role does** (portable) from **how each harness configures it** (specific):

    my-project/
    ├── AGENTS.md                    ← project rules for every harness
    ├── CLAUDE.md                    ← contains only: @AGENTS.md + Claude-only notes
    ├── docs/roles/
    │   ├── designer.md              ← role prompt, written once
    │   ├── frontend.md
    │   ├── backend.md
    │   ├── optimizer.md
    │   └── devops.md
    ├── .claude/agents/devops.md     ← Claude Code frontmatter + "follow docs/roles/devops.md"
    └── .opencode/agents/devops.md   ← OpenCode frontmatter + "follow docs/roles/devops.md"

In practice: the content of sections 3.2--3.6 (boundaries, non-negotiable rules, workflow) moves to `docs/roles/`, and each harness's file shrinks to the frontmatter plus a pointer. The routing rules of section 3.7 go into `AGENTS.md`, which `CLAUDE.md` imports.


### Protections do not travel on their own {#protezioni-harness}

This is the step not to skip. Hooks, `permissions.deny`, `isolation: worktree` and the `skills` field are Claude Code features: if you assign devops to a model running in OpenCode, **the hook that blocks `terraform apply` disappears.**

The protections must be rebuilt on two levels:

**In the harness**, where possible. OpenCode has its own permission system, configurable per agent in the frontmatter. Rules are evaluated in order and the last match wins, so the generic rule goes first:

``` {.sourceCode .markdown}
---
description: Pipelines, containers, infrastructure. Writes configuration, never applies it.
mode: subagent
permission:
  bash:
    "*": ask
    "terraform plan*": allow
    "helm template*": allow
    "terraform apply*": deny
    "kubectl apply*": deny
    "kubectl delete*": deny
    "helm upgrade*": deny
    "docker push*": deny
---

Follow the role instructions in docs/roles/devops.md.
```

**On the platform**, always. It is the only level that holds whatever model and whatever harness is running:

-   the daemon's machine has no cluster, cloud or registry credentials;
-   the daemon's Git token can only create branches and open MRs, never push to `main` or merge;
-   production environments require a manual approval in the pipeline.

If a protection exists only in a harness's configuration, treat it as a help, not a guarantee.


### What does not work across harnesses {#limiti-harness}

-   **Agent teams.** Mailbox, shared task list and direct messages between agents (chapter 7) are Claude Code features. Between a Claude Code agent and an OpenCode one, coordination goes through the dashboard: comments on the issue and dependencies between issues.
-   **Agent skills and memory.** The `skills` field and `memory: project` have no identical equivalents in other harnesses. Whatever must apply to everyone goes in `AGENTS.md` or in `docs/roles/`.
-   **Automatic review in CI.** The workflows in chapter 8 use the Claude Code action. They can stay on Claude even when another model wrote the code, and it is a good combination: the reviewer is not the author.


## 3.10 Security, on request only {#agente-security}

The sixth role looks for vulnerabilities in two ways: it reads the code, and it attacks the running application, locally or on staging, to confirm what it suspects. Then it proposes fixes, but **does not apply them**: attacker and fixer stay separate, like author and reviewer. The fixes become normal tasks for backend, frontend or devops.

**It is not part of the standard sequence.** A full assessment takes 30--40 turns on Opus, about \$3--4 with the assumptions in section 2.8. Running it after every change would multiply the cost without finding much more. You ask for it, explicitly, when the application is complete and then before every release. That is why its `description` tells the lead never to delegate anything to it on its own initiative, and `AGENTS.md` lists it among the on-request roles together with the optimizer.

``` {.sourceCode .markdown}
---
name: security
description: Application security assessment (code review and attacks on the
  running app, local or staging only) with suggested fixes. Use ONLY when
  the user explicitly asks for a security assessment, never on your own.
tools: Read, Grep, Glob, Bash, Write
model: opus
effort: high
skills:
  - security-review
color: red
memory: project
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./.claude/hooks/security-scope.sh"
    - matcher: "Write"
      hooks:
        - type: command
          command: "./.claude/hooks/security-writes.sh"
---

You are the team's application security engineer. You look for
vulnerabilities by reading the code and by attacking the running application,
and you propose fixes. You do not fix anything yourself.

## When you run
Only when the user explicitly asks for a security assessment, typically once
the application is complete or before a release. If you were invoked as a
routine step after an ordinary change, say so and stop.

## Scope: the rule that comes before all others
- Send requests only to the hosts listed in `.claude/security-scope`
  (`localhost` and `127.0.0.1` by default, plus the staging host if the user
  added it). Never production, never third-party services, never any other
  host, even if the code mentions it.
- Use test accounts and test data only. No real personal data. No
  destructive tests (data deletion, load or denial-of-service tests) unless
  the user explicitly asks and the target is disposable.
- Do not edit application code, tests or configuration. You write only
  under `docs/security/`.

## What you check
1. **Access control.** Every route checks who the caller is and whether they
   own the resource: change IDs, swap users, call admin routes as a normal
   user.
2. **Authentication and sessions.** Login, registration, password reset,
   token lifetime and storage, logout, brute-force protection, rate limiting.
3. **Injection.** SQL/NoSQL, command, template, path traversal, SSRF in any
   feature that fetches URLs.
4. **Input and output handling.** Validation at the edge, stored and
   reflected XSS, file uploads, CORS, CSRF.
5. **Secrets and configuration.** Committed secrets, debug modes, verbose
   errors, security headers, cookie flags.
6. **Dependencies.** Known vulnerabilities in the lockfiles (`npm audit`,
   `pip-audit` or the stack's equivalent).
7. **Integrations.** What the app trusts from other services without
   verifying it.

## How you work
1. Read `AGENTS.md`, the routes and the data model, and list the attack
   surface before testing anything.
2. Run the static tools available in the project (for example semgrep and the
   dependency audit). Say which ones are missing instead of skipping them.
3. Start the application locally, or use the staging host in scope, and
   confirm each suspected issue with a minimal, non-destructive proof.
4. What you could not confirm is reported as SUSPECTED, with the reason.

## Report
Write `docs/security/<yyyy-mm-dd>-assessment.md` and summarize it in your
final message. One entry per finding, most severe first:

  [CRITICAL|HIGH|MEDIUM|LOW|SUSPECTED] title
  where:  file:line or endpoint
  impact: what an attacker gets
  proof:  the request or steps that reproduce it, with test data
  fix:    the change to make, and the role that owns it (backend, frontend, devops)

End with what you did not test and why. The fixes become separate tasks for
the owning roles; once they are merged, the user can ask you to re-test only
those findings.
```

Its tools do not include `Edit`, and `Write` goes through a hook that only accepts paths under `docs/security/`. The second hook restricts the network: every URL in a command must point to a host listed in `.claude/security-scope`, and port scanners, brute-force tools and reverse shells are blocked.

``` {.sourceCode .bash}
#!/bin/bash
# .claude/hooks/security-scope.sh
# Lets the security agent reach only the hosts listed in .claude/security-scope.
# A guardrail, not a sandbox: for real isolation run the agent where the
# network only reaches local and staging.

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[ -z "$CMD" ] && exit 0

SCOPE_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/security-scope"
ALLOWED=$(grep -vE '^[[:space:]]*(#|$)' "$SCOPE_FILE" 2>/dev/null | sed -E 's/[[:blank:]]+//g; /^$/d')
[ -z "$ALLOWED" ] && ALLOWED=$(printf 'localhost\n127.0.0.1')

# every host that appears in a URL must be in scope
HOSTS=$(echo "$CMD" | grep -oE '[a-zA-Z][a-zA-Z0-9+.-]*://[^/:?#"'"'"'[:space:]]+' | sed -E 's#^[^:]+://##; s#^.*@##' | sort -u)
for h in $HOSTS; do
  if ! echo "$ALLOWED" | grep -qxF "$h"; then
    echo "Blocked: $h is not in .claude/security-scope." >&2
    echo "Test only in-scope hosts (local or staging). Ask the user if another host is needed." >&2
    exit 2
  fi
done

# no port scanners, brute-force tools or remote shells
if echo "$CMD" | grep -qE '(^|[;&|[:space:]])(nmap|masscan|hydra|medusa|nc|ncat|socat|ssh|telnet)([[:space:]]|$)'; then
  echo "Blocked: use HTTP tooling against in-scope URLs; scanners, brute-force tools and remote shells are not allowed." >&2
  exit 2
fi
exit 0
```

``` {.sourceCode .text}
# Hosts the security agent may send requests to, one per line.
# CUSTOMIZE: add your staging host (for example staging.your-domain.com). Never production.
localhost
127.0.0.1
```

A few things to know:

-   **The hook is a guardrail, not a sandbox.** It checks the URLs written in the command, not those a script builds at runtime. If the agent runs on a server or in CI, the real protection is a network that can reach only the local and staging environments.
-   **Never production in scope.** A security test on real data can modify or expose it, and on a third-party service it is an attack on systems that are not yours.
-   **Reports stay out of Git.** They contain working proofs of the vulnerabilities: the template puts `docs/security/` in `.gitignore`. Remove it only if the repository is private and you want to keep their history.
-   **How to ask for it.** Locally: `> use the security agent to run a full security assessment of the app`. With architecture C or D: the `agent:security` label on an issue that describes the scope. After the fixes, ask for a re-test of only the issues found, which costs much less than a full assessment.
-   **It does not replace human review.** Before going to production with personal data or payments, a check done by a person is still necessary: this role finds the most common problems early and cheaply, it certifies nothing.


# 4. Improving the project {#migliorare}

The measures in this chapter apply to every architecture. None is needed on day one: add them after you have watched the agents work, one at a time, measuring before and after.


## 4.1 How skills work in agents {#skill-agli-agenti}

A skill is a folder containing a `SKILL.md` file: instructions and materials that Claude loads when needed. They live in the filesystem, not in your profile: in `~/.claude/skills/` (personal), in `.claude/skills/` (project, versioned in the repository) or inside a plugin.

One point not to take for granted: **subagents do not inherit the main session's skills.** A skill working in your session does not mean the frontend sees it. It must be declared in the agent's frontmatter, with the `skills` field:

``` {.sourceCode .yaml}
---
name: frontend
description: Implements and changes the user interface...
skills:
  - design-system
  - accessibility-checklist
---
```

The field injects the **full content** of each skill into the agent's context at startup. Four practical rules follow:

-   **They have weight.** You pay for every preloaded skill at every start of every agent. Give each role only its own: `design-system` to designer and frontend, not to backend and devops.
-   **Typos make no noise.** Claude Code silently ignores frontmatter fields it does not recognize: writing `skill:` or `Skills:` instead of `skills:` produces no error, it produces an agent without skills.
-   **Not every skill can be preloaded.** Those with `disable-model-invocation: true` stay out, and preloading loads nothing without telling you.
-   **A plugin's skills are referenced with the plugin prefix**, in the form `plugin-name:skill-name`.

A test to repeat every time you change an agent: start it and ask which skill instructions it received at startup. If it mentions none, the field is not working. With agent teams the check matters even more: a bug was reported where the `skills` field was ignored on teammates started as separate processes, and it is not necessarily fixed in your version.


## 4.2 Finding skills with find-skills {#find-skills}

find-skills is a Vercel skill that helps you search for and install other skills from the open Agent Skills ecosystem. It is the most installed skill on skills.sh, the reference directory. Install it on your computer, at user level, not in the project: it is for you to search with, not for the agents.

```bash
npx skills add vercel-labs/skills -s find-skills -g
```

From there you can ask Claude "find a skill for …", or use the CLI directly:

```bash
npx skills find "react performance"          # search the skills.sh registry
npx skills add <owner/repo> -s <skill> -a claude-code -y   # install into the project
npx skills list                              # list installed skills
npx skills remove <skill>                    # remove a skill
npx skills update                            # update: read what changes first
```

The method the skill suggests, which this guide extends:

1. **Look at the skills.sh leaderboard first.** Widely installed skills are more battle-tested.
2. **Search by keyword**, trying synonyms (`deploy`, `ci-cd`, `github actions`).
3. **Check the quality:** at least a thousand installs, a reliable source (Anthropic, Vercel, Microsoft, Sentry, Supabase…), a repository with a reasonable number of stars.
4. **Read the `SKILL.md` before installing.** A skill runs with the agent's permissions: look for suspicious scripts and instructions.
5. **Measure the weight.** The description enters every session; the body enters when the skill is used. Prefer skills that keep references in separate files, read only when needed.
6. **Look for duplicates.** If a new skill does the same thing better than one you have, remove the old one: keeping both costs tokens and confuses the model when choosing.

If the skills.sh registry does not respond from your network, the command-line search returns "no results" without errors. In that case browse the skills.sh site and install with `npx skills add`, which downloads from GitHub.


## 4.3 Recommended skills for the five roles {#skill-consigliate}

This list comes from a search on skills.sh with the method in section 4.2: popularity, reliable source, then reading and measuring each candidate skill. Of 57 candidates, 12 remain. The criterion is the balance between quality and tokens: where two skills do the same thing the better one stays, or on a tie the lighter one.

Every skill costs in two ways:

-   **The description** enters every session of every agent, whether it uses it or not. The 12 in the list add up to about 870 tokens.
-   **The body** enters only when the agent opens the skill, or at startup if it is preloaded with `skills:`. Reference files are read only when needed.

Hence the rule: **preload only what the role uses in almost every task**, leave the rest on demand.

| Role              | Skill                              | Source and installs | Use                                        |
|------------------|------------------|------------------|------------------|
| Designer           | `frontend-design`                  | Anthropic, 976K       | preloaded                                |
| Designer           | `web-design-guidelines`            | Vercel, 724K          | on demand, for review              |
| Frontend           | `vercel-react-best-practices`      | Vercel, 791K          | preloaded, React only                |
| Frontend           | `webapp-testing`                   | Anthropic, 175K       | on demand                                |
| Frontend, backend  | `tdd`                              | Matt Pocock, 1.1M     | preloaded                                |
| Backend            | `api-design-principles`            | wshobson/agents       | preloaded                                |
| Backend, optimizer | `supabase-postgres-best-practices` | Supabase, 441K        | preloaded in the backend, Postgres only |
| Backend            | `security-review`                  | Sentry, 19.6K         | on demand, before the PR                |
| Optimizer          | `code-simplifier`                  | Sentry, 8.4K          | preloaded                                |
| Devops             | `gha-security-review`              | Sentry, 4.6K          | preloaded                                |
| Devops             | `github-actions-templates`         | wshobson/agents       | on demand                                |
| All              | `diagnosing-bugs`                  | Matt Pocock, 763K     | on demand                                |

Notes on the choices:

-   **Sentry's `security-review`** was the only one that passed an independent comparison of five security skills: it reports only high-confidence issues and checks where the data comes from.
-   **`gha-security-review`** checks GitHub Actions workflows, which in architectures C and D become the machine the agents run on.
-   **`web-design-guidelines`** downloads about 2,000 tokens of up-to-date rules from GitHub at every review: the designer needs `WebFetch`, which it already has.
-   **`diagnosing-bugs`** includes a script meant for a person at the terminal: it is worth more locally than on GitHub Actions.
-   **Stack variants.** Without React or Postgres remove the related skills. On GitLab `gitlab-ci-patterns` takes the place of `github-actions-templates`. With Terraform add HashiCorp's `terraform-style-guide`.

The install commands are in section 5.4. This is the assignment to the five agents (`design-system` is the project skill from section 5.2):

``` {.sourceCode .yaml}
# designer.md    skills: [design-system, frontend-design]
# frontend.md    skills: [design-system, vercel-react-best-practices, tdd]
# backend.md     skills: [api-design-principles, supabase-postgres-best-practices, tdd]
# optimizer.md   skills: [code-simplifier, vercel-react-best-practices]
# devops.md      skills: [gha-security-review]
# security.md    skills: [security-review]
```

On-demand skills work better if the role prompt says when to use them, for example in the backend: "before opening the PR, run the security-review skill on the diff".

**What was excluded and why.**

| Excluded                                                                         | In favor of                                 | Reason                                                                                                         |
|------------------------|------------------------|------------------------|
| `taste-skill`, `ui-ux-pro-max`, `impeccable`                                    | `frontend-design` + `web-design-guidelines` | they overlap; `taste-skill` weighs 22,000 tokens, `ui-ux-pro-max` runs scripts on a large data archive |
| Currents' `playwright-best-practices`                                         | `webapp-testing`                            | 6,100 body tokens versus 900; worth reconsidering for a large end-to-end suite                              |
| TDD from Superpowers and from ECC                                                     | `tdd`                                       | same function, 2.7 to 6 times heavier                                                                |
| Superpowers' `systematic-debugging`                                           | `diagnosing-bugs`                           | same function, many more reference files                                                                 |
| ECC's `security-review` and `security-scan`                                      | Sentry's `security-review`                 | lower quality in the comparison and the same name: the two clash                                             |
| ECC's `api-design`, `backend-patterns`, `postgres-patterns`, `docker-patterns` | the choices above                             | duplicates of 1,000--4,000 tokens each                                                                        |
| `verification-before-completion`, `verification-loop`                           | the `TaskCompleted` hook (section 7.5)        | the hook enforces it without spending tokens                                                                         |
| code review skills from Sentry, Pocock, Superpowers                             | the `code-review` plugin in CI (section 8.1) | review is already there                                                                                           |
| `git-guardrails-claude-code`                                                    | `permissions.deny` (section 5.5)            | protection already present                                                                                        |
| `improve-codebase-architecture`                                                 | none                                     | it is marked manual-only: agents cannot preload it                                                    |

The skills in the list were read before recommending them. The dangerous commands they contain are examples of vulnerabilities to recognize; the only scripts are Anthropic's test scripts, a debugging template and an API example.


## 4.4 Third-party packages: Everything Claude Code {#importare-ecc}

Everything Claude Code, now shortened to **ECC**, is an open-source collection of agents, skills, commands, rules and hooks for Claude Code and other tools. It is not an Anthropic product: it is third-party software and must be treated as such (see step 8). We use it as an example because it brings every kind of component together, each with different import rules.

> **Do not install it in full in the team's project.** ECC contains 311 skills, all model-invocable, and their descriptions weigh about 25,600 tokens. With the full plugin that weight enters every session of every agent, even when no skill is used. Over 70 tasks the cost is about \$18 a month with Opus and about \$60 with DeepSeek without a cache discount, versus about 870 tokens for the list in section 4.3. On top of that some ECC skills have the same name as the recommended ones, such as `security-review`. Use the steps below to try it on a test branch; for the team use the ECC installer's selective installation (the `--with` and `--without` options, see its README) and take only what does not duplicate section 4.3. If you have already installed it: `/plugin disable ecc@ecc`.

> **Watch the names.** The project was renamed: the official repository is `affaan-m/ECC` and the plugin identifier is `ecc@ecc`. Many tutorials and forks in circulation still use the old `everything-claude-code@everything-claude-code`. The project recommends installing only from its official channels: repository `affaan-m/ECC`, plugin `ecc@ecc`, npm package `ecc-universal`, site `ecc.tools`.

The commands below are those given in the project's README. The project changes fast: compare them with the current README before running them.

### What comes with the plugin and what does not

| Component | Comes with the plugin? | Worth knowing                                                                                     |
|------------------------|------------------------|------------------------|
| Agents     | yes                 | for security, plugin subagents ignore the `hooks`, `mcpServers` and `permissionMode` fields |
| Skills      | yes                 | they are not inherited by your agents: they must be declared with `skills:` (section 4.1)              |
| Commands    | yes                 | they have a prefix: `/ecc:plan`, not `/plan`                                                   |
| Hooks       | yes                 | they run in the project's sessions and add to yours                                       |
| Rules     | **no**             | a plugin cannot distribute them: they are copied by hand                                             |

### Step 1 --- Choose a single installation path

There are two, and they are **alternatives**: the plugin (recommended to start) or the project's installer (`npx ecc-universal install --guided`), which lets you choose which components to copy. If you install the plugin and then also run the full installer you get duplicated commands, hooks and skills: the README warns about it explicitly. This example follows the plugin path.

### Step 2 --- Install the plugin

Inside a Claude Code session, in the project folder:

    /plugin marketplace add https://github.com/affaan-m/ECC
    /plugin install ecc@ecc

Claude Code asks for the scope (user, project or local): choose **project**, so ECC does not affect the other repositories you work on.

### Step 3 --- Declare it in the repository (optional)

So that the marketplace is offered to anyone who opens the project, add to `.claude/settings.json`:

``` {.sourceCode .json}
{
  "extraKnownMarketplaces": {
    "ecc": {
      "source": { "source": "github", "repo": "affaan-m/ECC" }
    }
  },
  "enabledPlugins": { "ecc@ecc": true }
}
```

### Step 4 --- Copy the rules by hand

``` {.sourceCode .bash}
git clone https://github.com/affaan-m/ECC.git /tmp/ecc
mkdir -p .claude/rules/ecc
cp -r /tmp/ecc/rules/common .claude/rules/ecc/
ls /tmp/ecc/rules        # pick your language's folder
cp -r /tmp/ecc/rules/<language> .claude/rules/ecc/
```

Keeping them in an `ecc/` subfolder separates their rules from yours. Read them before copying them: they end up as instructions in every session.

### Step 5 --- Verify

    /plugin                                  # ecc must show as installed and enabled
    /agents                                  # the plugin's agents appear next to yours
    /ecc:plan "add the profile page"         # a plugin command, with its prefix

### Step 6 --- Connect it to the five agents

The safest way: **your five agents stay the team, ECC is the library they draw from.** You have two options.

**a) Declare the plugin's skills in the agents that need them:**

``` {.sourceCode .yaml}
---
name: backend
description: APIs, data model, migrations...
skills:
  - ecc:search-first
---
```

You will find the exact skill names in the repository's `skills/` folder. If you get the name wrong the agent starts without the skill and without errors: use the test in section 4.1.

**b) If you need an ECC agent, do not use it from the plugin: copy it** into `.claude/agents/`, rename it and adapt it to the file boundaries in section 3.7. As a file in your project it supports `hooks`, `mcpServers` and `permissionMode` again, which are ignored in the plugin version.

The case to avoid is replacing `devops` with an equivalent agent taken from the plugin: it would lose the `block-infra-commands.sh` hook, i.e. the protection section 3.6 considers non-negotiable. The same goes for the designer and its Playwright server.

### Step 7 --- What can go wrong

-   **Duplicates.** Plugin plus full installer: see step 1.
-   **Hooks adding to yours.** ECC's hooks are added to yours: frontend lint, the devops command block, the `TaskCompleted` gate. Try them first on a test branch and, if the guided installer offers a hook profile, start from the lightest.
-   **Token cost.** Every extra agent, skill and command adds descriptions to the context of every session; with agent teams every teammate reloads them. Measure before and after (`/cost` with an API key, `/usage` with a subscription): a package this large shifts the baseline consumption.
-   **Rules conflicting with yours.** If an ECC rule says one thing and `CLAUDE.md` another (for example about the commit flow or tests), behavior becomes unpredictable: reconcile them by hand.
-   **Updates.** `/plugin update ecc` brings in new content without you rereading it: read the release notes first.

### Step 8 --- Treat it as third-party code

-   Hooks are shell commands run with your permissions and MCP configurations can start processes: before enabling the package, read the repository's hooks folder and MCP configurations.
-   Install only from `affaan-m/ECC`: forks and clones with similar names are numerous.
-   With the npm installer pin the version (`ecc-universal@<version>`) instead of following the latest.
-   The project offers a scanner, `npx -y ecc-agentshield scan --path .`: it is a useful first check, but it is written by the same team and does not replace your own reading.
-   In the CI workflows of levels 3 and 4 do not enable it unless needed: there the agents run with secrets.

### Step 9 --- How to disable it

    /plugin disable ecc@ecc

If something behaves strangely after installation, disable the plugin and repeat the same request: you immediately see whether the problem is ECC or your agents.


## 4.5 Automatic project analysis: claude-code-setup {#claude-code-setup}

claude-code-setup is an official Anthropic plugin that analyzes the repository and proposes tailored automations, at most one or two per category: MCP servers, skills, hooks, subagents and slash commands. Each proposal should cite the evidence found in the repository (files, dependencies, existing `.claude` configuration). It applies nothing: it produces a report.

**When to use it.** Not on the empty repository: the guide already defines agents, hooks, permissions and skills, and you would get duplicates. Use it after the first two weeks of work, when the stack is concrete, as a check. It can notice things the guide could not foresee: a hook for your language's formatter, an MCP server for the database you chose, a command for a sequence you repeat often.

**How to use it without wasting tokens.**

1. Install it for yourself, at user level, not in the project: that way it does not enter the agents' sessions or the CI jobs.
   ```
   /plugin install claude-code-setup@claude-plugins-official
   /reload-plugins
   ```
   If the marketplace is missing: `/plugin marketplace add anthropics/claude-plugins-official`.
2. From the repository root ask `recommend automations for this project`, or a narrower question such as `what hooks should I use`.
3. Run `git status --short` before and after: the output must be the same.
4. Weigh each proposal against the guide and discard duplicates. Be careful with MCP servers: each one adds tool descriptions to every session.
5. Adopt one proposal at a time, with a diff to review, then disable the plugin.


## 4.6 Reducing token usage {#ridurre-token}

The levers that really matter are settings and habits, not extra tools. In order of effectiveness for a project like this:

1. **Reasoning level per role.** Reasoning is paid as output (\$20 per million tokens on Opus 5.5) and the default level is high. Lower it where the work follows a spec, keep it high where analysis and caution are needed:

   ```yaml
   # designer.md, frontend.md
   effort: medium
   # backend.md, optimizer.md, devops.md
   effort: high
   ```

   It is the first thing to try: measure cost and quality on ten or so tasks before and after.
2. **A fresh context for each task.** The biggest cost is the context that grows during the work. In architectures C and D every task already starts from scratch. Locally use `/clear` between tasks and `/compact` when a session gets long.
3. **Small tasks and clear specs.** Rework is the variable that weighs most in the estimates in section 2.8.
4. **Skills and plugins with judgment.** Only the skills in section 4.3, preloaded only where needed; no package installed in full (section 4.4).
5. **Models per role** as in section 3.8.


### Other habits that help {#abitudini}

-   **Isolate verbose output.** Running tests inside a subagent instead of the main session keeps thousands of log lines out of your context: only the summary comes back.
-   **A concise `CLAUDE.md`.** It is loaded in every single session and in every subagent. You pay for every useless line many times.
-   **`--max-turns`** on every CI job, and a timeout at workflow level.
-   **Concurrency controls** on GitHub Actions, so you do not get ten parallel runs from a burst of comments.


### Compression skills: caveman {#caveman}

The most installed skill for reducing tokens is caveman: it makes the model answer telegraphically, leaving code, commands and errors untouched. Issues, PRs, commits and documentation stay in normal prose, and so do security warnings.

**The real saving is small.** The README promises 65–75% less output; independent measurements find from 8.5% (an A/B test on 86 tasks, with no loss of quality) to 23%, and only 4% compared with the plain instruction "be concise". On total spend the estimated effect is 1–3%, because caveman only shortens the visible prose: it does not touch the context re-read at every step, the code written or the reasoning. In agents working in CI the visible prose is almost nil, so the saving is practically zero.

The `caveman-compress` variant compresses `CLAUDE.md`, but it overwrites the file and moves the readable copy out of the repository: in a versioned project it is better to write a short `CLAUDE.md` by hand.

If you like the terse style, install it only for your interactive session:

```bash
npx skills add juliusbrussee/caveman -s caveman -g
```


### Code maps: Graphify and similar tools {#mappe-del-codice}

Tools like Graphify build a map of the repository: who imports what, who calls what, which modules depend on which. The agent queries the map (`graphify query "…"`) instead of opening files one by one. For code the map is built locally, with a parser, without model calls: building it costs no tokens.

**When it pays off.** On large or unfamiliar repositories, where a large share of tokens goes into exploration. The sources that discuss it point to a threshold around 500 files. The project's own benchmark is on a repository of about a million lines, and there it mostly measures better answer coverage (from 71% to 82%), not a saving. The very high saving figures in circulation ("up to 70 times") have no published measurement method.

**For this guide's app, about 10,000 lines and a hundred or so files, it does not pay off yet.** The reasons:

-   exploration is a small part of the spend: tokens go mostly into the context that builds up during the task (section 2.8);
-   the code is written by the agents and changes constantly, so the map must be rebuilt at every commit or every Actions job;
-   on Claude Code it is installed with a hook that diverts reads and searches to the map: one more behavior to keep under control in every agent.

Reconsider it when the repository goes past a few hundred files, or if you have the agents work on a large existing codebase. Until then the levers that matter are these: small tasks, a short `CLAUDE.md`, verbose output isolated in subagents, skills preloaded only where needed (section 4.3).

If you adopt it: the official repository named in the README is `Graphify-Labs/graphify`, the package is called `graphifyy` (with two y's), and the README also promotes a paid cloud version. For code alone everything stays local; for documents and images it sends the content to the configured model.


## 4.7 Claude Code mods {#mod}

Mods are changes to the interface and behavior of Claude Code itself: side panels, a line above the prompt, status bar entries, notifications, slash commands and hooks written in TypeScript, with real state and logic. They are installed as small plugins on the computer where you use Claude Code.

They are useful only in the interactive architectures (A and B). Some useful uses:

- **a team dashboard:** active teammates, each one's tasks, blocked tasks;
- **spend always visible:** session cost in the status bar and a warning beyond a threshold;
- **an `/assign backend 42` command** that labels the issue and starts the architecture C or D workflow;
- **control of messages between sessions:** with the `session.send` and `session.receive` events a mod can strip secrets from outgoing messages or discard unverified incoming ones.

They are not needed in CI jobs, where nobody looks at the interface, nor with harnesses other than Claude Code. A message arriving from another session never counts as your approval of a permission, with or without mods.


# 5. Common preparation {#preparazione}

These steps apply to every architecture. Do them once, in order, before the chapter of the architecture you chose.


## 5.1 Installing Claude Code {#installare-claude-code}

Claude Code is installed with the official script or via npm:

``` {.sourceCode .bash}
# installer (recommended: puts the binary in ~/.local/bin)
curl -fsSL https://claude.ai/install.sh | bash

# or via npm
npm install -g @anthropic-ai/claude-code

claude --version
```

Then check authentication: you can use a Claude subscription (Pro, Max, Team, Enterprise) or an API key from the Claude Console. For CI use you will need one of the two as a secret:

``` {.sourceCode .bash}
# token tied to your subscription, useful for CI
claude setup-token
# → prints the value to store as CLAUDE_CODE_OAUTH_TOKEN
```


## 5.2 Creating the project structure {#struttura-progetto}

Everything that defines the team lives inside the repository, so it is versioned and shared:

    my-project/
    ├── CLAUDE.md                    ← project rules and the team's rules of engagement
    ├── .claude/
    │   ├── settings.json            ← shared configuration (versioned)
    │   ├── settings.local.json      ← personal overrides (in .gitignore)
    │   ├── agents/
    │   │   ├── designer.md
    │   │   ├── frontend.md
    │   │   ├── backend.md
    │   │   ├── optimizer.md
    │   │   └── devops.md
    │   ├── skills/
    │   │   └── design-system/SKILL.md
    │   └── hooks/
    │       ├── lint-frontend.sh
    │       ├── block-infra-commands.sh
    │       └── update-task.sh
    ├── .mcp.json                    ← shared MCP servers
    ├── .github/workflows/claude.yml  (or .gitlab-ci.yml)
    └── docs/
        └── design-decisions.md      ← written memory shared by the agents

Important note: files in `.claude/agents/` are hot-reloaded. If you change an agent while the session is open, the next delegation already uses the new version. The only exception is creating the `agents/` folder itself: if it did not exist when the session started, you must restart Claude Code.

### Starting from the template {#template-progetto}

The quickest way is to copy the [project template](https://claude.ai/artifact/QB6PBe2m3R9xtKmrpxcXnQ): a ready-made repository with the agents (designer, frontend, backend and devops for everyday work, optimizer and security on request), `AGENTS.md` and `CLAUDE.md`, the role prompts in `docs/roles/`, the hooks, the `design-system` skill, the GitHub workflows, the GitLab variant, the OpenCode agents and the LiteLLM gateway. From the template page you download the zip or copy the files one by one. It contains only the team configuration, not the application code. File names, commands and agent prompts are in English, like all the code examples in this guide: models follow them well in any language, and the repository stays readable by anyone.

**Filling it in with Claude.** The template includes `SETUP.md`, an instruction file written for a Claude session. Copy the template into the new project's folder, start Claude Code and type:

> Read SETUP.md and set up this project

Claude reads the file and interviews you in blocks: project name and Git platform, stack, build, test and lint commands, each role's folders, design system, chosen architecture, models, skills. If the folder already contains code, it reads it first (`package.json`, `pyproject.toml`, `CMakeLists.txt`, existing workflows...) and proposes values for you to confirm instead of asking. Before touching the files it shows you the full list of changes and waits for your yes; then it edits, deletes what the chosen architecture does not use, runs the checks (agent frontmatter, script syntax, a test of the hook that blocks infrastructure commands) and finishes with what remains to be done by hand: secrets, versions to pin, labels, branch protection. Then it moves on to the second, mandatory part: if the project does not have a design yet (`docs/design/project.md` with `ready: yes`), it opens a design studio session and the setup is not finished until the design is ready (section 3.2). You can answer in any language: the files stay in English.

`SETUP.md` is useful even if you prefer to do it by hand: it contains the map of which answer goes into which file. At the end it is worth deleting it, because otherwise every session that explores the repository finds it and reads it.

**By hand.** After copying the template, `grep -rn "CUSTOMIZE" .` lists all the points to adapt. The table summarizes what to change:

| File | What to change | When |
|---|---|---|
| `AGENTS.md` | project name, stack, build and test commands, each role's folders | always |
| `docs/roles/*.md` | boundary folders, commands, stack-specific rules | always |
| `.claude/skills/design-system/SKILL.md` | your design system's tokens, components and rules | always |
| `.claude/hooks/gate-test.sh` | the command that runs the tests | always |
| `.claude/hooks/lint-frontend.sh` | file extensions and linter | always |
| `scripts/install-skills.sh` | remove the skills that do not concern your stack (section 4.3) | always |
| `.claude/agents/*.md` | a `skills:` field consistent with the installed skills; `model` and `effort` (section 3.8) | if you change stack or budget |
| `.github/CODEOWNERS` | your user and the real critical paths | architectures C and D |
| `.claude/settings.json` | extra commands to deny, secret paths (section 5.5) | if needed |
| `.github/workflows/ci.yml`, `.gitlab/ci/ci.yml` | toolchain, build and test commands, lockfile for the cache (section 5.6) | always |
| `ci/scanners.env` | tool versions, vulnerability threshold, license policy | if the defaults do not suit you |
| `.github/workflows/*.yml`, `.gitlab-ci.yml.example` | in `--allowedTools`, your stack's build and test commands (section 8.5) | architectures C and D |
| `.claude/security-scope` | the staging host security may test, besides `localhost` (section 3.10) | if you use security on staging |
| `.github/workflows/agents.yml` | OpenCode action version, secret and model | architecture D |
| `opencode.json`, `.opencode/agents/*.md` | LiteLLM address, command permissions | architectures D and E |
| `infra/litellm/*` | models, domain, image version, `.env` file | only with LiteLLM |

`settings.json` and `opencode.json` do not allow comments, so their review points are only in this table. Third-party skills are not included: `scripts/install-skills.sh` installs them (section 5.4).

What to keep depending on the chosen architecture:

- **A and B:** `AGENTS.md`, `CLAUDE.md`, `docs/` and `.claude/` are enough; you can delete `.github/`, `.opencode/`, `opencode.json` and `infra/`. For B set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` to `1` in `.claude/settings.json`.
- **C:** like A plus `.github/`; run `scripts/create-labels.sh` and follow chapter 8.
- **D:** like C plus the `OPENCODE_ROLES` repository variable, `opencode.json` and `.opencode/`; `infra/litellm/` only with variant 2 (section 9.3).
- **E:** `docs/roles/`, `.opencode/`, `opencode.json` and `infra/litellm/` on the daemon's server; the `agents.yml` workflow is not needed.

A structural detail: in the template the agents in `.claude/agents/` contain only the frontmatter and point to the prompt in `docs/roles/<role>.md`, which OpenCode reads in turn. It is the one-definition-per-role version from section 3.9; it costs one file read at every agent start. If you use only Claude you can paste the prompt directly into the agent file, as in the examples in chapter 3.

### Starting from scratch

To create it by hand:

```bash
mkdir my-project && cd my-project && git init
mkdir -p .claude/agents .claude/skills/design-system .claude/hooks docs/design
echo ".claude/settings.local.json" >> .gitignore
```


## 5.3 Writing the agents and CLAUDE.md {#scrivere-agenti}

If you started from the template in section 5.2 these files already exist: the steps below become "reread and adapt", following the `CUSTOMIZE` comments.

1. **The agents.** Create the five files from chapter 3 in `.claude/agents/`: `designer.md`, `frontend.md`, `backend.md`, `optimizer.md`, `devops.md`. Adapt folder boundaries and commands to your stack.
2. **`CLAUDE.md`.** Start from the example in section 3.7 and write the stack, the build and test commands, the delegation rules by file boundary. Keep it short: it is re-read at every step.
3. **The `design-system` project skill.** Write your design system's tokens and rules in `.claude/skills/design-system/SKILL.md`; designer and frontend preload it.
4. **The hook scripts.** `block-infra-commands.sh` is in section 3.6. The frontend lint script can be simple:

   ```bash
   #!/bin/bash
   # .claude/hooks/lint-frontend.sh: lint only the file that was just edited
   INPUT=$(cat)
   FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
   case "$FILE" in
     *.ts|*.tsx|*.js|*.jsx) npx eslint --fix "$FILE" >/dev/null 2>&1 || true ;;
   esac
   exit 0
   ```

   Make them executable, otherwise the hook fails instead of blocking:

   ```bash
   chmod +x .claude/hooks/*.sh
   ```
5. **Verify.** Check that the agent files parse correctly, then start Claude Code and ask for the list of available agents:

   ```bash
   claude plugin validate .claude/agents
   claude
   ```

   A typo in the frontmatter gives no error: the field is ignored. If an agent is missing from the list, recheck `name` and `description`.


## 5.4 Installing the skills {#installare-skill}

The skills and their use per role are explained in section 4.3. The commands, from the repository root:

```bash
npx skills add anthropics/skills -s frontend-design -s webapp-testing -a claude-code -y
npx skills add vercel-labs/agent-skills -s web-design-guidelines -s vercel-react-best-practices -a claude-code -y
npx skills add mattpocock/skills -s tdd -s diagnosing-bugs -a claude-code -y
npx skills add supabase/agent-skills -s supabase-postgres-best-practices -a claude-code -y
npx skills add getsentry/skills -s security-review -s code-simplifier -s gha-security-review -a claude-code -y
npx skills add wshobson/agents -s api-design-principles -s github-actions-templates -a claude-code -y
```

Remove the skills that do not concern your stack (React, Postgres, GitHub Actions). Then add to each agent the `skills:` field with the skills to preload, as in the table in section 4.3, and commit `.claude/skills/` and `skills-lock.json`.


## 5.5 Protecting the repository {#proteggere-repository}

This is the part not to delegate. Control is enforced on the platform, not in prompts: a prompt is a request, a branch protection is a rule.

**On the repository:**

-   Protect `main`: no direct push, MR required, at least one approval --- yours.
-   Explicitly forbid auto-merge and never give approval permission to the identity the agents run as.
-   If you work on GitHub, check that the GitHub App does not have permission to approve reviews (it does not by default).
-   Add a CODEOWNERS that assigns you as reviewer on critical paths: migrations, authentication, deploy configuration, CI pipelines.
-   Require green CI before merging.

**In the agents' configuration:**

-   No agent has `bypassPermissions`. If someone must have it, let it be an explicit, temporary choice, not the default in `settings.json`.
-   Use `permissions.deny` for commands that must not exist:

``` {.sourceCode .json}
{
  "permissions": {
    "deny": [
      "Bash(git push origin main:*)",
      "Bash(git push --force:*)",
      "Bash(gh pr merge:*)",
      "Bash(glab mr merge:*)",
      "Bash(terraform apply:*)",
      "Bash(terraform destroy:*)",
      "Bash(kubectl apply:*)",
      "Bash(kubectl delete:*)",
      "Bash(helm upgrade:*)",
      "Bash(helm install:*)",
      "Bash(docker push:*)",
      "Read(./.env)",
      "Read(./secrets/**)"
    ]
  }
}
```

-   Limit turns (`--max-turns`) and set a job-level timeout: they are the protection against a job running for hours.
-   Keep secrets out of the context: if an agent must not see `.env`, deny it read access.

**In the process:**

-   Read the diff. Always. Even when the MR description is convincing: the description was written by the same agent that wrote the code.
-   Be wary of huge MRs. If an agent opens a 2,000-line MR, the problem is the size of the task, not the review.
-   Treat a subagent's results as untrusted text: an agent may have read files or web pages containing instructions aimed at you. Claude Code flags some suspicious patterns in subagent reports, but that is no substitute for limiting up front what an agent can reach.


## 5.6 The project CI {#ci-progetto}

In this guide "CI" means two different things, and it is good to keep them apart.

-   **The agent workflows** (`agents.yml`, `claude.yml`, the `claude-team` job): they make the agents *work* on GitHub or GitLab runners. They exist only in architectures C and D.
-   **The project CI**: it *checks* every PR or MR, whoever wrote it, you or an agent. It builds, runs the tests, produces the inventory of dependencies with their licenses, looks for vulnerabilities, secrets and dangerous configurations. It is needed in every architecture, and it is the independent check on the agents' work: it runs somewhere other than they do and is not swayed by a well-written summary.

### What the template CI does

| Job | Tool | What it produces | When it fails |
|---|---|---|---|
| build and test | your stack's commands | the build, the test results | lint, build or tests red |
| SBOM and licenses | syft, trivy | `sbom.cdx.json` and `sbom.spdx.json` (full dependency inventory), `licenses.csv` (component, version, license), trivy's report | a license in a category forbidden by the policy |
| vulnerabilities | grype, trivy | `grype.json`, `grype.sarif`, `trivy-fs.json` and, if there is a Dockerfile, `trivy-image.json` | vulnerabilities above the threshold, secrets, dangerous configurations above the threshold |

The three tools have distinct roles, so none does the same work twice:

-   **syft** generates the SBOM, the list of everything the project contains, in the two standard formats (CycloneDX and SPDX). From the SBOM the script derives `licenses.csv`, the document to keep or hand to a client.
-   **grype** reads the SBOM and compares it against vulnerability databases. Scanning the SBOM instead of the code means the result refers exactly to the archived inventory.
-   **trivy** does the rest: it classifies licenses (forbidden, restricted, reciprocal...) and applies the policy; it looks for secrets in files and dangerous configurations in Dockerfiles, Kubernetes manifests, Terraform; it scans the container image.

Reports are saved as pipeline artifacts for 90 days, even when a check fails: that is exactly when they are needed.

### How it is built

The security part is a single script, `ci/scan.sh`, called identically from GitHub Actions and GitLab CI. Versions and policies live in a single file:

``` {.sourceCode .bash}
# ci/scanners.env: versions and policies of the CI security steps.
# CUSTOMIZE: bump the versions on purpose (read the release notes), tune the policies.
SYFT_VERSION=1.54.1
GRYPE_VERSION=0.120.1
TRIVY_VERSION=0.76.0

# grype: fail on vulnerabilities of this severity or worse (negligible, low, medium, high, critical)
VULN_FAIL_ON=high
# trivy: severities that fail the build for secrets and misconfigurations
TRIVY_FAIL_SEVERITY=HIGH,CRITICAL
# trivy license categories: CRITICAL = forbidden, HIGH = restricted, MEDIUM = reciprocal
LICENSE_FAIL_SEVERITY=CRITICAL
# directories trivy skips for secrets and misconfigurations (dependencies, build output)
TRIVY_SKIP_DIRS=node_modules,dist,build,reports

REPORTS_DIR=reports
```

`ci/install-scanners.sh` downloads the three tools at the given versions from the official releases and verifies their checksums, instead of the classic `curl | sh`. Updating a version is therefore an explicit change that goes through an MR.

``` {.sourceCode .bash}
#!/usr/bin/env bash
# ci/scan.sh: the security steps of the CI, the same on GitHub and GitLab.
#   ci/scan.sh sbom-licenses     SBOM (syft) + license report and policy (trivy)
#   ci/scan.sh vulnerabilities   vulnerabilities from the SBOM (grype)
#                                + secrets and misconfigurations (trivy)
#                                + the container image, if IMAGE is set (trivy)
# Every report goes to $REPORTS_DIR, which the CI saves as an artifact.
# Run sbom-licenses after installing the dependencies: license data come from them.
set -euo pipefail
source "$(dirname "$0")/scanners.env"
export PATH="${SCANNERS_BIN:-$HOME/.local/bin}:$PATH"
R=$REPORTS_DIR
mkdir -p "$R"

case "${1:-}" in
  sbom-licenses)
    syft dir:. --exclude "./$R" \
      -o "cyclonedx-json=$R/sbom.cdx.json" -o "spdx-json=$R/sbom.spdx.json"

    # one line per component: name, version, licenses
    jq -r '["name","version","licenses"],
      (.components[]? | [.name, (.version // ""),
        ([.licenses[]? | (.license.id // .license.name // .expression)]
          | map(select(. != null)) | join(" | "))])
      | @csv' "$R/sbom.cdx.json" > "$R/licenses.csv"

    trivy fs --scanners license --format json  --output "$R/licenses-trivy.json" .
    trivy fs --scanners license --format table --output "$R/licenses.txt" .
    # policy: fail on the license categories in LICENSE_FAIL_SEVERITY
    trivy fs --scanners license --severity "$LICENSE_FAIL_SEVERITY" --exit-code 1 --format table .
    ;;

  vulnerabilities)
    [ -f "$R/sbom.cdx.json" ] || { echo "Missing $R/sbom.cdx.json: run sbom-licenses first." >&2; exit 2; }
    status=0

    grype "sbom:$R/sbom.cdx.json" -o json  --file "$R/grype.json"
    grype "sbom:$R/sbom.cdx.json" -o sarif --file "$R/grype.sarif"
    grype "sbom:$R/sbom.cdx.json" -o table --fail-on "$VULN_FAIL_ON" | tee "$R/grype.txt" || status=1

    trivy fs --scanners secret,misconfig --skip-dirs "$TRIVY_SKIP_DIRS" \
      --format json --output "$R/trivy-fs.json" .
    trivy fs --scanners secret,misconfig --skip-dirs "$TRIVY_SKIP_DIRS" \
      --severity "$TRIVY_FAIL_SEVERITY" --exit-code 1 . || status=1

    if [ -n "${IMAGE:-}" ]; then
      trivy image --format json --output "$R/trivy-image.json" "$IMAGE"
      trivy image --severity "$TRIVY_FAIL_SEVERITY" --exit-code 1 "$IMAGE" || status=1
    fi
    exit $status
    ;;

  *)
    echo "usage: $0 sbom-licenses | vulnerabilities" >&2
    exit 2
    ;;
esac
```

On GitHub the workflow has three jobs: build and test, SBOM and licenses, vulnerabilities (which starts afterwards and uses the SBOM from the previous job). Actions are pinned to the commit, with the release in the comment:

``` {.sourceCode .yaml}
# .github/workflows/ci.yml: the project's CI. It checks every PR, whoever
# wrote it (you or an agent): build, test, SBOM and licenses, vulnerabilities.
# CUSTOMIZE: the toolchain and the commands of your stack (SETUP.md fills them in).
# Actions are pinned to a commit SHA; the comment says which release it is.
name: CI
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build-test:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803  # v6
      # CUSTOMIZE: toolchain (setup-python, setup-java, setup-go...) and cache
      - uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1  # v7.1.0
        with:
          node-version: 24
          cache: npm
      # CUSTOMIZE: the commands in AGENTS.md > Commands
      - run: npm ci
      - run: npm run lint
      - run: npm run build
      - run: npm test

  sbom-licenses:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803  # v6
      - uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1  # v7.1.0
        with:
          node-version: 24
          cache: npm
      # dependencies installed without running their scripts: license data come from them
      - run: npm ci --ignore-scripts     # CUSTOMIZE
      - run: ./ci/install-scanners.sh
      - run: ./ci/scan.sh sbom-licenses
      - uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9  # v7.0.2
        if: always()
        with:
          name: sbom-and-licenses
          path: reports/
          retention-days: 90

  vulnerabilities:
    needs: sbom-licenses
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803  # v6
      - uses: actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333  # v8.0.2
        with:
          name: sbom-and-licenses
          path: reports/
      - run: ./ci/install-scanners.sh
      # the container image is scanned too, when the project has a Dockerfile
      - name: Build the image
        if: hashFiles('Dockerfile') != ''
        run: |
          docker build -t app:ci .
          echo "IMAGE=app:ci" >> "$GITHUB_ENV"
      - run: ./ci/scan.sh vulnerabilities
      - uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9  # v7.0.2
        if: always()
        with:
          name: vulnerabilities
          path: |
            reports/grype.*
            reports/trivy-*.json
          retention-days: 90
      # Optional: show the findings in the Security tab (code scanning; on private
      # repositories it needs GitHub Code Security). Add "security-events: write"
      # to the job permissions and uncomment.
      # - uses: github/codeql-action/upload-sarif@<sha>  # CUSTOMIZE
      #   if: always()
      #   with:
      #     sarif_file: reports/grype.sarif
```

On GitLab the main file includes two parts, the project CI and the agent jobs, so with architectures A, B and E you remove only the second:

``` {.sourceCode .yaml}
# GitLab only: rename to .gitlab-ci.yml (guide sections 5.6 and 8.2).
# The pipeline has two parts:
#   .gitlab/ci/ci.yml      the project's CI: build, test, licenses, vulnerabilities
#   .gitlab/ci/agents.yml  the agent jobs, started only explicitly (AI_FLOW_INPUT)
include:
  - local: .gitlab/ci/ci.yml
  - local: .gitlab/ci/agents.yml   # remove with architecture A, B or E

# One pipeline per change: MR pipelines, the default branch, explicit triggers.
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS
      when: never
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    - if: $CI_PIPELINE_SOURCE == "web" || $CI_PIPELINE_SOURCE == "api" || $CI_PIPELINE_SOURCE == "trigger"

stages:
  - build
  - test
  - scan
  - ai
```

The jobs in `.gitlab/ci/ci.yml` are the same as on GitHub, with an image of your toolchain instead of the actions, and they never start in pipelines that launch an agent (`AI_FLOW_INPUT`).

**The template is written for npm.** `SETUP.md` adapts it to your stack: it asks for, or derives from the repository, the toolchain, commands, the lockfile for the cache and whether there is a Dockerfile, and fills in the two files. You decide the policies (vulnerability threshold, forbidden license categories) in `ci/scanners.env`; to move a license from one category to another you need a `trivy.yaml` with a `license:` section.

Three details that matter:

-   **Licenses are read from the installed dependencies.** The job installs the dependencies before scanning, without running their scripts. Without installation, for some ecosystems trivy finds no licenses and the report comes out empty, not clean.
-   **A vulnerability without a fix** still blocks the build if it exceeds the threshold. Exceptions go in a grype or trivy ignore file, with the reason and an expiry date, and go through your approval: `AGENTS.md` forbids agents from adding them on their own.
-   **Make the CI a required check** in the rules for `main` (GitHub) or in the MR settings (GitLab): without it, a red PR stays mergeable.

### What happens in the various architectures

| Architecture | Where the agent works | What the CI does | How the result gets back to the agent |
|---|---|---|---|
| A, B | on your computer | checks the PR the agent opens | the agent waits for the checks (`gh pr checks --watch`, `glab ci status`), fixes and pushes again |
| C | in a job on GitHub or GitLab | starts on the PR opened by the job, as for any PR | the agent does not wait, so as not to tie up a runner: ask for the fix with `@claude` on the PR, or with a new task |
| D | like C, also with OpenCode | like C | like C |
| E | on the Multica daemon (server or your PC) | like A | like A; with Multica's Git integration you also see the pipeline status on the issue |
| F | in the orchestrator's worktree | like A | the orchestrator reads the check status from the APIs and, if it fails, adds a fix step for the same role |

In architectures A, B and E the rule is in `AGENTS.md`: whoever runs outside CI, after opening the MR, waits for the checks and fixes until they are green. It is the simplest way to close the loop, at the price of a few extra turns while the pipeline runs.

Multica's integration with GitHub and GitLab (linking issues and PRs, CI status on the issue) relies on inbound webhooks: with everything on `localhost` you need a tunnel that exposes only the webhook URL, or the Multica server on a VPS. Without the integration everything still works: you see the CI status on the PR.


# 6. Architecture A, step by step {#passo-a}

Assumes chapter 5. Everything happens on your computer, in the Claude Code session opened in the project folder.


## 6.1 Starting the session and trying the agents {#provare-agenti}

``` {.sourceCode .bash}
cd my-project
claude

# explicit delegation with an @-mention
> @designer write the spec for the login page

# delegation in natural language
> use the backend agent to implement POST /api/auth/login

# chain of agents
> use optimizer to find the performance problems in the search
  module, then pass the results to backend to fix them

# devops: check that it stops where it should
> @devops add an image build job to the pipeline and deploy
  to staging
```

On this last command you should see the agent write the job and then **refuse** to run the deploy, pointing you to the merge request. If it runs it instead, your hook is not executable: check `chmod +x`.

Good to know: `/tasks` shows the running subagents, with the model they run on; the panel under the prompt lists them and `Enter` opens their transcript.


## 6.2 Running a complete feature {#feature-completa}

The most useful step in the whole guide: run an entire feature with you coordinating, and note where the agents go wrong.

```text
Implement the "user profile" feature following the standard sequence in CLAUDE.md:
1. use designer for the spec in docs/design/profile.md
2. use backend for GET and PATCH /api/profile, with tests
3. use frontend for the page, following the spec
4. use designer to review the implemented page
5. use frontend to apply the feedback
6. use optimizer on the new code, with green tests
Work on the branch feat/profile. Stop after each step and show me a summary.
```

After each step check the diff. Every recurring mistake becomes a line in that role's prompt or in `CLAUDE.md`. At the end open the pull request, yourself or by asking the main agent to use `gh pr create`, and review it as you would a colleague's.


## 6.3 Subscription or API key {#abbonamento-api}

- **Subscription.** It is the simplest choice for this architecture. The limits are not published in tokens: with Opus on the main roles and a month of intense work, Pro is not enough, Max 5x probably is. With `/usage` you see where you stand on session and weekly limits.
- **API key.** You pay per use and with `/cost` you see the session's cost. Useful for measuring the first days and comparing with section 2.8.
- **Keep the two uses separate.** If you later add CI (architecture C), use a dedicated API key for the workflows: with the subscription token every CI run would consume the same quota as your interactive work.


# 7. Architecture B, step by step {#passo-b}

Assumes chapter 5 and experience with architecture A. With agent teams the roles become independent Claude Code sessions that share a task list and a mailbox, and write to each other directly.

> **Warning:** the feature is experimental and disabled by default. It has known limits on session resumption, task coordination and shutdown (appendix 12.2). It costs 2.5 to 4 times architecture A: consider whether that one is enough for you.


## 7.1 Enabling agent teams {#team-attivazione}

In `.claude/settings.json`:

``` {.sourceCode .json}
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "teammateMode": "in-process"
}
```

`in-process` is the default and works in any terminal: teammates live in your terminal and you select them with the arrow keys in the panel. If you prefer a pane for each, use `"auto"` or `"tmux"`, but you need tmux or iTerm2 with the `it2` CLI --- and it does not work in VS Code's integrated terminal, in Windows Terminal or in Ghostty.

A side effect to know about: with agent teams enabled, every subagent Claude gives a name to starts as a teammate, even when you had not asked for a team. If you do not want that, set the variable back to `"0"`.


## 7.2 Starting the team {#team-avvio}

The team is created by describing it in words. You can reuse the subagent definitions you have already written: just name their type.

``` text
Create a team for the "user profile" feature.

Spawn four teammates using the agent types defined in the project:
- one of type designer, call it "dsg"
- one of type backend, call it "be"
- one of type frontend, call it "fe"
- one of type optimizer, call it "opt"

Do not spawn devops: this feature does not touch infrastructure.

Use Sonnet for fe, Opus for the others.

Create the task list with these dependencies:
1. dsg: UI spec in docs/design/profile.md
2. be: GET/PATCH /api/profile endpoints + tests   (depends on 1)
3. fe: profile page following the spec           (depends on 1 and 2)
4. dsg: review of the implementation              (depends on 3)
5. fe: apply the feedback                         (depends on 4)
6. opt: optimize the new code, green tests        (depends on 5)

Wait for the teammates to finish their tasks before you proceed.
Do not implement anything yourself.
```

By giving teammates explicit names you can refer to them in later messages; otherwise the lead names them and the names change every session.

Note the line about devops: five defined roles do not mean five teammates every round. The three-to-five teammates rule in section 7.6 applies to the number of *active* sessions, not to the number of roles you have written. A typical team uses three; devops joins when the task touches pipelines or deploys, and then it is often the designer who stays out.


## 7.3 What happens underneath {#team-sotto}

-   Each teammate has its own context window. It loads `CLAUDE.md`, the project's MCP servers and skills, **but does not inherit the lead's conversation**: everything it needs must be in the spawn prompt.
-   Each one's mailbox is a JSON file in `~/.claude/teams/<team>/inboxes/<agent>.json`. The task list lives in `~/.claude/tasks/<team>/` and survives the session.
-   Dependencies unblock on their own: when a teammate completes a task, the tasks that depended on it become claimable.
-   Claiming uses file locking, so two teammates do not take the same task.
-   When a teammate finishes and goes idle, it notifies the lead including its final answer.


## 7.4 Talking to a single agent {#team-singolo}

In the panel under the prompt: up/down arrows to select, `Enter` to open that teammate's transcript. From there everything you type goes to it. `Esc` returns to the lead. `x` on a selected teammate stops it. `Ctrl+T` shows and hides the task list.

Careful: a teammate's model and fast mode are fixed at spawn, so `/model` while you are looking at it changes the *lead's* model, not its own.


## 7.5 Quality gates with hooks {#team-gate}

Hooks are the way to enforce rules that the prompt alone does not guarantee. Three events are specific to teams:

| Event          | When it fires                | Effect of `exit 2`                               |
|------------------------|------------------------|------------------------|
| `TeammateIdle`  | the teammate is about to stop | sends feedback back and keeps it working |
| `TaskCreated`   | a task is being created       | prevents creation                            |
| `TaskCompleted` | a task is being closed     | prevents closing                             |

Example: no task closes with red tests.

``` {.sourceCode .json}
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          { "type": "command", "command": "./.claude/hooks/gate-test.sh" }
        ]
      }
    ]
  }
}
```

``` {.sourceCode .bash}
#!/bin/bash
# .claude/hooks/gate-test.sh
if ! npm test --silent > /tmp/test.log 2>&1; then
  echo "Task cannot be closed: the test suite fails." >&2
  tail -n 30 /tmp/test.log >&2
  exit 2
fi
exit 0
```

Remember `chmod +x` on the script, otherwise the hook fails instead of blocking.


## 7.6 Practical rules that make the difference {#team-regole}

-   **Three to five teammates**, no more. Token cost grows linearly and coordination overhead grows faster than the gain.
-   **No shared files.** Two teammates writing the same file overwrite each other. Split the work by file boundaries: that is why section 3.7 assigns folders and not topics.
-   **Five or six tasks per teammate.** If the lead creates too few, ask explicitly: "break the work into smaller tasks".
-   **The lead sometimes starts implementing on its own.** If you see it happen: "wait for the teammates to complete their tasks before proceeding".
-   **Do not leave it running unattended** for hours. Check, correct course, collect results as you go.
-   **Permissions are inherited from the lead** and cannot be differentiated at spawn. If the lead runs with broad permissions, they all have them.


# 8. Architecture C, step by step {#passo-c}

Assumes chapter 5, with the repository protection from section 5.5 already active. Here the team leaves your computer and works in CI: you create the issues, the agents open the merge requests, you review them.


## 8.1 Connecting GitHub {#collegare-github}

### Quick installation

From the repository, with the GitHub CLI already authenticated (`gh auth login`):

``` {.sourceCode .bash}
claude
> /install-github-app
```

The command installs the Claude GitHub App, saves the authentication secret (`ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`) and opens a pull request with the workflow files ready. It needs admin access to the repository.

### Manual installation

1.  Install the GitHub App from `github.com/apps/claude`. The three permissions the action needs are Contents, Issues and Pull requests, all read and write.
2.  Add the secret to the repository: `ANTHROPIC_API_KEY` (key from the Claude Console) or `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`).
3.  Add the workflow.

### Workflow: answering comments

This is the piece you asked for --- the agent answers the comments you write.

``` {.sourceCode .yaml}
# .github/workflows/claude.yml
name: Claude
on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]

concurrency:
  group: claude-${{ github.event.issue.number || github.event.pull_request.number }}
  cancel-in-progress: false

jobs:
  claude:
    if: contains(github.event.comment.body, '@claude')
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      issues: write
      id-token: write
      actions: read
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 1
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          claude_args: |
            --max-turns 15
            --model claude-sonnet-5-5
            --allowedTools "Bash(npm:*),Bash(npx:*)"
```

The lines that matter: `id-token: write` is needed for authentication via the GitHub App; `actions: read` lets Claude read the CI results on the PR; the `if` condition avoids starting a runner for every comment.

From then on, in an issue or a PR:

    @claude implement this feature as described in the issue
    @claude the integration test fails on the edge case, fix it
    @claude why is the pipeline red?

Claude answers in a comment on the same thread and updates it as it works. If the work produces changes, it commits them to the branch.

**Who can trigger it.** On issue and PR events the user writing must have write access to the repository. Bots are rejected unless listed in `allowed_bots`, to avoid infinite loops. These are two protections that keep you safe from unwanted triggers.

### Workflow: automatic review of every PR

It has Claude review every PR, including the agents' ones, and leaves comments on the lines. It is optional: via API it costs about \$30 a month with the volumes in section 2.8. With `claude_code_oauth_token` instead of the key it uses the subscription, which however consumes its quota; alternatively, start it only on PRs with a label, instead of on every push.

``` {.sourceCode .yaml}
# .github/workflows/claude-review.yml
name: Revisione
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
      issues: read
      id-token: write
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 1
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          plugin_marketplaces: "https://github.com/anthropics/claude-code.git"
          plugins: "code-review@claude-code-plugins"
          prompt: "/code-review:code-review --comment ${{ github.repository }}/pull/${{ github.event.pull_request.number }}"
          claude_args: '--allowedTools "mcp__github_inline_comment__create_inline_comment"'
```

The `--comment` argument is what makes the review get posted on the PR as an inline comment on every issue found; without it, the results stay in the workflow log. The `claude_args` line must be kept even if the skill already declares the same tool: the action starts the inline-comment MCP server only if the tool appears in `--allowedTools`.

### Two modes, one distinction to remember

-   **Without a `prompt` input** → interactive mode: Claude waits for the trigger phrase (`@claude` by default, customizable with `trigger_phrase`).
-   **With a `prompt` input** → automation mode: Claude starts on its own on the event, and by default writes to the workflow log. If you want it to post on the PR you have to say so in the prompt and give it a tool that allows it.

### Classic trap

If you pass `github_token: ${{ secrets.GITHUB_TOKEN }}` to the action, Claude's commits do not trigger your CI: GitHub does not trigger workflows on commits made with the default `GITHUB_TOKEN`. Remove it and let the action authenticate as the GitHub App, or use a token from an app of your own.


## 8.2 Connecting GitLab {#collegare-gitlab}

The GitLab integration is in beta and maintained by GitLab. There is no equivalent of GitHub's native comment trigger: GitLab does not start pipelines from MR comments, so you use the web/API trigger or merge request events.

1.  **Settings → CI/CD → Variables**: add `ANTHROPIC_API_KEY` as a *masked* variable (and protected, if you only need it on protected branches).
2.  Add the job:

``` {.sourceCode .yaml}
# .gitlab-ci.yml
stages:
  - ai

claude:
  stage: ai
  image: node:24-alpine3.21
  resource_group: claude-task-$TASK_ID
  interruptible: false
  rules:
    - if: '$AI_FLOW_INPUT && ($CI_PIPELINE_SOURCE == "web" || $CI_PIPELINE_SOURCE == "api" || $CI_PIPELINE_SOURCE == "trigger")'
  variables:
    GIT_STRATEGY: fetch
  before_script:
    - apk update && apk add --no-cache git curl bash
    - curl -fsSL https://claude.ai/install.sh | bash
    - export PATH="$HOME/.local/bin:$PATH"
  script:
    - >
      claude -p "$AI_FLOW_INPUT

      Follow AGENTS.md, including the alignment rules. Before opening the MR,
      rebase on main and rerun the tests. Do not start other agents."
      --permission-mode acceptEdits
      --allowedTools "Bash Read Edit Write mcp__gitlab"
      --max-turns 30
```

The job can be launched by hand from the UI, from the API with a context payload (the `AI_FLOW_*` variables), or automatically on merge request events.

To bridge comments and pipelines you can add a small external webhook: you listen for GitLab's `note` event, check that the text contains `@claude` and that the author has the permissions, and call the pipeline trigger API passing the comment text as a variable. It is about fifty lines of code and it is the route almost everyone on GitLab uses today.

If you need Amazon Bedrock or Google Cloud you can authenticate via OIDC without keeping static credentials in the repository.


## 8.3 Issues as the dashboard {#issue-dashboard}

The idea: the dashboard you already have is your issue tracker. A label indicates the role, opening or labeling starts the workflow, and the agent comments on the issue as it works.

On GitHub:

``` {.sourceCode .yaml}
# .github/workflows/claude-task.yml
name: Run assigned task
on:
  issues:
    types: [labeled]

jobs:
  run:
    if: startsWith(github.event.label.name, 'agent:')
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write
      pull-requests: write
      id-token: write
      actions: read
    steps:
      - uses: actions/checkout@v6
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            You are the "${{ github.event.label.name }}" agent (drop the
            "agent:" prefix to get the role name) of the team defined in
            .claude/agents/. Adopt that role's prompt.

            Task to carry out — issue #${{ github.event.issue.number }}:
            Title: ${{ github.event.issue.title }}
            Description:
            ${{ github.event.issue.body }}

            Proceed as follows, in this order:
            1. Comment on the issue with the plan you intend to follow.
            2. Implement on a new branch, staying within your role's boundaries.
            3. Run lint and tests. If they fail, fix them.
            4. Check whether main changed docs/api/ or docs/alignment/
               since the issue was opened; adapt or report it.
            5. If other roles rely on what you changed, add the entry
               under docs/alignment/ (AGENTS.md > Alignment changes).
            6. Push and open a pull request that closes the issue
               (gh pr create); if you cannot, post the pre-filled link.
               Description: what you changed, why, what you decided NOT
               to do, what the reviewer must check, and an
               "## Alignment impact" section ("none" if none). With an
               impact, add the alignment-needed label to the PR.
            7. Comment on the issue with the PR link and a summary of
               five lines at most.

            Do not merge. Do not close the issue. Do not touch main.
            Do not start other agents: the user creates alignment tasks.
          claude_args: |
            --max-turns 40
            --model claude-opus-5-5
            --allowedTools "Read,Write,Edit,Glob,Grep,Bash(git:*),Bash(npm:*),Bash(npx:*),Bash(gh pr create:*),Bash(gh pr edit:*),Bash(gh pr view:*),Bash(gh issue view:*),Bash(gh issue comment:*)"
```

The flow you get:

1.  You open an issue: *"Add the date filter to the orders list"*.
2.  You give it the `agent:backend` label.
3.  The workflow starts, the agent comments with its plan, works, opens the PR and summarizes what it did.
4.  You read the diff, comment with `@claude` to ask for changes, and merge when you agree.

The advantage is that the "dashboard" already has notifications, permissions, history, search and a mobile app. With a GitHub Project view you also get the kanban.

On GitLab the logic is identical, with the `issue` webhook instead of the `labeled` trigger and a call to the pipeline trigger API.


## 8.4 Trying the complete loop {#ciclo-completo}

Before entrusting it with real work, try the full loop on a small task:

1. Open an issue with a clear, bounded task, for example "Add a GET /api/health endpoint that returns the database status".
2. Give it the `agent:backend` label and check in the Actions tab (or Pipelines on GitLab) that the job starts.
3. Wait for the comment with the plan, then the pull request and the final summary on the issue.
4. Review the diff and leave a comment with `@claude` asking for a fix. Check that the agent answers and updates the PR.
5. Check that it cannot do what it must not: no push to `main`, no merge, no approval.
6. You merge.

Then tune the workflow prompt until the summaries the agent writes in the issues are really useful to you.


## 8.5 Several agents in parallel {#agenti-in-parallelo}

Every CI run is an independent session: it does not know whether another one is working on the same task, and does not see the others' work in progress. Two risks, and how the template handles them.

### Two agents on the same task

-   **GitHub.** `agents.yml` has `concurrency` per issue: two labels on the same issue do not start together, the second waits. The group keeps only one pending run: a third cancels the queued one. `claude.yml` also has its own group, so two `@claude` comments close together on the same PR do not make two agents work on the same branch. Loops are unlikely: the action discards events generated by a bot, so the agent's comments and pushes do not retrigger it. The only job that restarts on every push is the automatic review.
-   **GitLab.** The official example also starts Claude on `merge_request_event`, i.e. on every push to the MR: if the agent pushes with a project token, each of its commits can start another one. The template starts it only on explicit request (web interface, API or trigger with `AI_FLOW_INPUT`) and uses `resource_group` to queue jobs for the same task:

    ``` {.sourceCode .yaml}
    claude:
      resource_group: claude-task-$TASK_ID    # TASK_ID: the issue number, passed with the trigger
      interruptible: false
      rules:
        - if: '$AI_FLOW_INPUT && ($CI_PIPELINE_SOURCE == "web" || $CI_PIPELINE_SOURCE == "api" || $CI_PIPELINE_SOURCE == "trigger")'
    ```

-   **On both:** one role label per issue. If two roles are needed, they are two issues.

### Frontend and backend out of alignment

The contract and the alignment entries in section 3.7 are the first defense. In CI others are added, because direct messages between agents do not exist:

-   **GitHub: "Require branches to be up to date before merging"** in the rules for `main`. A PR built on an old `main` must be updated and pass CI again before merging: if meanwhile the backend has changed the contract, the frontend PR turns red before, not after. Claude's action does not rebase or merge `main`, by design: you update with the "Update branch" button and, if CI fails, ask for the fix with `@claude`. In private repositories branch protection requires a paid plan; the merge queue, which tests each PR on top of the ones before it, also depends on the plan.
-   **GitLab:** the agent can rebase on `main` before opening the MR, and the prompt asks it to. Checking the merged result before merging (merged results pipelines, merge trains) is in the paid plans; without it, run the end-to-end tests on `main` right after every merge.
-   **Dependencies between issues.** A feature that touches the API becomes three issues: contract, backend, frontend. You label the frontend one after the contract is merged. GitHub shows dependencies ("blocked by") and sub-issues; but the block does not stop the workflow, so you keep the order by applying the labels.
-   **The `alignment-needed` label.** Filter PRs and MRs with that label: they are the ones asking for alignment tasks before or right after the merge.

### One task, several roles, a single branch {#task-di-team}

Sometimes splitting everything into separate tasks costs more than it protects: for a small feature where backend and frontend change together, waiting for the backend merge before starting the frontend is just waiting. The **team task** is the alternative: one issue, several roles in sequence on the same branch, a single PR. You ask for it, explicitly, and `AGENTS.md` describes it in the "Team tasks" section.

**On GitHub** apply the `agent:team` label and write in the issue which roles and in what order:

``` {.sourceCode .text}
Add the "profile" page: GET/PATCH /api/profile and the page that uses it.
The spec is in docs/design/profile.md (merged in #41).

Roles: backend, frontend
```

The `team` job in `agents.yml` starts a coordinator that writes no code: it delegates to the subagents in `.claude/agents/`, one after the other, and checks that each has committed and pushed before moving to the next. Alignment entries that concern listed roles are resolved within the task, because the affected role works afterwards and on the same code; the others stay open and end up in the PR with the `alignment-needed` label.

``` {.sourceCode .yaml}
# .github/workflows/agents.yml (excerpt)
jobs:
  team:
    # One issue, several roles, one branch, one PR. Claude roles only.
    if: github.event.label.name == 'agent:team'
    runs-on: ubuntu-latest
    timeout-minutes: 120
    permissions:
      contents: write
      issues: write
      pull-requests: write
      id-token: write
      actions: read
    steps:
      - uses: actions/checkout@v6
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            You are the coordinator of a team task (AGENTS.md > Team tasks).
            You do not write code yourself: you delegate to the subagents in
            .claude/agents/.

            Task: issue #${{ github.event.issue.number }}
            Title: ${{ github.event.issue.title }}
            Description:
            ${{ github.event.issue.body }}

            1. Read the "Roles:" line of the description. Delegate ONLY to those
               roles, in that order. If the line is missing, comment on the issue
               asking for it and stop.
            2. Comment on the issue with the plan: which role does what, in order.
            3. Work on a single new branch. For each role in turn: delegate its part
               with the issue context and the previous roles' summaries; then make
               sure its work is committed and pushed before the next role starts.
            4. After each role, check docs/alignment/ for entries with
               "status: open". If the affected roles are in the "Roles:" list,
               handle them now (designer first if listed, then the affected roles)
               and mark them resolved. If a decision is needed or an affected role
               is not listed, leave the entry open and say so in the PR.
            5. Run lint and tests on the final result.
            6. Open one pull request that closes the issue (gh pr create); if you
               cannot, post the pre-filled link. Description: one section per role,
               what you decided NOT to do, what the reviewer must check, and
               "## Alignment impact". Label it alignment-needed if entries are
               still open.
            7. Comment on the issue with the PR link and a summary per role.
            Do not merge. Do not touch main. Never delegate to roles that are not
            in the "Roles:" line.
          # CUSTOMIZE: the build and test commands of your stack (npm here)
          claude_args: >-
            --max-turns 100
            --model claude-sonnet-5-5
            --allowedTools "Agent,Read,Write,Edit,Glob,Grep,Bash(git:*),Bash(npm:*),Bash(npx:*),Bash(gh pr create:*),Bash(gh pr edit:*),Bash(gh pr view:*),Bash(gh issue view:*),Bash(gh issue comment:*)"
```

**On GitLab** the equivalent job starts when the trigger also passes `AI_FLOW_ROLES` (for example `backend, frontend`):

``` {.sourceCode .yaml}
claude-team:
  stage: ai
  image: node:24-alpine3.21
  resource_group: claude-task-$TASK_ID
  interruptible: false
  timeout: 2h
  rules:
    - if: '$AI_FLOW_INPUT && $AI_FLOW_ROLES && ($CI_PIPELINE_SOURCE == "web" || $CI_PIPELINE_SOURCE == "api" || $CI_PIPELINE_SOURCE == "trigger")'
  variables:
    GIT_STRATEGY: fetch
  before_script:
    - apk update && apk add --no-cache git curl bash
    - curl -fsSL https://claude.ai/install.sh | bash
    - export PATH="$HOME/.local/bin:$PATH"
  script:
    - git checkout -B "feat/$TASK_ID"
    - >
      claude -p "You are the coordinator of a team task (AGENTS.md > Team tasks).
      Delegate ONLY to these roles, in this order: $AI_FLOW_ROLES.
      Branch: feat/$TASK_ID. After each role, commit and push its work and
      handle open docs/alignment/ entries for listed roles. Finally rebase on
      main, run the tests and open one MR with a section per role.

      Task: $AI_FLOW_INPUT"
      --permission-mode acceptEdits
      --model claude-sonnet-5-5
      --allowedTools "Agent Bash Read Edit Write mcp__gitlab"
      --max-turns 100
```

With roles on different harnesses, for example backend on Claude and frontend on OpenCode, the coordinator cannot delegate. On GitLab the solution is two jobs in successive stages on the same branch, with the Git part done by the script and not by the agent: it is more predictable and does not depend on what the harness allows.

``` {.sourceCode .yaml}
# Two harnesses, one branch: backend on Claude Code, frontend on OpenCode.
# Trigger with AI_FLOW_INPUT, TASK_ID and TWO_STEP=1.
# CUSTOMIZE: images, OpenCode flags and model, the token variable.
stages: [backend, frontend]

.push: &push
  - git add -A && git commit -m "$CI_JOB_NAME: task $TASK_ID" || true
  - git push "https://oauth2:${GITLAB_ACCESS_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git" "HEAD:feat/$TASK_ID"

backend-step:
  stage: backend
  resource_group: claude-task-$TASK_ID
  rules:
    - if: '$AI_FLOW_INPUT && $TWO_STEP'
  script:
    - git checkout -B "feat/$TASK_ID"
    - claude -p "You are the backend agent (docs/roles/backend.md). Task: $AI_FLOW_INPUT. Update the API contract first. Do not open the MR." --permission-mode acceptEdits --allowedTools "Bash Read Edit Write" --max-turns 40
    - *push

frontend-step:
  stage: frontend
  needs: [backend-step]
  resource_group: claude-task-$TASK_ID
  rules:
    - if: '$AI_FLOW_INPUT && $TWO_STEP'
  script:
    - git fetch origin "feat/$TASK_ID" && git checkout -B "feat/$TASK_ID" "origin/feat/$TASK_ID"
    - opencode run --model "deepseek/<model>" "You are the frontend agent (docs/roles/frontend.md). Task: $AI_FLOW_INPUT. The backend part is already on this branch: regenerate the API types from the contract first."
    - *push
    - glab mr create --source-branch "feat/$TASK_ID" --title "Task $TASK_ID" --description "Backend and frontend, see the commits." --yes
```

On GitHub the same chain with Claude's action is not reliable: the action pushes only to the branch it was invoked from or to the PR's branch. To mix harnesses on GitHub, the way is the orchestrator in section 11.4.

When to use it:

-   **Yes** for small, coupled features: an endpoint and the page that uses it, a migration and its adaptation in the frontend.
-   **No** for large work: the single PR becomes hard to review, and a mistake halfway stops the whole task. There, separate tasks with the contract merged first remain the way.
-   **Cost:** the coordinator adds about 10--20% tokens compared with separate tasks; it runs on Sonnet, while each role uses the model in its frontmatter. The job lasts longer: `timeout-minutes` is 120 and `--max-turns` 100.
-   **Before trusting it:** check on a small feature that the coordinator sees the project's agents on the runner, respects the order, and that the PR contains the commits of all the roles.

### Two limits of the GitHub action

-   **Tools must be granted.** With a `prompt` (automatic mode) the action can comment, but to edit files, run tests and use `git` or `gh` it needs entries in `--allowedTools`. The template lists them in `agents.yml`; they must be adapted to your stack's commands.
-   **It might not open the PR.** By default the action pushes the branch and leaves a pre-filled link to the PR, instead of opening it. The template grants it `gh pr create`; if it still does not open it, you find the link in the issue comment and open it yourself with one click.


# 9. Architecture D, step by step {#passo-d}

Assumes chapter 5 and the GitHub integration from section 8.1: the Claude part of the workflows uses the same app. Agents that do not use Claude run with OpenCode; their protections must be rebuilt as in section 3.9.


## 9.1 Variant 1: direct keys in secrets {#variante-chiavi}

1.  **Create one API key per role** with each provider you use, and set a spending limit in its console. It is the only spending cap you have in this variant: do not skip it.
2.  **Save them as repository secrets** (Settings → Secrets and variables → Actions), with names that state role and provider: `ANTHROPIC_KEY_BACKEND`, `DEEPSEEK_KEY_FRONTEND`, `MISTRAL_KEY_OPTIMIZER` and so on.
3.  **Install the two integrations**: `/install-github-app` from Claude Code (section 8.1) and `opencode github install` from OpenCode.
4.  **Add a workflow that dispatches by label.** The labels are those in section 8.3 (`agent:backend`, `agent:frontend`, ...).

``` {.sourceCode .yaml}
# .github/workflows/agents.yml
name: Agents
on:
  issues:
    types: [labeled]

concurrency:
  group: issue-${{ github.event.issue.number }}
  cancel-in-progress: false

jobs:
  claude:
    if: contains(fromJSON('["agent:backend","agent:devops","agent:designer"]'), github.event.label.name)
    runs-on: ubuntu-latest
    timeout-minutes: 60
    permissions:
      contents: write
      issues: write
      pull-requests: write
      id-token: write
    steps:
      - uses: actions/checkout@v6
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_KEY_BACKEND }}
          prompt: |
            You are the ${{ github.event.label.name }} agent. Carry out issue
            #${{ github.event.issue.number }} following AGENTS.md and docs/roles/.
            Work on a branch and open a pull request. Do not merge.
            Follow AGENTS.md > Alignment changes. Do not start other agents.
          claude_args: >-
            --max-turns 40
            --model ${{ github.event.label.name == 'agent:designer' && 'claude-sonnet-5-5' || 'claude-opus-5-5' }}
            --allowedTools "Read,Write,Edit,Glob,Grep,Bash(git:*),Bash(npm:*),Bash(npx:*),Bash(gh pr create:*),Bash(gh pr edit:*),Bash(gh issue comment:*)"

  opencode:
    if: contains(fromJSON('["agent:frontend","agent:optimizer"]'), github.event.label.name)
    runs-on: ubuntu-latest
    timeout-minutes: 60
    permissions:
      contents: write
      issues: write
      pull-requests: write
      id-token: write
    steps:
      - uses: actions/checkout@v6
      - uses: anomalyco/opencode/github@<pinned version>
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_KEY_FRONTEND }}
          MISTRAL_API_KEY: ${{ secrets.MISTRAL_KEY_OPTIMIZER }}
        with:
          # frontend on DeepSeek, optimizer on Mistral: swap the two names to switch
          model: ${{ github.event.label.name == 'agent:optimizer' && 'mistral/<model>' || 'deepseek/<model>' }}
          prompt: |
            You are the ${{ github.event.label.name }} agent. Carry out issue
            #${{ github.event.issue.number }} following AGENTS.md and docs/roles/.
            Work on a branch and open a pull request. Do not merge.
            Follow AGENTS.md > Alignment changes. Do not start other agents.
```

A few notes on this workflow:

-   **Model names.** Claude's are the current API names. For DeepSeek, Mistral and the other providers use the exact name given in OpenCode's provider documentation.
-   **Two providers in the same job.** Both keys reach the `opencode` job, whatever the role; the spending limit remains the one set in each console. If you want each role to see only its own key, split the job in two, one per provider, or move to the LiteLLM variant.
-   **Versions.** OpenCode's documentation uses `@latest`: pin a version, as for any third-party action.
-   **`timeout-minutes` and `--max-turns`** are the protection against a job running for hours and burning budget.
-   **`concurrency`** prevents two labels on the same issue from starting two agents in parallel on the same files.
-   **The trap in section 8.1 applies here too.** If the actions commit with the default `GITHUB_TOKEN`, your CI does not start on their commits. Let them authenticate with their own app.
-   **Public repositories.** GitHub does not pass secrets to pull requests from forks, so the workflows do not expose the keys. But never give write permissions to a workflow triggered by a fork.


## 9.2 Configuring LiteLLM and OpenCode {#config-litellm-opencode}

This configuration is needed for variant 2 of this chapter and for architecture E. It is not needed for variant 1, where OpenCode uses the providers' keys directly.


### The gateway: LiteLLM {#gateway-litellm}

LiteLLM exposes a single endpoint compatible with the OpenAI API and translates to each provider. A minimal configuration file:

``` {.sourceCode .yaml}
# litellm-config.yaml
model_list:
  - model_name: claude-sonnet
    litellm_params:
      model: anthropic/claude-sonnet-5-5
      api_key: os.environ/ANTHROPIC_API_KEY
  - model_name: gpt
    litellm_params:
      model: openai/<model>
      api_key: os.environ/OPENAI_API_KEY
  - model_name: deepseek
    litellm_params:
      model: deepseek/<model>
      api_key: os.environ/DEEPSEEK_API_KEY
  - model_name: mistral
    litellm_params:
      model: mistral/<model>
      api_key: os.environ/MISTRAL_API_KEY
  - model_name: local
    litellm_params:
      model: ollama/<model>
      api_base: http://ollama:11434
```

Start it with the official Docker image (see LiteLLM's quick start for the current command) and check it with `curl http://localhost:4000/health`. In production put it behind TLS and create a **virtual key for each agent**: that is how you get a separate budget and cost log per role, and how you revoke one agent without touching the others.


### The harness for non-Claude models: OpenCode {#harness-opencode}

OpenCode is an agentic harness similar to Claude Code that talks to any provider. You connect it to the gateway with an `opencode.json` in the project root:

``` {.sourceCode .json}
{
  "provider": {
    "litellm": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "LiteLLM",
      "options": { "baseURL": "http://localhost:4000/v1" },
      "models": {
        "gpt":      { "name": "GPT via LiteLLM" },
        "deepseek": { "name": "DeepSeek via LiteLLM" },
        "mistral":  { "name": "Mistral via LiteLLM" },
        "local":    { "name": "Local model" }
      }
    }
  }
}
```

The model keys must match LiteLLM's `model_name` values. The gateway key does not go in the file: you enter it in OpenCode with `/connect`, choosing the LiteLLM provider.

Claude Code can stay connected directly to Anthropic: it does not need to go through LiteLLM to have the multi-model dashboard.


## 9.3 Variant 2: LiteLLM on a small server {#variante-litellm}

Here the providers' real keys live on a server of yours, and GitHub only knows LiteLLM virtual keys, one per role, each with its own budget. It needs little: LiteLLM does not run models, it forwards requests. The smallest plan from a provider like Hetzner is enough, and costs about €6 a month with an IPv4 address.

**1. The stack on the server.** LiteLLM, a Postgres (needed for virtual keys and budgets) and Caddy for the TLS certificate. Only Caddy is exposed to the internet.

``` {.sourceCode .yaml}
# docker-compose.yml
services:
  litellm:
    image: ghcr.io/berriai/litellm:<pinned version>
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    volumes:
      - ./litellm-config.yaml:/app/config.yaml:ro
    environment:
      DATABASE_URL: postgresql://litellm:${PG_PASSWORD}@db:5432/litellm
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      MISTRAL_API_KEY: ${MISTRAL_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: litellm
      POSTGRES_PASSWORD: ${PG_PASSWORD}
      POSTGRES_DB: litellm
    volumes:
      - pgdata:/var/lib/postgresql/data
  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy:/data
volumes:
  pgdata: {}
  caddy: {}
```

    # Caddyfile
    llm.your-domain.com {
        reverse_proxy litellm:4000
    }

The `litellm-config.yaml` file is the one from section 9.2. Check the image name and version in LiteLLM's quick start before starting.

**2. One virtual key per role, with a budget.** You create them with the master key, which never leaves the server:

``` {.sourceCode .bash}
curl -s https://llm.your-domain.com/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"key_alias": "optimizer", "models": ["deepseek", "mistral"],
       "max_budget": 30, "budget_duration": "30d"}'
```

The returned key goes into GitHub secrets as `LITELLM_KEY_OPTIMIZER`. The `models` field restricts the key to the role's models: the optimizer cannot call Opus even by mistake. With both DeepSeek and Mistral allowed, switching from one to the other only requires changing the model in the workflow; the budget stays a single one for the role and the cost log separates them by model.

**3. OpenCode points to the server.** In the repository's `opencode.json` the `litellm` provider from section 9.2 changes only its `baseURL`, which becomes `https://llm.your-domain.com/v1`. In the workflow the `opencode` job uses `model: litellm/deepseek` or `model: litellm/mistral` and receives the virtual key from the secret. The action's documentation does not say how to pass the key to a custom provider: try it with a test job before entrusting it with real work.

**4. Claude can stay direct.** The `claude` job can keep using the Anthropic key from the secrets, with the spending limit set in the Console. It is the simplest choice: LiteLLM is mostly for the non-Claude models.

**5. Protect the server.** It is exposed to the internet, and filtering by IP does not work because GitHub runners use too wide a range of addresses. So:

-   only ports 80 and 443 open, SSH only with a key;
-   master key never off the server, only virtual keys with budgets to GitHub;
-   automatic security updates and a database backup.


## 9.4 Variant 3: a hosted gateway {#variante-gateway}

A service like OpenRouter gives a single key for many models, with no server to manage. Two things to know: it charges a fee on credit purchases (about 5.5%), and it sees the prompt and code of every request. For work or client code it is one more third party to assess.


## 9.5 Protecting non-Claude agents {#proteggere-non-claude}

Agents running with OpenCode do not have Claude Code's hooks. Before entrusting them with work:

1. Create their files in `.opencode/agents/` with the permissions from section 3.9, starting from devops if you assign it infrastructure.
2. Move the role prompts to `docs/roles/` and the common rules to `AGENTS.md`, as in section 3.9, so Claude Code and OpenCode read the same instructions.
3. Check the platform protections in section 5.5: they are the only ones that hold whatever model is running.
4. Run a test with a forbidden command, as in section 6.1: the agent must refuse.


# 10. Architecture E, step by step {#passo-e}

Assumes chapter 5, the LiteLLM and OpenCode configuration from section 9.2 and the portable roles from section 3.9. You need an always-on server: the Multica daemon runs the agents' harnesses there.


## 10.1 Preparing the server {#server-multica}

1. **The server.** A Linux machine with at least 4 vCPUs and 8 GB of RAM: the agents' builds and tests run here. A plan of this size costs roughly €15–25 a month.
2. **Access.** SSH with a key only, a firewall with only the necessary ports, a non-administrator user for the daemon.
3. **Docker with Compose,** installed following Docker's official guide for your distribution, and `git`.
4. **The harnesses**, installed and authenticated as the daemon's user:

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   curl -fsSL https://opencode.ai/install | bash
   claude        # sign in, then exit
   opencode      # connect the LiteLLM provider with /connect, then exit
   ```
5. **Git credentials:** a token that can create branches and open merge requests, never push to `main` or merge.
6. **No cluster, cloud or registry credentials** on this machine.


## 10.2 Starting LiteLLM next to the daemon {#litellm-locale}

If LiteLLM runs on the same server as the daemon, there is no need to expose it to the internet: start the stack from section 9.3 without Caddy and have LiteLLM listen only on the local interface, for example with `ports: ["127.0.0.1:4000:4000"]`. OpenCode will point to `http://127.0.0.1:4000/v1`. Create one virtual key per role anyway, with its budget: that is how you compare costs in section 10.5.


## 10.3 Installing Multica {#installare-multica}

Self-hosted server with Docker Compose:

``` {.sourceCode .bash}
git clone https://github.com/multica-ai/multica.git
cd multica
make selfhost          # creates .env, generates JWT_SECRET, starts the stack
# UI: http://localhost:3000   API: http://localhost:8080
```

Then, on the machine where the agents' work runs:

``` {.sourceCode .bash}
multica setup self-host \
  --server-url https://api.your-domain.com \
  --app-url https://app.your-domain.com

multica daemon status
multica daemon logs -f
```

The daemon looks in the `PATH` for the CLIs of the supported agents (including `claude`, `codex`, `opencode`, `gemini`) and registers them as runtimes. They must already be installed and authenticated on that machine, and the daemon must have access to the repositories and Git credentials.

Run the daemon in a container or a dedicated VM, not on your laptop: that is where the agents execute commands, and that is where step 4 applies.


## 10.4 Creating the agents and assigning tasks {#multica-agenti}

In the interface you create one agent per role and choose its runtime. A reasonable starting assignment:

| Role     | Runtime     | Model    | Why                                                                 |
|------------------|------------------|------------------|------------------|
| backend   | Claude Code | Opus       | costly mistakes, full hooks and permissions                               |
| devops    | Claude Code | Opus       | the blocking hook from section 3.6 stays active                        |
| frontend  | OpenCode    | to try | follows a spec that is already written: a good test bench for other models |
| optimizer | OpenCode    | to try | the result is measurable: timings before and after                          |
| designer  | Claude Code | Sonnet     | uses the Playwright MCP server configured in section 3.2             |

The rule behind the table: **try other models where the outcome is verifiable and the damage of a mistake is contained.** Keep Claude Code on the roles that touch data, security and infrastructure until you have rebuilt their protections in the other harness.

From there the flow is that of architecture C (section 8.3): you create the issue, assign it to the agent, it picks it up, works on a branch, updates the status and opens the MR. You review and merge.


## 10.5 Comparing models with numbers {#confrontare-modelli}

The price per token does not tell you which model costs less. A weaker model gets more tool calls wrong, repeats more turns and produces more rework, and the per-token saving can vanish. Measure per **delivered task**:

-   cost of the task, from LiteLLM's logs per virtual key;
-   number of turns up to the MR;
-   review rounds before the merge;
-   how many MRs you had to close without merging.

After twenty or so tasks per role you have the data to decide. Often the answer is mixed: a cheap model is fine for one role and not for another.


## 10.6 Everything on your PC: test bench and consumption estimate {#multica-locale}

Before paying for a server, or choosing a model for a role, it is worth running architecture E on your computer. It serves two purposes: verifying that the setup works with your project, and replacing the estimates in section 2.8 with numbers measured on your code.

### The local stack

Everything lives on one machine: the Multica server in Docker (frontend on `localhost:3000`, Go backend on `localhost:8080`, PostgreSQL 17), the daemon outside the containers, LiteLLM if you use it. The daemon connects to the backend with an outbound WebSocket, so you open no ports and expose nothing to the internet. The models stay remote: only the harnesses, builds and tests run on the PC, and no GPU is needed.

``` {.sourceCode .bash}
# server (frontend, backend, Postgres): requires Docker and Docker Compose
git clone https://github.com/multica-ai/multica.git && cd multica
make selfhost

# CLI and daemon: configures localhost, logs in, starts the daemon
multica setup self-host

# limit parallel tasks (the daemon default is 20): it also caps the spend
export MULTICA_DAEMON_MAX_CONCURRENT_TASKS=3
```

LiteLLM is the stack from section 9.3 without Caddy. The template has an extra file that exposes the port only on `127.0.0.1`:

``` {.sourceCode .yaml}
# docker-compose.local.yml: LiteLLM on your own PC, without Caddy.
# Use: docker compose -f docker-compose.yml -f docker-compose.local.yml up -d litellm db
# The port is bound to 127.0.0.1 only: nothing is reachable from the network.
services:
  litellm:
    ports:
      - "127.0.0.1:4000:4000"
```

In the Multica configuration and in `opencode.json` the LiteLLM address becomes `http://localhost:4000/v1`.

### Resources

These are estimates, not measurements: Multica's documentation gives no hardware requirements. The Multica stack itself is light; what matters is how many agents work at once and what they run: installing dependencies, builds, tests, dev servers, the Playwright browser, test databases in containers.

| Use | CPU | RAM | Free disk |
|---|---|---|---|
| Minimum: 1--2 agents in parallel, no LiteLLM | 4--6 cores | 16 GB | 50 GB on SSD |
| Comfortable: 3--4 agents, LiteLLM, end-to-end tests | 8 cores | 32 GB | 100+ GB on NVMe |

Roughly: Multica 1--2 GB of RAM, LiteLLM with its database 0.5--1 GB, each working agent 2--4 GB counting builds, tests and browser. A fast disk matters more than the CPU: each task has its own copy of the repository in `~/multica_workspaces`, with its dependencies. A GPU is needed only for local models with Ollama, and that is another spending bracket (at least 24 GB of VRAM for models of about 30 billion parameters, suitable only for small jobs).

### What changes compared with the server

-   **Work only progresses while the PC is on.** Tasks created in the meantime stay in the queue.
-   **From your phone** you reach it from your home network or with a VPN like Tailscale; do not expose the dashboard to the internet.
-   **Agents run with your user's permissions.** Use at least a system user dedicated to the daemon, better a virtual machine or WSL2 on Windows; no cloud credentials reachable and a Git token that cannot merge (section 12.1).
-   **The daemon's cleanup of working copies** discards whatever has not been pushed: agents must always push.

When you want work to progress even with the PC off, you move the server to a small VPS and leave the daemon on the PC, or move everything: the configuration stays the same, only the addresses change.

### CI with Multica

The project CI does not change: it starts on the PR or MR the agent opens from your PC and runs on the platform's runners. Agents wait for the checks before closing the task and fix things if they fail (section 5.6). The workflows that make agents work in CI are not needed here: Multica plays that role.

### Verifying the setup

Before measuring, a trial run that touches every piece:

1.  A small task for each role you will use, with a ready spec: for example a health endpoint for the backend, a component for the frontend.
2.  Check in the dashboard that each task reaches the daemon, the right harness and the right model, and ends with an MR.
3.  Verify the protections: ask devops for a `terraform apply` and check that it is blocked; try to make security write outside `docs/security/`.
4.  A team task with two roles, to see that the same branch reaches the MR intact.

### Estimating token consumption

The goal is the **average cost per task for each role** on your project, to be multiplied by the tasks you expect.

**1. A single measurement point.** Route all models through LiteLLM, Claude included, with one virtual key per role. Claude Code accepts a gateway: in the daemon's environment set `ANTHROPIC_BASE_URL=http://localhost:4000` and the role's virtual key as the token. Check that your LiteLLM version exposes the Anthropic-API-compatible endpoint. If you prefer to keep Claude direct, use an API key dedicated to the test and read the consumption in the Console.

**2. A representative sample.** Ten to fifteen tasks, distributed among the roles as in real work (for a web app: more backend and frontend, few devops and designer), each with a ready spec. Add a couple of fixes requested with a comment and a team task: rework is cost too.

**3. The cost of each task.** The template's script reads the spend LiteLLM records per key: run it before and after the task, the difference is the cost.

``` {.sourceCode .bash}
#!/bin/bash
# Prints the spend recorded by LiteLLM for one or more virtual keys.
# Usage: ./key-spend.sh <virtual-key> [<virtual-key>...]
# Run it before and after a task: the difference is the cost of the task.
# CUSTOMIZE: LITELLM_URL if LiteLLM is not on localhost.
set -euo pipefail
URL=${LITELLM_URL:-http://localhost:4000}
for KEY in "$@"; do
  curl -s "$URL/key/info?key=$KEY" -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
    | jq -r '.info | "\(.key_alias // "?")\t$\(.spend)"'
done
```

For each task also note the turns up to the MR, the minutes, the fix rounds and the share of input read from the cache. You find turns and cache in LiteLLM's logs and in the task summary in Multica.

**4. The calculation.**

| Role | Tasks measured | Average cost per task | Tasks expected per month | Rework | Monthly cost |
|---|---|---|---|---|---|
| backend | 4 | *measured* | 22 | +15% | average cost × 22 × 1.15 |
| frontend | 4 | *measured* | 20 | +15% | ... |
| ... | | | | | |

You derive the rework from the sample itself: cost of the fixes divided by the cost of the tasks. Add up the rows and add the automatic reviews in CI, if you use them.

**5. Three corrections before trusting the number.**

-   **The project grows.** The first tasks run on a small repository and read little; halfway through the project every turn reads more. Repeat the measurement when the code is a third or halfway done, and use that for projections.
-   **The cache.** If the share of input read from the cache is low, the cost per turn rises a lot, especially with DeepSeek and Mistral (section 2.8). A share below 60--70% usually indicates sessions that are too long or a `CLAUDE.md` that changes often.
-   **Comparing models.** To choose between two models for a role, run the same tasks on both, with the same spec: what counts is the cost per delivered task, not the price per token (section 10.5).

With these numbers the table in section 2.8 becomes yours, and the choice between subscription, direct API and architecture is made on real data.


# 11. Architecture F, step by step {#passo-f}

Assumes chapter 5 and the repository protection from section 5.5. The two variants differ in where the tasks live: in a tracker you already use, or in a dashboard of your own.


## 11.1 Variant with an existing tracker, via MCP {#tracker-mcp}

If you already use Linear, Jira, Notion or similar, you connect the tracker as an MCP server and the agents read and update tasks directly.

``` {.sourceCode .json}
{
  "mcpServers": {
    "linear": {
      "type": "http",
      "url": "https://mcp.linear.app/mcp"
    }
  }
}
```

You can also assign an MCP server to a single agent, by defining it inline in its frontmatter: that way the tracker's tools do not take up context in the others.

``` {.sourceCode .markdown}
---
name: backend
description: ...
mcpServers:
  - linear
---
```

You still need something that *starts* the agent when you change a task's status: a tracker webhook that triggers a pipeline, or the orchestrator in section 11.2. MCP gives reading and writing, not triggering.


## 11.2 Custom orchestrator with the Agent SDK {#orchestratore-sdk}

It is the way to a dashboard of your own, with full control over queues, priorities, retries and progress streaming.

``` {.sourceCode .bash}
npm install @anthropic-ai/claude-agent-sdk
# or, in Python:  pip install claude-agent-sdk
```

An orchestrator skeleton in TypeScript:

``` {.sourceCode .typescript}
import { query } from "@anthropic-ai/claude-agent-sdk";
import { takeQueuedTask, updateTask } from "./dashboard";

const ROLE_PROMPT: Record<string, string> = {
  designer:  "You are the product designer. You write specs, not code.",
  frontend:  "You are the frontend developer. You work only under src/ui/.",
  backend:   "You are the backend developer. You work only under src/server/.",
  optimizer: "You optimize working code without changing its behavior.",
};

async function runTask(task) {
  await updateTask(task.id, { status: "in_progress", startedAt: new Date() });

  const steps: string[] = [];

  try {
    for await (const msg of query({
      prompt: `${ROLE_PROMPT[task.role]}

Task #${task.id}: ${task.title}
${task.description}

Work on the branch feat/${task.id}. When you are done, open a merge
request. Do not merge and do not touch main.`,
      options: {
        cwd: task.repoPath,
        model: "claude-opus-5-5",
        permissionMode: "acceptEdits",
        maxTurns: 40,
        allowedTools: ["Read", "Write", "Edit", "Grep", "Glob", "Bash"],
        settingSources: ["project"],   // loads CLAUDE.md and .claude/
      },
    })) {

      // stream progress to the dashboard
      if (msg.type === "assistant") {
        for (const block of msg.message.content) {
          if (block.type === "text") {
            steps.push(block.text);
            await updateTask(task.id, { lastUpdate: block.text });
          }
          if (block.type === "tool_use") {
            await updateTask(task.id, { action: block.name });
          }
        }
      }

      if (msg.type === "result") {
        await updateTask(task.id, {
          status: msg.subtype === "success" ? "in_review" : "failed",
          summary: msg.result,
          cost: msg.total_cost_usd,
          log: steps,
        });
      }
    }
  } catch (e) {
    await updateTask(task.id, { status: "failed", error: String(e) });
  }
}

// main loop
while (true) {
  const task = await takeQueuedTask();
  if (task) await runTask(task);
  else await new Promise((r) => setTimeout(r, 5000));
}
```

Important notes on this code:

-   `settingSources: ["project"]` is what loads `CLAUDE.md` and the definitions in `.claude/agents/`. Without it, the SDK starts without the project context.
-   `permissionMode: "acceptEdits"` accepts file changes in the working directory but does not skip the other checks. Do not use `bypassPermissions`.
-   In the `result` message you have the session's cost in dollars: write it into the task, it is the simplest way to notice if a role is burning budget.
-   Run the orchestrator in a container with write access to the repository only and with a Git token that cannot push to `main`.

For automatic task updates without writing code around the SDK, there is also the hooks route: a `SubagentStop` or `Stop` hook that calls your API with the outcome.

``` {.sourceCode .json}
{
  "hooks": {
    "SubagentStop": [
      {
        "hooks": [
          { "type": "command", "command": "./.claude/hooks/update-task.sh" }
        ]
      }
    ]
  }
}
```


## 11.3 Running the orchestrator in production {#esercizio-orchestratore}

The orchestrator is an always-on service: treat it as such.

- **Where to run it:** in a container on a server of yours, with write access to the working repository only.
- **Credentials:** a dedicated API key with a spending limit in the Console; a Git token that cannot push to `main` or merge.
- **Restart and logs:** have it restart on its own on errors (for example with the container's automatic restart) and keep cost, duration and outcome for each task, as in the code in section 11.2.
- **Concurrency:** start with one task at a time per role; increase only when costs per task are stable.
- **Safety cap:** `maxTurns` on every run and an overall timeout per task.


## 11.4 Skeleton of a complete orchestrator {#orchestratore-completo}

The orchestrator in section 11.2 runs one role per task. To handle everything that architectures C and D entrust to GitHub, GitLab and your discipline, i.e. tasks with several roles, alignment, concurrency, different models and approvals, a few more components are needed. This is the skeleton: what to build, how the parts talk to each other, in what order to build them. The code is a frame to complete, not a ready program. You can give it to Claude Code together with this section as a starting spec.

### The components

    ┌──────────────────────────────────────────────────────────────────────┐
    │ INTAKE     GitHub/GitLab webhooks · dashboard API · commands         │
    └───────────────────────────────┬──────────────────────────────────────┘
                                    │ normalized tasks
    ┌───────────────────────────────▼──────────────────────────────────────┐
    │ STORE      tasks, steps, events, costs, locks       (Postgres)       │
    └───────┬──────────────────────────────────────────────────▲───────────┘
            │ runnable tasks                                   │ status, events
    ┌───────▼────────────┐   ┌─────────────────────┐   ┌───────┴───────────┐
    │ SCHEDULER          │──►│ TASK PIPELINE       │──►│ ALIGNMENT          │
    │ locks, budgets,    │   │ step by step,       │   │ CONTROL            │
    │ concurrency        │   │ test, commit, push  │   │ auto / ask you     │
    └────────────────────┘   └──────┬──────────────┘   └───────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
    ┌─────▼──────────┐   ┌──────────▼─────────┐   ┌───────────▼─────────┐
    │ WORKSPACE      │   │ RUNNERS            │   │ GIT PLATFORM        │
    │ one worktree   │   │ Claude (Agent SDK) │   │ PRs/MRs, comments,  │
    │ per task       │   │ OpenCode (CLI)     │   │ labels              │
    └────────────────┘   └────────────────────┘   └─────────────────────┘
                                    │ streamed progress
                          ┌─────────▼──────────┐
                          │ DASHBOARD (SSE)    │
                          └────────────────────┘

-   **Intake.** GitHub and GitLab webhooks (label added, comment with a command), the dashboard API. Everything becomes a `Task` with its list of steps.
-   **Store.** Tasks, steps, events, costs and locks in a database. It is the source of truth: the dashboard reads from here, and after a restart the orchestrator resumes from here.
-   **Scheduler.** Picks runnable tasks respecting three constraints: one task at a time per branch, a cap on concurrent runs (total and per role), the task's remaining budget.
-   **Task pipeline.** Runs the steps in order in the same worktree. After each step: tests, commit, push, check of the contract and the alignment entries.
-   **Alignment control.** If a step opens an entry in `docs/alignment/`, it inserts the following steps (designer, then the roles involved) or puts the task on hold for your decision, according to the task's policy.
-   **Workspace.** One Git worktree per task on the `feat/<id>` branch, updated with `main` before each step and removed at the end of the task.
-   **Runners.** A common interface with two implementations: Claude via the Agent SDK, which loads the project's `.claude/` with hooks and permissions, and OpenCode from the command line for the other models, with the agents in `.opencode/`.
-   **Git platform.** Opens the PR or MR, comments, applies labels. It is the only component that talks to GitHub or GitLab, so changing platform touches a single file.
-   **Studio.** Design conversations, one per feature: they produce the spec, open the design PR and, after the merge, create the tasks (later in this section).
-   **Dashboard.** Reads the store and receives streamed events; from there you create tasks, approve pending decisions and see costs and progress.

### The states of a task

    blocked ──► queued ──► running ──► in_review ──► done   (merged by you)
     (waits for tasks)       │  ▲
                             │  └──── waiting_human ◄── decision requested by the designer,
                             │                          budget exhausted, tests red after N attempts
                             └──► failed ──► queued         (manual retry)

A task always ends in `in_review` with an open PR, or in `waiting_human` or `failed` with a written reason. The orchestrator never merges.

### The project structure

``` {.sourceCode .text}
orchestrator/
├── src/
│   ├── types.ts              # Task, Step, Role, events
│   ├── intake/
│   │   ├── github.ts         # webhook → Task (labels agent:<role>, agent:team)
│   │   ├── gitlab.ts
│   │   └── api.ts            # dashboard endpoints
│   ├── store/
│   │   ├── schema.sql
│   │   └── repo.ts           # tasks, steps, events, locks
│   ├── scheduler.ts          # picks runnable tasks, locks, budgets
│   ├── pipeline.ts           # runs the steps of one task
│   ├── alignment.ts          # reads docs/alignment/, decides next steps
│   ├── workspace.ts          # git worktrees, sync with main, push
│   ├── runners/
│   │   ├── runner.ts         # common interface
│   │   ├── claude.ts         # Agent SDK
│   │   └── opencode.ts       # OpenCode CLI
│   ├── platform/
│   │   ├── github.ts         # PRs, comments, labels
│   │   └── gitlab.ts
│   ├── events.ts             # SSE stream for the dashboard
│   └── config.ts             # roles → harness, model, budget, limits
├── dashboard/                # web UI
└── Dockerfile
```

### The types

``` {.sourceCode .typescript}
// src/types.ts
export type Role = "designer" | "frontend" | "backend" | "devops" | "optimizer" | "security";
export type Harness = "claude" | "opencode";

export type TaskStatus = "blocked" | "queued" | "running" | "waiting_human" | "in_review" | "done" | "failed";
export type StepStatus = "pending" | "running" | "done" | "failed" | "skipped";

export interface Step {
  id: string;
  role: Role;
  instructions: string;          // what this role must do in this task
  reason: "planned" | "alignment" | "retry";
  status: StepStatus;
  costUsd: number;
  summary?: string;              // final message of the agent
}

export interface Task {
  id: string;
  title: string;
  description: string;
  source: { kind: "github" | "gitlab" | "dashboard"; ref?: string };  // issue URL
  branch: string;                // feat/<id>
  steps: Step[];                 // executed in order
  specPath?: string;             // docs/design/<feature>.md, included in every prompt
  dependsOn?: string[];          // task ids: the task stays "blocked" until they are merged
  alignmentPolicy: "auto" | "ask";
  budgetUsd: number;
  spentUsd: number;
  status: TaskStatus;
  waitingFor?: string;           // why a human is needed
  prUrl?: string;
}

export interface RoleConfig {
  harness: Harness;
  model: string;                 // claude-opus-5-5, deepseek/<model>, ...
  maxTurns: number;
  maxConcurrent: number;
}

export interface RunResult {
  ok: boolean;
  summary: string;
  costUsd: number;
}

export interface Runner {
  run(opts: { role: Role; prompt: string; cwd: string; config: RoleConfig;
              onEvent: (e: { kind: string; text: string }) => void }): Promise<RunResult>;
}
```

### The heart: a task's pipeline

``` {.sourceCode .typescript}
// src/pipeline.ts
import { Task, Step } from "./types";
import { store } from "./store/repo";
import { workspace } from "./workspace";
import { runners, roleConfig, buildPrompt } from "./runners/runner";
import { openAlignmentEntries, planAlignmentSteps } from "./alignment";
import { platform } from "./platform";
import { emit } from "./events";

const MAX_ALIGNMENT_ROUNDS = 2;   // avoid endless designer → role → designer loops

export async function runTask(task: Task) {
  const cwd = await workspace.prepare(task.branch);          // worktree, synced with main
  let alignmentRounds = 0;

  for (let i = 0; i < task.steps.length; i++) {
    const step = task.steps[i];
    if (step.status === "done" || step.status === "skipped") continue;

    if (task.spentUsd >= task.budgetUsd)
      return store.wait(task, "budget exhausted before step " + step.role);

    await workspace.syncWithMain(cwd);                         // rebase; on conflict → wait for a human
    await store.updateStep(task, step, { status: "running" });

    const config = roleConfig(step.role);
    const result = await runners[config.harness].run({
      role: step.role,
      prompt: buildPrompt(task, step),                         // docs/roles/<role>.md + task + previous summaries
      cwd,
      config,
      onEvent: (e) => emit(task.id, { step: step.id, ...e }),
    });

    task.spentUsd += result.costUsd;
    if (!result.ok)
      return store.fail(task, step, result.summary);

    const tests = await workspace.runTests(cwd);               // same command as the gate-test hook
    if (!tests.ok)
      return store.wait(task, "tests failing after " + step.role + ": " + tests.tail);

    await workspace.commitAndPush(cwd, task.branch, `${step.role}: ${task.title}`);
    await store.updateStep(task, step, { status: "done", summary: result.summary, costUsd: result.costUsd });

    // Alignment: new entries opened by this step
    const entries = await openAlignmentEntries(cwd);
    if (entries.length) {
      if (task.alignmentPolicy === "ask" || alignmentRounds >= MAX_ALIGNMENT_ROUNDS
          || entries.some((e) => e.decisionNeeded))
        return store.wait(task, "alignment decision needed: " + entries.map((e) => e.file).join(", "));
      alignmentRounds++;
      task.steps.splice(i + 1, 0, ...planAlignmentSteps(entries));   // designer first, then affected roles
      await store.saveSteps(task);
    }
  }

  task.prUrl = await platform.openPullRequest(task);           // one PR for all the steps
  await store.update(task, { status: "in_review" });
  await platform.comment(task, summaryOf(task));
}

function summaryOf(task: Task): string {
  return task.steps.map((s) => `- ${s.role}: ${s.summary ?? s.status}`).join("\n")
    + `\n\nCost: $${task.spentUsd.toFixed(2)}`;
}
```

And the two components that make the loop reliable:

``` {.sourceCode .typescript}
// src/alignment.ts
import { Step } from "./types";

export interface AlignmentEntry {
  file: string;                  // docs/alignment/<date>-<task>.md
  affects: string[];             // from the front matter
  decisionNeeded: boolean;
}

// Reads docs/alignment/*.md (except _template.md and README.md)
// and returns the entries with "status: open".
export async function openAlignmentEntries(cwd: string): Promise<AlignmentEntry[]> {
  /* parse the YAML front matter of each file */
  return [];
}

export function planAlignmentSteps(entries: AlignmentEntry[]): Step[] {
  const roles = [...new Set(entries.flatMap((e) => e.affects))];
  return [
    newStep("designer", "Review the open alignment entries " + entries.map((e) => e.file).join(", ")
      + ", update docs/design/ and write the follow-up actions per role."),
    ...roles.filter((r) => r !== "designer").map((r) =>
      newStep(r as Step["role"], "Carry out your follow-up actions in the open alignment entries, then mark them resolved.")),
  ];
}

declare function newStep(role: Step["role"], instructions: string): Step;
```

``` {.sourceCode .typescript}
// src/scheduler.ts
import { store } from "./store/repo";
import { runTask } from "./pipeline";
import { config } from "./config";

// One loop, many tasks: never two runs on the same branch,
// never more than maxConcurrent per role or maxTotal overall.
export async function schedulerLoop() {
  while (true) {
    const running = await store.runningCount();
    if (running < config.maxTotal) {
      const task = await store.claimNextRunnable({          // SELECT ... FOR UPDATE SKIP LOCKED
        excludeLockedBranches: true,
        roleLimits: config.roleLimits,
      });
      if (task) {
        runTask(task)
          .catch((e) => store.failTask(task, String(e)))
          .finally(() => store.releaseBranch(task.branch));
        continue;
      }
    }
    await new Promise((r) => setTimeout(r, 3000));
  }
}
```

### Design decisions not to lose

-   **The orchestrator does the Git part, not the agent.** Branching, syncing with `main`, committing, pushing and opening the PR are your own deterministic code. The agent edits files and runs tests. That way behavior does not depend on what a harness allows or refuses.
-   **The project's protections stay active.** With `settingSources: ["project"]` the Agent SDK loads `.claude/settings.json`: hooks, `permissions.deny`, the block on infrastructure commands. For OpenCode the permissions in `.opencode/agents/` apply. On top of that, the orchestrator's Git token cannot push to `main` or merge.
-   **One worktree per task, one task per branch.** That is what prevents two agents from working on the same files at the same time. The lock goes in the database, not in memory, so it survives a restart.
-   **A cap on alignment rounds.** Two rounds at most, then the task waits for you: it avoids designer → role → designer ping-pong.
-   **Budget per task, checked before every step.** The cost comes in the result of every run (`total_cost_usd` in the Agent SDK); for OpenCode you read it from LiteLLM's logs, if you use it.
-   **CI decides when a step is finished.** After pushing and opening the PR, the orchestrator reads the check status from the GitHub or GitLab APIs; if it fails, it inserts a fix step for the same role with the failed job's log, up to a maximum number of attempts, then waits for you.
-   **Webhook idempotency.** GitHub and GitLab can deliver the same event twice: record the delivery identifier and ignore duplicates.
-   **Role prompts come from the repository.** `buildPrompt` reads `docs/roles/<role>.md`, `AGENTS.md` and the summaries of previous steps of the same task. The orchestrator contains no prompts of its own, so improving a role remains a change to the repository.

### Studio mode

The orchestrator can also host the design phase: one conversation per feature in the dashboard, which produces the spec and, after the merge, the tasks. You need one more component (**Studio**), two fields in tasks (`dependsOn` and the `blocked` state, for tasks waiting on other tasks) and a small spec parser.

``` {.sourceCode .typescript}
// src/studio.ts
import { query } from "@anthropic-ai/claude-agent-sdk";
import { store } from "./store/repo";
import { workspace } from "./workspace";
import { platform } from "./platform";
import { parseSpec, tasksFromBreakdown } from "./spec";

// One message of the design conversation. The same Agent SDK session is
// resumed at every message, so the designer keeps the whole discussion.
export async function studioMessage(studioId: string, userText: string,
                                    onText: (text: string) => void) {
  const studio = await store.getStudio(studioId);           // feature, branch design/<feature>, sessionId
  const cwd = await workspace.prepare(studio.branch);

  for await (const msg of query({
    prompt: studio.sessionId
      ? userText
      : `Run a design studio session for "${studio.feature}" following docs/roles/design-studio.md.\n\n${userText}`,
    options: {
      cwd,
      resume: studio.sessionId,                               // undefined on the first message
      model: "claude-opus-5-5",
      settingSources: ["project"],
      permissionMode: "acceptEdits",
      allowedTools: ["Read", "Grep", "Glob", "Write", "Edit"], // no Bash: the designer writes specs only
    },
  })) {
    if (msg.type === "system" && msg.subtype === "init" && !studio.sessionId)
      await store.setStudioSession(studioId, msg.session_id);
    if (msg.type === "assistant")
      for (const block of msg.message.content)
        if (block.type === "text") onText(block.text);
  }
  // the draft is saved after every round, so the session can stop at any time
  await workspace.commitAndPush(cwd, studio.branch, `design: ${studio.feature} (draft)`);
}

// "Finalize" button: the checklist decides, not the conversation.
export async function finalizeStudio(studioId: string) {
  const studio = await store.getStudio(studioId);
  const spec = await parseSpec(studio.specPath);              // front matter, checklist, open questions, breakdown
  const missing = spec.checklist.filter((c) => !c.done).map((c) => c.text);
  if (!spec.ready || missing.length > 0 || spec.openQuestions.length > 0)
    return { ok: false, missing, openQuestions: spec.openQuestions };

  const prUrl = await platform.openPullRequest({ branch: studio.branch, title: `design: ${studio.feature}` });
  await store.updateStudio(studio, { status: "in_review", prUrl });
  return { ok: true, prUrl };
}

// Webhook: the design PR was merged. The breakdown becomes tasks: one team
// task if the spec allows it, otherwise one task per row, with dependencies.
export async function onDesignMerged(studioId: string) {
  const studio = await store.getStudio(studioId);
  const spec = await parseSpec(studio.specPath);
  const tasks = tasksFromBreakdown(spec, { specPath: studio.specPath });
  await store.createTasks(tasks);                             // tasks with dependsOn start as "blocked"
}
```

Three precautions:

-   **Writing stays in the design files.** The tools exclude `Bash`; to also restrict `Write` to `docs/design/` and contract drafts, use a hook like the security role's (section 3.10).
-   **The checklist decides when it is ready, not the conversation.** The "Finalize" button rejects a spec with open items and shows what is missing: it is the same rule as `docs/roles/design-studio.md`, checked by code.
-   **Tasks are born from the spec.** The "Task breakdown" table becomes orchestrator tasks with dependencies: those depending on others stay `blocked` until the previous ones are merged. If the spec says it is possible, a single team task is created. A task created this way carries the spec's path, which `buildPrompt` includes in the prompt.

### In what order to build it

| Stage | What it adds | Usable already for |
|---|---|---|
| 1 | One task, one role, Agent SDK, state in the database (section 11.2 with the store) | single tasks from the dashboard |
| 2 | Worktree per task, commit and push done by the orchestrator, PR opened via API | the full loop up to the PR |
| 3 | Several steps per task, prompts built from the role files | team tasks |
| 4 | Alignment control with the `ask` policy, then `auto` | automatic alignment even off your computer |
| 5 | GitHub and GitLab webhooks, `agent:<role>` and `agent:team` labels | the platform's board as the dashboard |
| 6 | OpenCode runner and per-role configuration | models other than Claude |
| 7 | Budgets, per-role limits, retries, cost metrics per task | continuous use |
| 8 | Studio mode: design chat, checklist verification, tasks created from the spec | the whole loop, from design to PR, from the dashboard |

Stages 1 and 2 are enough to replace architecture C; from stage 4 onwards you get what GitHub Actions cannot give you, i.e. automatic alignment even in CI, with rules you decide.


# 12. Security and limits {#sicurezza}


## 12.1 Security checklist {#checklist-di-sicurezza}

- [ ] `main` protected, MR required, human approval required
- [ ] The agents' identity can neither approve nor merge
- [ ] CODEOWNERS on migrations, auth, CI, deploy configuration
- [ ] `permissions.deny` on force pushes, merges, reading `.env` and `secrets/`
- [ ] No `bypassPermissions` in versioned files
- [ ] Secrets only as platform secrets, never in prompts or files
- [ ] `--max-turns` and a timeout on every automated job
- [ ] `optimizer` with `isolation: worktree`
- [ ] `devops` with the `PreToolUse` hook that blocks apply, deploy and push
- [ ] `security` without `Edit`, with writing limited to `docs/security/` and network limited to the hosts in `.claude/security-scope`; production never in scope
- [ ] Security reports out of Git, or in a private repository
- [ ] A security assessment once the application is complete and before every release
- [ ] Cloud, cluster and registry credentials are not reachable from the environment the agents run in
- [ ] Production environments are protected by a manual approval in the pipeline, not only by MR review
- [ ] Third-party packages (for example ECC): installed only from the official channel, at project scope, with hooks and MCP configurations read before enabling
- [ ] Agents on harnesses other than Claude Code: protections rebuilt in their permissions and, above all, at platform level (no cluster credentials on the daemon, Git token without merge)
- [ ] Agent workflows on GitHub Actions: `timeout-minutes`, `--max-turns` and a spending limit for every key, at the provider or in LiteLLM
- [ ] Skills: only those in section 4.3, no package installed in full; preloaded with `skills:` only those the role uses in almost every task
- [ ] `TaskCompleted` hook that blocks closing with red tests
- [ ] Versioned API contract, frontend types generated from the contract, non-backward-compatible changes approved by you
- [ ] Entries in `docs/alignment/` and an `## Alignment impact` section in MRs; in CI no agent starts other agents
- [ ] A single agent per task: `concurrency` on GitHub workflows, `resource_group` and explicit-only triggers on GitLab
- [ ] Team tasks: the coordinator delegates only to the roles listed in the issue, and the PR stays small enough to review
- [ ] On GitHub, "Require branches to be up to date before merging" on `main`
- [ ] No implementation task without a `ready: yes` spec; design is discussed in a studio session, not in MR comments
- [ ] The project CI (build, tests, licenses, vulnerabilities) is a required check for merging; tool versions pinned, reports kept as artifacts
- [ ] Vulnerability or license exceptions only with a reason, an expiry date and your approval
- [ ] Human review of the diff before every merge, no exceptions


## 12.2 Limits to keep in mind {#limiti}

-   The maximum number of concurrent subagents in a session is 20 by default (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`); nesting goes up to three levels (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`).
-   Teammates **cannot create teammates**: only the lead manages the team.
-   A session has **only one team**, and `/resume` does not restore in-process teammates. If you resume a session, ask the lead to respawn them.
-   Task status sometimes lags: a teammate may fail to mark a task as completed, blocking the dependent ones. If a task looks stuck, check and update it by hand.
-   The lead is fixed for the lifetime of the session: a teammate cannot be promoted.


# 13. A five-day adoption plan {#piano-adozione}

**Day 1 — Foundations.** Follow chapter 5: install Claude Code, copy the template (section 5.2) and have Claude fill it in with `SETUP.md`, which also leads you to define the project design, or create the structure and write the five agents and `CLAUDE.md`, install the skills, protect the repository. Try the agents one by one (section 6.1) and check that they stay within their boundaries; for devops, check above all that it stops where it should.

**Day 2 — Chain.** Run an entire feature with architecture A (section 6.2), with you coordinating. Note where the agents go wrong: those notes become lines in their prompts and in `CLAUDE.md`. It is the most important day of the five.

**Day 3 — Git.** Move to architecture C (chapter 8): install the GitHub or GitLab integration and try the full loop in section 8.4. Branch protection must be active *before* giving the agents write access.

**Day 4 — Dashboard.** Use issues as the dashboard (section 8.3): create three real issues, label them, watch the agents work. Tune the prompts until the summaries in the issues are useful to you.

**Day 5 — One more direction, your choice.** Try agent teams on a contained feature (chapter 7), or a second model on one role with variant 1 of architecture D (section 9.1). Compare result and cost with the previous days: if the gain is not obvious, you do not need it yet.

After two weeks: measure the real costs and apply the levers in section 4.6; then, if you like, run claude-code-setup (section 4.5) for a check of the project.


## A final recommendation {#ultima-raccomandazione}

The temptation, in a system like this, is to add agents. Almost always the real improvement comes from the other direction: more precise role prompts, sharper file boundaries, smaller tasks and hooks that verify instead of hoping. Three well-instructed agents beat eight generic ones, in quality and in cost: the roles in this guide are a repertoire to draw from, not a lineup to field in full for every match.


# 14. References {#riferimenti}

**Project template**

-   [Agent team template](https://claude.ai/artifact/QB6PBe2m3R9xtKmrpxcXnQ): the files from section 5.2, with the points to change highlighted and the zip to download.

**Official Claude Code documentation**

-   Subagents: [code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents)
-   Agent teams: [code.claude.com/docs/en/agent-teams](https://code.claude.com/docs/en/agent-teams)
-   Hooks: [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks)
-   Permissions: [code.claude.com/docs/en/permissions](https://code.claude.com/docs/en/permissions)
-   Settings: [code.claude.com/docs/en/settings](https://code.claude.com/docs/en/settings)
-   MCP: [code.claude.com/docs/en/mcp](https://code.claude.com/docs/en/mcp)
-   Skills: [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)
-   Memory and CLAUDE.md: [code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory)
-   Worktrees: [code.claude.com/docs/en/worktrees](https://code.claude.com/docs/en/worktrees)
-   GitHub Actions: [code.claude.com/docs/en/github-actions](https://code.claude.com/docs/en/github-actions)
-   GitLab CI/CD: [code.claude.com/docs/en/gitlab-ci-cd](https://code.claude.com/docs/en/gitlab-ci-cd)
-   Code Review: [code.claude.com/docs/en/code-review](https://code.claude.com/docs/en/code-review)
-   Costs: [code.claude.com/docs/en/costs](https://code.claude.com/docs/en/costs)

**Agent SDK**

-   Overview: [code.claude.com/docs/en/agent-sdk/overview](https://code.claude.com/docs/en/agent-sdk/overview)
-   Quickstart: [code.claude.com/docs/en/agent-sdk/quickstart](https://code.claude.com/docs/en/agent-sdk/quickstart)
-   TypeScript reference: [code.claude.com/docs/en/agent-sdk/typescript](https://code.claude.com/docs/en/agent-sdk/typescript)
-   Subagents in the SDK: [code.claude.com/docs/en/agent-sdk/subagents](https://code.claude.com/docs/en/agent-sdk/subagents)

**Repositories**

-   GitHub action: [github.com/anthropics/claude-code-action](https://github.com/anthropics/claude-code-action)
-   Workflow examples: [github.com/anthropics/claude-code-action/tree/main/examples](https://github.com/anthropics/claude-code-action/tree/main/examples)
-   Action security: [github.com/anthropics/claude-code-action/blob/main/docs/security.md](https://github.com/anthropics/claude-code-action/blob/main/docs/security.md)

**Third-party packages (ECC)**

-   Official repository: [github.com/affaan-m/ECC](https://github.com/affaan-m/ECC)
-   Claude Code plugin: `ecc@ecc`
-   npm package: `ecc-universal`
-   Site: [ecc.tools](https://ecc.tools)

**Multi-model dashboards**

-   Multica: [github.com/multica-ai/multica](https://github.com/multica-ai/multica)
-   LiteLLM, OpenCode integration: [docs.litellm.ai/docs/tutorials/opencode_integration](https://docs.litellm.ai/docs/tutorials/opencode_integration)
-   OpenHands, model configuration: [docs.openhands.dev/openhands/usage/llms/llms](https://docs.openhands.dev/openhands/usage/llms/llms)
-   GitHub Agent HQ: GitHub Copilot documentation, coding agent section
-   OpenCode, GitHub integration: [opencode.ai/docs/github](https://opencode.ai/docs/github)
-   LiteLLM, Docker quick start: [docs.litellm.ai/docs/proxy/docker_quick_start](https://docs.litellm.ai/docs/proxy/docker_quick_start)
-   GitHub Actions pricing: [docs.github.com](https://docs.github.com), billing section

**Improvement tools**

-   Skills directory and leaderboard: [skills.sh](https://skills.sh)
-   find-skills: [github.com/vercel-labs/skills](https://github.com/vercel-labs/skills)
-   claude-code-setup: plugin `claude-code-setup@claude-plugins-official`
-   Caveman: [github.com/juliusbrussee/caveman](https://github.com/juliusbrussee/caveman)
-   Graphify: [github.com/Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify)
-   Claude Code plugins: [code.claude.com/docs/en/plugins/overview](https://code.claude.com/docs/en/plugins/overview)
-   Claude Code mods: [code.claude.com/docs/en/plugins/mods/overview](https://code.claude.com/docs/en/plugins/mods/overview)

------------------------------------------------------------------------

*Guide written in October 2026 and reorganized into two parts, concepts and implementation. Claude Code evolves quickly and some of the features described --- in particular agent teams and the GitLab integration --- are marked experimental or beta: check the official documentation for up-to-date details before going to production.*
