# Collaborator Setup Guide

This is a step-by-step guide for team members who need to push code to the team's main repository:
**`https://github.com/elham715/ICT_Fest_Hackathon_Preliminary.git`**

---

## Who Can Push?

Only people with **push access** to the repo can push directly to `main`. Two ways to get access:

1. **Be added as a collaborator** on the GitHub repo (Settings → Collaborators → Add people)
2. **Use a Personal Access Token (PAT)** if you are a collaborator or have been given one

---

## One-Time Setup (pick ONE path)

### Path A: Use HTTPS + Personal Access Token (Recommended)

**Step 1 — Create a PAT** (skip if you already have one):
1. Open https://github.com/settings/tokens/new
2. Fill in:
   - **Note:** `hackathon-push` (or anything memorable)
   - **Expiration:** your choice (30 days, 90 days, or no expiry)
   - **Scopes:** check **`repo`** (full control of private repositories)
3. Click **Generate token**
4. **Copy the token** immediately — GitHub only shows it once

**Step 2 — Tell git who you are:**
```bash
cd /path/to/cowork-preliminary
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

**Step 3 — Cache your token in macOS keychain:**
```bash
git config --global credential.helper osxkeychain
```

**Step 4 — First push (will prompt for credentials):**
```bash
./scripts/collab-push.sh "first push"
```
When prompted:
- **Username:** your GitHub username
- **Password:** paste your PAT (NOT your GitHub password)

After the first successful push, the token is cached in keychain and you won't be prompted again.

---

### Path B: Use SSH (Alternative)

**Step 1 — Generate an SSH key** (skip if you have one):
```bash
ssh-keygen -t ed25519 -C "your.email@example.com"
# Press Enter to accept default path
# Optionally set a passphrase
```

**Step 2 — Add your public key to GitHub:**
1. Copy the public key: `cat ~/.ssh/id_ed25519.pub`
2. Open https://github.com/settings/keys
3. Click **New SSH key**
4. Title: any name (e.g., `mylaptop`)
5. Paste the key, click **Add SSH key**

**Step 3 — Switch the remote to SSH:**
```bash
cd /path/to/cowork-preliminary
./scripts/switch-to-ssh.sh
```

**Step 4 — First push (no prompts):**
```bash
./scripts/collab-push.sh "first push"
```

---

## Daily Workflow

Once setup is done, all your work follows this loop:

```bash
cd /path/to/cowork-preliminary

# 1. Make your code changes
# 2. Push them
./scripts/collab-push.sh "what I changed and why"

# 3. If push fails, see "Troubleshooting" below
```

---

## Scripts Provided

| Script | What it does |
|--------|--------------|
| `scripts/collab-push.sh "msg"` | **The main one** — stage, commit, rebase-pull, push |
| `scripts/switch-to-ssh.sh` | Switch remote URL from HTTPS to SSH |
| `scripts/test-auth.sh` | Verify your auth setup works |
| `scripts/setup-token.sh` | Configure HTTPS token (interactive) |

---

## Switching Between Collaborators

If two people share the same machine, **commit authorship is per-person** (use your own `user.name`/`user.email`). Push access is per-GitHub-account (use your own PAT or SSH key).

To check who you are configured as:
```bash
git config user.name
git config user.email
```

To set yourself as the committer for this repo only (not globally):
```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

---

## Working on Lanes / Avoiding Conflicts

The team has split the work into 8 lanes under `Bug_fix/`. To avoid stepping on each other:

1. **Claim a lane** by telling the team which folder you're working on
2. **Touch only the files listed** in that lane's `fix_script.md` (`Files To Edit` section)
3. **Run `git pull --rebase` before starting work** every time
4. **Commit small, often** — one bug per commit is best
5. **Write a clear commit message** referencing the lane, e.g.:
   - "Lane 8: add lock to reference counter"
   - "Lane 5: thread-safe rate-limit bucket"
   - "Lane 6: fix refund half-up rounding"

---

## What NOT To Do

- ❌ Don't push directly to `main` while another collaborator is mid-edit — wait or coordinate
- ❌ Don't use `git push --force` unless absolutely necessary (and ask the team first)
- ❌ Don't commit `.env` files, secrets, API keys, or the local SQLite `cowork.db` (the `.gitignore` already excludes these)
- ❌ Don't commit changes to `Bug_fix/<lane>/issues.md` — that's the team's shared triage doc
- ❌ Don't amend commits that other people may have pulled

---

## Troubleshooting

### "Permission denied (publickey)"
You're using SSH but your key isn't on GitHub. Switch to HTTPS+PAT (Path A above).

### "Authentication failed"
Your PAT is wrong, expired, or doesn't have `repo` scope. Generate a new one or check scopes.

### "Updates were rejected because the tip of your current branch is behind"
Someone else pushed while you were working. Run:
```bash
git pull --rebase
./scripts/collab-push.sh "your message"
```

### "CONFLICT" during rebase
You and another collaborator edited the same file. Resolve manually:
```bash
# Edit the conflicted files
git add <fixed-files>
git rebase --continue
./scripts/collab-push.sh "your message"
```

### "fatal: not a git repository"
You're not inside the `cowork-preliminary` folder. `cd` into it first.

### "dubious ownership"
You're inside a `.git` owned by another user. Run:
```bash
git config --global --add safe.directory /path/to/cowork-preliminary
```

---

## Contact

If you're stuck, ask the team lead (Elham / `elham715` on GitHub) for push access or a token.

Repository: **https://github.com/elham715/ICT_Fest_Hackathon_Preliminary**
