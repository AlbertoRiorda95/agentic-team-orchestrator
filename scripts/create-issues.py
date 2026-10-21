#!/usr/bin/env python3
"""Create GitHub or GitLab issues from the roadmap and the specs (guide 8.3).

The roadmap in docs/design/project.md drives the structure:
  - one milestone per roadmap row ("M0 · ...", "M1 · ..."): a native
    GitHub/GitLab milestone, with its progress bar, not an issue;
  - in it, for every feature of that milestone:
      * the tasks of its spec, if the spec is ready (one issue per row of the
        "Task breakdown", or one agent:team issue with --team);
      * otherwise one "Design: <feature>" issue (design happens with you).
Specs that no milestone covers get their task issues without a milestone.
Sub-issues are left for scripts/split-issue.py: the parts of one task.
A milestone is matched by its code ("M0"), so renaming its features in the
roadmap does not create a second one; issues that already have a milestone
keep it.

A spec covers roadmap features in two ways: its file name matches the feature
(docs/design/task-board.md <-> "Task board"), or its front matter lists them:
    milestone: M0
    features: Walking skeleton, CI
That is how the foundations spec covers the first milestone, without creating
"Design:" issues for work it already plans.

An optional fifth column "Issue" in the Task breakdown marks rows that need no
new issue: "#12" (already tracked by that issue, which gets the milestone if it has
none) or "done". Leave it empty, or "-", for rows to create.

Issues get no labels: an agent starts only when you add agent:<role> to a task
issue. The script never closes issues and changes existing ones only to give
a milestone to those that have none: existing titles are skipped, and issues it
created that are no longer in the plan are listed so you can close them. Run it again after every studio session.

Usage:
  python3 scripts/create-issues.py --dry-run      # show the plan
  python3 scripts/create-issues.py                # create what is missing
  python3 scripts/create-issues.py --team         # one agent:team issue per spec that allows it
  python3 scripts/create-issues.py --migrate      # move from the old "M0 · ..." parent issues

--migrate is for repositories set up with an earlier version of this script,
which made one parent issue per milestone with the tasks as sub-issues (GitHub)
or linked issues (GitLab). It creates the milestones, assigns them to those
tasks, detaches the tasks from the parent issues and lists the parent issues
for you to close. Combine it with --dry-run to see what it would do.

Needs a Git remote (origin) and an authenticated `gh` (GitHub) or `glab`
(GitLab). Exit code 2 when the remote or the CLI is missing.
"""
import argparse, glob, json, os, re, subprocess, sys

DESIGN = "docs/design"
ROLES = {"designer", "frontend", "backend", "optimizer", "devops", "security"}
MARK = "<!-- created-by: scripts/create-issues.py -->"


def sh(cmd, inp=None):
    return subprocess.run(cmd, input=inp, capture_output=True, text=True)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def front(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.split("#")[0].strip()
    return meta


def items(value):
    return [x.strip(" '\"") for x in re.split(r"[,;]", value.strip("[] ")) if x.strip(" '\"")]


def section(text, name):
    m = re.search(r"^## " + re.escape(name) + r"\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


def table(block):
    rows = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|") or re.match(r"^\|[\s:|-]+\|$", line):
            continue
        rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows[1:] if rows else []


def load_spec(path):
    text = open(path, encoding="utf-8").read()
    meta = front(text)
    if meta.get("ready") != "yes":
        return None
    title = re.search(r"^# (.+)$", text, re.M)
    title = re.sub(r"\s+[—-]\s+.*$", "", title.group(1)).strip() if title else os.path.basename(path)
    block = section(text, "Task breakdown")
    rows = [r for r in table(block) if len(r) >= 3 and r[0].strip().isdigit() and r[2] not in ("", "...")]
    team = re.search(r"Team task possible:\s*yes\b.*?roles?:\s*([^)]+)\)", block, re.I | re.S)
    return {"path": path, "title": title, "rows": rows,
            "slug": slug(os.path.splitext(os.path.basename(path))[0]),
            "milestone": meta.get("milestone", ""), "features": items(meta.get("features", "")),
            "team_roles": [x for x in items(team.group(1).replace("\n", " ")) if x.lower() in ROLES] if team else None}


def load_roadmap():
    path = os.path.join(DESIGN, "project.md")
    if not os.path.exists(path):
        return []
    out = []
    for r in table(section(open(path, encoding="utf-8").read(), "Roadmap")):
        if len(r) >= 2 and r[0] not in ("", "..."):
            out.append((r[0], [f for f in items(r[1]) if f != "..."]))
    return out


def tracked(r):
    """The Issue column: None (create), 'done', or an issue number."""
    v = r[4].strip() if len(r) > 4 else ""
    if v in ("", "-", "—"):
        return None
    m = re.match(r"#?(\d+)$", v)
    return int(m.group(1)) if m else "done"


def task_issues(spec, team):
    """[(key, title, body, dep_keys, ref)] for one spec; ref is None, 'done' or an issue number."""
    out = []
    for r in spec["rows"]:
        ref = tracked(r)
        if ref is not None:
            out.append(((spec["path"], r[0].strip()), None, None, [], ref))
    rows = [r for r in spec["rows"] if tracked(r) is None]
    if not rows:
        return out
    if team and spec["team_roles"]:
        lines = "\n".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3] if len(r) > 3 else '-'} |" for r in rows)
        nums = ", ".join(r[0] for r in rows)
        out.append(((spec["path"], "team"), f"{spec['title']} · team task (tasks {nums})",
                    f"## Spec\n{spec['path']} - section: Task breakdown, rows {nums}\n\n"
                    f"## Task\nImplement these tasks of the breakdown on one branch, one PR:\n\n"
                    f"| # | Role | Task | Depends on |\n|---|---|---|---|\n{lines}\n\n"
                    f"Roles: {', '.join(spec['team_roles'])}\n\n"
                    f"To start it, add the label `agent:team`.\n\n{MARK}", [], None))
        return out
    total = len(spec["rows"])
    for r in rows:
        num, role, task = r[0].strip(), r[1].strip().lower(), r[2].strip()
        deps = re.findall(r"\d+", r[3]) if len(r) > 3 else []
        short = task if len(task) <= 70 else task[:67].rstrip() + "..."
        out.append(((spec["path"], num), f"{spec['title']} · {num}/{total} · {role}: {short}",
                    f"## Spec\n{spec['path']} - section: Task breakdown, row {num}\n\n"
                    f"## Task\n{task}\n\n## Depends on\n{{deps}}\n\n"
                    f"To start it, add the label `agent:{role}` once the issues it depends on are merged.\n\n{MARK}",
                    [(spec["path"], d) for d in deps], None))
    return out


def build_plan(team):
    specs = [s for s in (load_spec(p) for p in sorted(glob.glob(os.path.join(DESIGN, "*.md")))
                         if not os.path.basename(p).startswith("_")
                         and os.path.basename(p) not in ("project.md", "README.md")) if s]
    used, groups = set(), []          # groups: (milestone or None, [issues])
    for milestone, feats in load_roadmap():
        children = []
        for feat in feats:
            spec = next((s for s in specs if s["slug"] == slug(feat)
                         or (slug(feat) in map(slug, s["features"])
                             and (not s["milestone"] or s["milestone"] == milestone))), None)
            if spec:
                if spec["path"] not in used:
                    used.add(spec["path"])
                    children += task_issues(spec, team)
                continue
            children.append(((milestone, feat), f"Design: {feat} ({milestone})",
                             f"## Roadmap\nMilestone {milestone}, feature \"{feat}\" (docs/design/project.md).\n\n"
                             f"## Task\nDesign this feature in a studio session with you: `/design-studio {slug(feat)}`. "
                             f"It produces docs/design/{slug(feat)}.md; once it is ready and merged, run "
                             f"`python3 scripts/create-issues.py` again to create its task issues in this milestone.\n\n"
                             f"No agent label: design happens with you, not in CI.\n\n{MARK}", [], None))
        ms = (milestone, f"{milestone} · {', '.join(feats)}"[:120],
              f"Roadmap milestone {milestone}: {', '.join(feats)} (docs/design/project.md).\n"
              f"Created by scripts/create-issues.py.")
        groups.append((ms, children))
    for s in specs:
        if s["path"] not in used:
            groups.append((None, task_issues(s, team)))
    return groups


def code(title):
    """The milestone code at the start of a title: "M0 · Walking skeleton" -> "M0"."""
    return title.split(" · ")[0].strip()


def run(cmd):
    p = sh(cmd)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p.stdout


class Platform:
    def __init__(self, kind):
        self.kind = kind
        self._repo = None

    @property
    def repo(self):
        if not self._repo:
            self._repo = run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]).strip()
        return self._repo

    def glab(self, args):
        return json.loads(run(["glab"] + args) or "null")

    def gh(self, args):
        return [json.loads(l) for l in run(["gh", "api"] + args).splitlines() if l.strip()]

    def existing(self):
        """{title: {number, state, ours, old_parent, milestone}}"""
        def info(n, state, body, ms):
            body = body or ""
            return {"number": n, "state": state, "ours": MARK in body, "milestone": ms,
                    "old_parent": MARK in body and body.startswith("## Milestone ")}
        if self.kind == "github":
            out = run(["gh", "issue", "list", "--state", "all", "--limit", "2000",
                       "--json", "number,title,state,body,milestone"])
            return {i["title"]: info(i["number"], i["state"].lower(), i["body"],
                                     (i.get("milestone") or {}).get("title"))
                    for i in json.loads(out or "[]")}
        found, page = {}, 1
        while True:
            items_ = self.glab(["api", f"projects/:fullpath/issues?state=all&per_page=100&page={page}"])
            found.update({i["title"]: info(i["iid"], i["state"], i["description"],
                                           (i.get("milestone") or {}).get("title")) for i in items_})
            if len(items_) < 100:
                return found
            page += 1

    def milestones(self):
        """{code: (ref, title)}; ref is the number (GitHub) or the id (GitLab)."""
        if self.kind == "github":
            rows = [(m["number"], m["title"]) for m in self.gh(
                ["--paginate", f"repos/{self.repo}/milestones?state=all&per_page=100",
                 "--jq", ".[] | {number, title}"])]
        else:
            rows, page = [], 1
            while True:
                ms = self.glab(["api", f"projects/:fullpath/milestones?per_page=100&page={page}"])
                rows += [(m["id"], m["title"]) for m in ms]
                if len(ms) < 100:
                    break
                page += 1
        return {code(t): (ref, t) for ref, t in rows}

    def create_milestone(self, title, description):
        if self.kind == "github":
            return self.gh(["-X", "POST", f"repos/{self.repo}/milestones", "-f", f"title={title}",
                            "-f", f"description={description}", "--jq", "{number}"])[0]["number"]
        return self.glab(["api", "-X", "POST", "projects/:fullpath/milestones", "-f", f"title={title}",
                          "-f", f"description={description}"])["id"]

    def create(self, title, body, ms):
        if self.kind == "github":
            extra = ["-F", f"milestone={ms}"] if ms else []
            return self.gh(["-X", "POST", f"repos/{self.repo}/issues", "-f", f"title={title}",
                            "-f", f"body={body}", *extra, "--jq", "{number}"])[0]["number"]
        extra = ["-f", f"milestone_id={ms}"] if ms else []
        return self.glab(["api", "-X", "POST", "projects/:fullpath/issues", "-f", f"title={title}",
                          "-f", f"description={body}", *extra])["iid"]

    def set_milestone(self, n, ms):
        if self.kind == "github":
            run(["gh", "api", "-X", "PATCH", f"repos/{self.repo}/issues/{n}", "-F", f"milestone={ms}"])
        else:
            run(["glab", "api", "-X", "PUT", f"projects/:fullpath/issues/{n}", "-f", f"milestone_id={ms}"])

    def old_children(self, parent):
        """[(child number, handle to detach it)] under an old milestone issue."""
        if self.kind == "github":
            return [(c["number"], c["id"]) for c in self.gh(
                ["--paginate", f"repos/{self.repo}/issues/{parent}/sub_issues", "--jq", ".[] | {number, id}"])]
        return [(c["iid"], c["issue_link_id"])
                for c in self.glab(["api", f"projects/:fullpath/issues/{parent}/links"]) or []]

    def detach(self, parent, handle):
        if self.kind == "github":
            run(["gh", "api", "-X", "DELETE", f"repos/{self.repo}/issues/{parent}/sub_issue",
                 "-F", f"sub_issue_id={handle}"])
        else:
            run(["glab", "api", "-X", "DELETE", f"projects/:fullpath/issues/{parent}/links/{handle}"])


def detect(forced):
    if forced:
        return forced
    p = sh(["git", "remote", "get-url", "origin"])
    if p.returncode:
        return None
    return "github" if "github.com" in p.stdout else "gitlab"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--team", action="store_true")
    ap.add_argument("--migrate", action="store_true")
    ap.add_argument("--platform", choices=["github", "gitlab"])
    a = ap.parse_args()

    kind = detect(a.platform)
    if not kind:
        print("No Git remote 'origin' yet. Create the repository on GitHub or GitLab, push, "
              "then run: python3 scripts/create-issues.py --dry-run", file=sys.stderr)
        return 2
    plat = Platform(kind)
    try:
        existing = plat.existing()
        milestones = plat.milestones()
    except (RuntimeError, FileNotFoundError) as e:
        cli = "gh" if kind == "github" else "glab"
        if not a.dry_run:
            print(f"Cannot read the issues with {cli}: {e}\nInstall and authenticate {cli}, then run again.",
                  file=sys.stderr)
            return 2
        print(f"(dry run: {cli} not available, existing issues and milestones not checked)")
        existing, milestones = {}, {}
    by_number = {v["number"]: v for v in existing.values()}

    groups = build_plan(a.team)
    if not groups and not a.migrate:
        print("Nothing to do: no roadmap in docs/design/project.md and no ready spec with a Task breakdown.")
        return 0
    numbers, planned, done = {}, set(), set()
    count = {"issues": 0, "milestones": 0, "assigned": 0, "detached": 0}

    def ensure_ms(ms_code, title, description):
        if ms_code in milestones:
            ref, t = milestones[ms_code]
            print(f"milestone exists   {t}" if ref else f"milestone planned  {t}")
            return ref
        if a.dry_run:
            print(f"milestone create   {title}")
            milestones[ms_code] = (None, title)
            return None
        ref = plat.create_milestone(title, description)
        milestones[ms_code] = (ref, title)
        count["milestones"] += 1
        print(f"milestone created  {title}")
        return ref

    def assign(n, ms_ref, ms_title, indent):
        """Give the milestone to an existing issue that has none."""
        if not ms_title or by_number.get(n, {}).get("milestone"):
            return
        if a.dry_run:
            print(f"{indent}    -> gets milestone {ms_title}")
            return
        plat.set_milestone(n, ms_ref)
        by_number.setdefault(n, {})["milestone"] = ms_title
        count["assigned"] += 1
        print(f"{indent}    -> milestone {ms_title}")

    def ensure(key, title, body, deps, ref, ms_ref, ms_title, indent=""):
        if ref == "done":
            numbers[key] = None
            done.add(key)
            print(f"{indent}done          task {key[1]} of {key[0]}")
            return
        if ref is not None:
            numbers[key] = ref
            print(f"{indent}tracked #{ref}  task {key[1]} of {key[0]}")
            assign(ref, ms_ref, ms_title, indent)
            return
        planned.add(title)
        if title in existing:
            numbers[key] = existing[title]["number"]
            print(f"{indent}exists  #{numbers[key]}  {title}")
            assign(numbers[key], ms_ref, ms_title, indent)
            return
        dep_txt = ", ".join(f"#{numbers[d]}" if numbers.get(d) else (f"task {d[1]} (done)" if d in done else f"task {d[1]}")
                            for d in deps) or "none"
        if a.dry_run:
            numbers[key] = None
            print(f"{indent}create        {title}" + (f"   (depends on: {dep_txt})" if deps else ""))
            return
        numbers[key] = plat.create(title, body.replace("{deps}", dep_txt), ms_ref)
        count["issues"] += 1
        print(f"{indent}created #{numbers[key]}  {title}")

    for ms, children in groups:
        ms_ref = ensure_ms(*ms) if ms else None
        ms_title = milestones[ms[0]][1] if ms else None
        for child in children:
            ensure(*child, ms_ref, ms_title, indent="    " if ms else "")

    old = sorted((v["number"], t) for t, v in existing.items()
                 if v["old_parent"] and v["state"] in ("open", "opened"))
    if old and not a.migrate:
        print(f"\n{len(old)} milestone issue(s) from the old layout (milestones are now native):")
        for n, t in old:
            print(f"  #{n}  {t}")
        print("Run python3 scripts/create-issues.py --migrate --dry-run (it moves their tasks, if any, into the milestones), then close them.")
    if a.migrate:
        print("\nMigration from the old milestone issues:" if old else "\nMigration: no old milestone issues found.")
        in_plan = {ms[0]: ms for ms, _ in groups if ms}
        for n, t in old:
            c = code(t)
            ms_ref = ensure_ms(*in_plan.get(c, (c, t, "Created by scripts/create-issues.py --migrate.")))
            for child, handle in plat.old_children(n):
                print(f"    #{child} " + ("would be detached from" if a.dry_run else "detached from") + f" #{n}")
                assign(child, ms_ref, milestones[c][1], "    ")
                if not a.dry_run:
                    plat.detach(n, handle)
                    count["detached"] += 1
        if old:
            print("\nClose these old milestone issues once you have checked the milestones:")
            for n, t in old:
                print(f"  #{n}  {t}")

    stale = [(v["number"], t) for t, v in existing.items()
             if v["ours"] and not v["old_parent"] and v["state"] in ("open", "opened") and t not in planned]
    if stale:
        print("\nCreated by this script but no longer in the plan (close them if obsolete):")
        for n, t in sorted(stale):
            print(f"  #{n}  {t}")
    if not a.dry_run:
        print(f"\n{count['issues']} issue(s) and {count['milestones']} milestone(s) created, "
              f"{count['assigned']} issue(s) given a milestone"
              + (f", {count['detached']} detached from old milestone issues." if a.migrate else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())