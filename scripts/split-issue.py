#!/usr/bin/env python3
"""Split one issue into task issues, one per role (guide section 8.3).

Two steps, with your approval in between:
  1. propose: Claude writes a plan file; this script checks it and posts it as
     a comment on the issue. Nothing is created.
  2. create: after your "@claude ok", this script creates exactly the plan in
     the latest proposal comment, as sub-issues of the issue (GitHub) or
     linked issues (GitLab). The model is not involved in this step.

Usage:
  python3 scripts/split-issue.py check   <plan.json>
  python3 scripts/split-issue.py propose <issue> <plan.json>
  python3 scripts/split-issue.py create  <issue> [--team]

Plan format (JSON):
  {
    "parent": 42,                          # the issue being split
    "summary": "Why this split, in two or three sentences.",
    "spec": "docs/design/orders.md",       # optional: the spec it implements
    "tasks": [                             # 1 to 6 tasks, in execution order
      {
        "key": "contract",                 # lowercase letters, digits, hyphens
        "role": "backend",                 # designer frontend backend devops optimizer security
        "title": "Add the date filter to the orders API contract",
        "task": "What to do, in a few sentences.",
        "acceptance": ["Checkable without reading the code", "..."],
        "files": ["docs/api/openapi.yaml"],
        "depends_on": []                   # keys of earlier tasks
      }
    ],
    "team": {                              # optional: suggest one agent:team issue
      "roles": ["backend", "frontend"],
      "reason": "Small and tightly coupled."
    }
  }

The created issues get no labels and the parent's milestone, if it has one: start each task by adding agent:<role> once
the issues it depends on are merged. Running create twice creates nothing new:
tasks already created for this issue (same key) are skipped. At the end the
agent:split label is removed from the issue.

Needs `gh` (GitHub) or `glab` (GitLab), authenticated; in CI the workflow
provides the token.
"""
import json, os, re, subprocess, sys

ROLES = ["designer", "frontend", "backend", "devops", "optimizer", "security"]
MAX_TASKS = 6
START, END = "<!-- split-plan v1 -->", "<!-- split-plan-end -->"
LABEL = "agent:split"


def sh(cmd, inp=None):
    return subprocess.run(cmd, input=inp, capture_output=True, text=True)


def run(cmd, inp=None):
    p = sh(cmd, inp)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:4])}...: {p.stderr.strip() or p.stdout.strip()}")
    return p.stdout


def jlines(out):
    return [json.loads(l) for l in out.splitlines() if l.strip()]


# ---------------------------------------------------------------- the plan

def validate(plan, issue=None):
    """Return a list of problems; empty when the plan is usable."""
    err = []
    if not isinstance(plan, dict):
        return ["the plan must be a JSON object"]
    if issue is not None and plan.get("parent") != issue:
        err.append(f'"parent" must be {issue}')

    def text(where, value, limit, required=True):
        if not isinstance(value, str) or (required and not value.strip()):
            err.append(f"{where}: missing or not a string")
            return
        if len(value) > limit:
            err.append(f"{where}: longer than {limit} characters")
        if "```" in value or "<!--" in value:
            err.append(f"{where}: must not contain ``` or <!--")

    text("summary", plan.get("summary"), 800)
    if "spec" in plan:
        text("spec", plan["spec"], 200)
    tasks = plan.get("tasks")
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= MAX_TASKS:
        err.append(f'"tasks" must list 1 to {MAX_TASKS} tasks; with more, split the issue into features first')
        return err
    keys = []
    for i, t in enumerate(tasks, 1):
        w = f"task {i}"
        if not isinstance(t, dict):
            err.append(f"{w}: not an object")
            continue
        k = t.get("key")
        if not isinstance(k, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,29}", k):
            err.append(f'{w}: "key" must be 1-30 lowercase letters, digits or hyphens')
        elif k in keys:
            err.append(f'{w}: duplicate key "{k}"')
        if t.get("role") not in ROLES:
            err.append(f'{w}: "role" must be one of {", ".join(ROLES)}')
        text(f"{w} title", t.get("title"), 90)
        text(f"{w} task", t.get("task"), 2000)
        acc = t.get("acceptance")
        if not isinstance(acc, list) or not 1 <= len(acc) <= 10:
            err.append(f'{w}: "acceptance" must list 1 to 10 criteria')
        else:
            for j, a in enumerate(acc, 1):
                text(f"{w} acceptance {j}", a, 300)
        files = t.get("files", [])
        if not isinstance(files, list) or len(files) > 15:
            err.append(f'{w}: "files" must be a list of at most 15 paths')
        else:
            for j, f in enumerate(files, 1):
                text(f"{w} file {j}", f, 200)
        deps = t.get("depends_on", [])
        if not isinstance(deps, list) or any(d not in keys for d in deps):
            err.append(f'{w}: "depends_on" may only list keys of earlier tasks')
        keys.append(k)
    team = plan.get("team")
    if team is not None:
        roles = team.get("roles") if isinstance(team, dict) else None
        used = {t.get("role") for t in tasks if isinstance(t, dict)}
        if not isinstance(roles, list) or len(roles) < 2 or any(r not in used for r in roles):
            err.append('"team.roles" must list at least two roles used by the tasks')
        else:
            text("team reason", team.get("reason"), 300)
    return err


def render(plan, kind):
    tasks, n = plan["tasks"], plan["parent"]
    idx = {t["key"]: i for i, t in enumerate(tasks, 1)}
    rows = "\n".join(
        f"| {i} | {t['role']} | {t['title']} | {', '.join(str(idx[d]) for d in t.get('depends_on', [])) or '-'} |"
        for i, t in enumerate(tasks, 1))
    details = []
    for i, t in enumerate(tasks, 1):
        acc = "\n".join(f"- {a}" for a in t["acceptance"])
        files = ", ".join(f"`{f}`" for f in t.get("files", [])) or "-"
        details.append(f"**{i} · {t['role']}: {t['title']}**\n\n{t['task']}\n\nAcceptance:\n{acc}\n\nFiles: {files}")
    team = plan.get("team")
    if kind == "github":
        ok = f"reply `@claude ok` to create these {len(tasks)} issues as sub-issues of #{n}, without labels"
        ok_team = "reply `@claude ok team` to create one `agent:team` issue instead"
        change = "reply `@claude` followed by what to change: a new proposal replaces this one"
    else:
        ok = (f"run the pipeline with `SPLIT_ISSUE={n}` and `SPLIT_CONFIRM=ok` to create these "
              f"{len(tasks)} issues, linked to #{n}, without labels")
        ok_team = "use `SPLIT_CONFIRM=team` to create one team-task issue instead"
        change = f"run it with `SPLIT_ISSUE={n}` and `SPLIT_FEEDBACK` set to what to change"
    team_txt = (f"**Team task:** possible with roles {', '.join(team['roles'])}. {team['reason']}"
                if team else "**Team task:** not suggested.")
    lines = [START, f"### Proposed split of #{n}", "", plan["summary"],
             (f"\nSpec: `{plan['spec']}`" if plan.get("spec") else ""), "",
             "| # | Role | Task | Depends on |", "|---|---|---|---|", rows, "",
             "<details><summary>Task details</summary>", "", "\n\n---\n\n".join(details), "", "</details>", "",
             team_txt, "", f"**To confirm**, {ok}." + (f" Or {ok_team}." if team else ""),
             f"**To change it**, {change}.", "",
             "<details><summary>Plan data (what the confirmation creates)</summary>", "",
             "```json", json.dumps(plan, indent=2, ensure_ascii=False), "```", "", "</details>", END]
    return "\n".join(lines)


def parse(body):
    m = re.search(re.escape(START) + r".*?```json\n(.*?)\n```", body or "", re.S)
    return json.loads(m.group(1)) if m else None


# ---------------------------------------------------------------- platforms

class GitHub:
    kind = "github"

    def __init__(self):
        self.repo = os.environ.get("GITHUB_REPOSITORY") or run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]).strip()
        me = sh(["gh", "api", "user", "--jq", ".login"])   # fails with a CI token: then only bots count
        self.me = me.stdout.strip() if me.returncode == 0 else None

    def api(self, *args):
        return run(["gh", "api", *args])

    def comment(self, n, body):
        run(["gh", "issue", "comment", str(n), "--body-file", "-"], body)

    def issue(self, n):
        i = json.loads(self.api(f"repos/{self.repo}/issues/{n}"))
        return {"title": i["title"], "labels": [l["name"] for l in i["labels"]],
                "milestone": (i.get("milestone") or {}).get("number")}

    def latest_plan(self, n):
        """Body of the latest proposal posted by a bot, or by you when run locally."""
        found = None
        for c in jlines(self.api("--paginate", f"repos/{self.repo}/issues/{n}/comments",
                                 "--jq", ".[] | {body, type: .user.type, login: .user.login}")):
            if (c["type"] == "Bot" or (self.me and c["login"] == self.me)) and START in (c["body"] or ""):
                found = c["body"]
        return found

    def children(self, n):
        out = self.api("--paginate", f"repos/{self.repo}/issues/{n}/sub_issues",
                       "--jq", ".[] | {number, id, body}")
        return [(c["number"], c["id"], c["body"] or "") for c in jlines(out)]

    def create(self, title, body, milestone=None):
        extra = ["-F", f"milestone={milestone}"] if milestone else []
        i = json.loads(self.api("-X", "POST", f"repos/{self.repo}/issues", "-f", f"title={title}",
                                "-f", f"body={body}", *extra, "--jq", "{number, id}"))
        return i["number"], i["id"]

    def attach(self, parent, child_id):
        self.api("-X", "POST", f"repos/{self.repo}/issues/{parent}/sub_issues", "-F", f"sub_issue_id={child_id}")

    def block(self, n, blocker_id):
        """Native "blocked by" relation; best effort, the issue body says it anyway."""
        return sh(["gh", "api", "-X", "POST", f"repos/{self.repo}/issues/{n}/dependencies/blocked_by",
                   "-F", f"issue_id={blocker_id}"]).returncode == 0

    def unlabel(self, n):
        sh(["gh", "issue", "edit", str(n), "--remove-label", LABEL])


class GitLab:
    kind = "gitlab"

    def __init__(self):
        self.p = "projects/" + (os.environ.get("CI_PROJECT_ID") or ":fullpath")
        self.me = json.loads(run(["glab", "api", "user"]))["id"]
        self.pid = json.loads(run(["glab", "api", self.p]))["id"]

    def api(self, *args):
        out = run(["glab", "api", *args])
        return json.loads(out or "null")

    def comment(self, n, body):
        self.api("-X", "POST", f"{self.p}/issues/{n}/notes", "-f", f"body={body}")

    def issue(self, n):
        i = self.api(f"{self.p}/issues/{n}")
        return {"title": i["title"], "labels": i["labels"], "milestone": (i.get("milestone") or {}).get("id")}

    def latest_plan(self, n):
        """Body of the latest proposal posted with this job's token (never trust a user's copy)."""
        notes = self.api(f"{self.p}/issues/{n}/notes?sort=desc&order_by=created_at&per_page=100") or []
        for c in notes:
            if not c.get("system") and c["author"]["id"] == self.me and START in (c["body"] or ""):
                return c["body"]
        return None

    def children(self, n):
        return [(c["iid"], c["iid"], c.get("description") or "")
                for c in self.api(f"{self.p}/issues/{n}/links") or []]

    def create(self, title, body, milestone=None):
        extra = ["-f", f"milestone_id={milestone}"] if milestone else []
        i = self.api("-X", "POST", f"{self.p}/issues", "-f", f"title={title}", "-f", f"description={body}", *extra)
        return i["iid"], i["iid"]

    def attach(self, parent, child_iid):
        self.api("-X", "POST", f"{self.p}/issues/{parent}/links",
                 "-f", f"target_project_id={self.pid}", "-f", f"target_issue_iid={child_iid}")

    def block(self, n, blocker_iid):
        """"Blocked by" links need a paid plan; best effort, the issue body says it anyway."""
        return sh(["glab", "api", "-X", "POST", f"{self.p}/issues/{n}/links", "-f", f"target_project_id={self.pid}",
                   "-f", f"target_issue_iid={blocker_iid}", "-f", "link_type=is_blocked_by"]).returncode == 0

    def unlabel(self, n):
        sh(["glab", "api", "-X", "PUT", f"{self.p}/issues/{n}", "-f", f"remove_labels={LABEL}"])


def platform():
    if os.environ.get("GITHUB_ACTIONS"):
        return GitHub()
    if os.environ.get("GITLAB_CI"):
        return GitLab()
    url = sh(["git", "remote", "get-url", "origin"]).stdout
    if not url:
        sys.exit("No Git remote 'origin': this script works on GitHub or GitLab issues.")
    return GitHub() if "github.com" in url else GitLab()


# ---------------------------------------------------------------- commands

def load(path, issue=None):
    try:
        plan = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"Cannot read {path}: {e}", file=sys.stderr)
        return None
    err = validate(plan, issue)
    if err:
        print("The plan has problems, fix them and run again:\n- " + "\n- ".join(err), file=sys.stderr)
        return None
    return plan


def how(kind, role, num):
    """How to start a task issue on each platform."""
    if kind == "github":
        return f"add the label `agent:{role}`"
    task = "this issue's number" if num == "#" else num
    if role == "team":
        return f"run the `claude-team` job with `TASK_ID` = {task}, `AI_FLOW_INPUT` and `AI_FLOW_ROLES`"
    return f"run the `claude` job with `TASK_ID` = {task} and `AI_FLOW_INPUT` (the {role} task)"


def marker(n, key):
    return f"<!-- split-of: #{n} key: {key} -->"


def create(plat, n, team):
    body = plat.latest_plan(n)
    plan = parse(body) if body else None
    if not plan or validate(plan, n):
        sys.exit(f"No valid proposal on #{n}: add the {LABEL} label (GitHub) or run the proposal job first.")
    if team and not plan.get("team"):
        sys.exit("The proposal does not suggest a team task: confirm with plain ok, or ask for a new proposal.")
    info = plat.issue(n)
    parent, ms = info["title"], info.get("milestone")
    approver = os.environ.get("SPLIT_APPROVER", "")
    done = {}
    for num, ref, b in plat.children(n):
        m = re.search(r"<!-- split-of: #\d+ key: ([a-z0-9-]+) -->", b)
        if m:
            done[m.group(1)] = (num, ref)
    if team and set(done) - {"team"}:
        sys.exit(f"#{n} already has task issues from this split: it cannot also become a team task.")
    if not team and "team" in done:
        sys.exit(f"#{n} already has a team-task issue from this split (#{done['team'][0]}).")
    tasks, made, notes = plan["tasks"], [], []
    short = parent if len(parent) <= 60 else parent[:57].rstrip() + "..."
    spec = f"\n\nSpec: `{plan['spec']}`" if plan.get("spec") else ""
    by = f" (approved by @{approver})" if approver else ""

    if team:
        key = "team"
        if key in done:
            print(f"exists  #{done[key][0]}  team task")
        else:
            rows = "\n".join(f"| {i} | {t['role']} | {t['title']} |" for i, t in enumerate(tasks, 1))
            acc = "\n".join(f"- [ ] {a}" for t in tasks for a in t["acceptance"])
            title = f"{short} · team task"
            b = (f"## Parent\n#{n}{by}{spec}\n\n## Task\n{plan['summary']}\n\n| # | Role | Task |\n|---|---|---|\n{rows}\n\n"
                 f"## Acceptance criteria\n{acc}\n\nRoles: {', '.join(plan['team']['roles'])}\n\n"
                 f"To start it: {how(plat.kind, 'team', '#')}.\n\n{marker(n, key)}")
            num, ref = plat.create(title, b, ms)
            plat.attach(n, ref)
            made.append((num, "team", title))
            print(f"created #{num}  {title}")
    else:
        for i, t in enumerate(tasks, 1):
            if t["key"] in done:
                print(f"exists  #{done[t['key']][0]}  {t['title']}")
                continue
            deps = t.get("depends_on", [])
            dep_txt = ", ".join(f"#{done[d][0]}" for d in deps if d in done) or "none"
            acc = "\n".join(f"- [ ] {a}" for a in t["acceptance"])
            files = "\n".join(f"- `{f}`" for f in t.get("files", [])) or "-"
            title = f"{short} · {i}/{len(tasks)} · {t['role']}: {t['title']}"[:250]
            b = (f"## Parent\n#{n}{by}{spec}\n\n## Task\n{t['task']}\n\n## Acceptance criteria\n{acc}\n\n"
                 f"## Files\n{files}\n\n## Depends on\n{dep_txt}\n\n"
                 f"To start it, once the issues it depends on are merged: {how(plat.kind, t['role'], '#')}.\n\n"
                 f"{marker(n, t['key'])}")
            num, ref = plat.create(title, b, ms)
            done[t["key"]] = (num, ref)
            plat.attach(n, ref)
            for d in deps:
                if d in done and not plat.block(num, done[d][1]):
                    notes.append(f"#{num} depends on #{done[d][0]}: written in the issue, not as a native link")
            made.append((num, t["role"], title))
            print(f"created #{num}  {title}")

    plat.unlabel(n)
    if made:
        lst = "\n".join(f"- #{num} ({role})" for num, role, _ in made)
        msg = (f"Created {len(made)} issue(s) from the approved split{by}:\n\n{lst}\n\n"
               f"Start with #{made[0][0]}: {how(plat.kind, made[0][1], made[0][0])}. No labels were added.")
        if notes:
            msg += "\n\n" + "\n".join(f"- {x}" for x in notes)
        plat.comment(n, msg)
    print(f"{len(made)} issue(s) created; the {LABEL} label was removed from #{n}.")


def main(argv):
    if len(argv) >= 2 and argv[0] == "check":
        return 0 if load(argv[1]) else 1
    if len(argv) >= 3 and argv[0] == "propose":
        n = int(argv[1].lstrip("#"))
        plan = load(argv[2], n)
        if not plan:
            return 1
        plat = platform()
        plat.comment(n, render(plan, plat.kind))
        print(f"Proposal posted on #{n}.")
        return 0
    if len(argv) >= 2 and argv[0] == "create":
        create(platform(), int(argv[1].lstrip("#")), "--team" in argv[2:])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))