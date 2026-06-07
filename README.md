# resume-agent

Prompt-driven **LaTeX résumé builder** powered by Claude (Opus 4.8) + the
[Tectonic](https://tectonic-typesetting.github.io/) LaTeX engine.

Tell it what you want — *"build me a modern one-page resume for a backend
engineer"* — and it writes the LaTeX, compiles it to PDF, fixes any errors, and
hands you the finished file. Give it your details up front and it writes the
whole thing; or work with it conversationally and refine as you go. Save resumes
under names you choose and re-open them to edit later.

```
you › make me a clean two-column resume with a teal accent
  → writing main.tex
  → compiling main.tex
Done — compiled to main.tex → main.pdf. Want me to tweak the spacing or colors?
```

## Features

- **Any format, your call** — single- or two-column, classic or modern, academic
  CV, cover letters, custom colors, section order, a named template look. You
  describe it; the agent builds it.
- **Write-it-all or collaborate** — one-shot `build` from your details, or an
  interactive `chat`/`edit` session.
- **Always compiles** — the agent runs Tectonic and won't stop until the PDF
  builds; it reads the error log and fixes the LaTeX itself.
- **Web app with accounts** — sign in, describe a resume in the browser, watch it
  build, and view/download the PDF. Each user's resumes (and their PDFs) are
  private: the PDF endpoint is gated to its owner.
- **Saved resume library** — keep named, editable resumes (your "account") and
  re-open any of them later, from the CLI or the web UI. Rename them anytime.
- **No fabrication** — it never invents jobs, dates, or degrees; missing info
  becomes clear placeholders for you to fill in.

See [`examples/sample_resume.pdf`](examples/sample_resume.pdf) for the kind of
output it produces (that PDF is the compiled
[`examples/sample_resume.tex`](examples/sample_resume.tex)).

## Install

Requires **Python 3.10+** and **Tectonic**.

```bash
# 1. Tectonic (the LaTeX engine)
brew install tectonic            # macOS; see tectonic docs for Linux/Windows

# 2. The tool
git clone https://github.com/ruhaans05/resume-agent.git
cd resume-agent
pip install -e .                 # installs the `resume-agent` command

# 3. Your Anthropic API key  (https://console.anthropic.com/)
export ANTHROPIC_API_KEY=sk-ant-...
```

(Prefer not to install? `pip install -r requirements.txt` then run it as
`python -m resume_agent ...`.)

## Web app (sign in + browser UI)

```bash
resume-agent serve            # opens http://127.0.0.1:5000 in your browser
```

Create an account, then describe a resume and click **Build it**. The page shows
the build progress and, when ready, embeds the PDF with **Open** / **Download**
buttons. Refine it with follow-up instructions, rename it, or delete it — all in
the browser.

Accounts and resumes are stored locally under `~/.resume-agent/web/`
(SQLite for users + metadata, files per user on disk). Passwords are hashed
(Werkzeug PBKDF2) and **a resume's PDF is only served to the signed-in user who
owns it** — anyone else gets a 404, and signed-out requests are redirected to the
login page. This is a local single-host app; run it behind HTTPS/a reverse proxy
if you expose it beyond `127.0.0.1`.

## Usage (CLI)

### Build in one shot

```bash
# from a free-text prompt
resume-agent build "resume for a new-grad data scientist named Sam Lee" --open

# from a details file, in a specific style, saved under a name
resume-agent build \
  --details examples/sample_details.md \
  --style "modern single-column" \
  --name "SWE resume" \
  --open
```

### Work interactively

```bash
resume-agent chat --name "SWE resume"
# you › make the header bigger and add a Projects section
# you › /open        (open the latest PDF)
# you › /rename Backend SWE resume
# you › /exit
```

### Manage your saved resumes

```bash
resume-agent list                       # show everything you've saved
resume-agent edit "SWE resume"          # re-open and keep editing
resume-agent rename "SWE resume" "Backend resume"
resume-agent open "Backend resume"      # open its PDF
resume-agent delete "old draft"
```

Saved resumes live in `~/.resume-agent/resumes/` (override with
`RESUME_AGENT_HOME`). Each is a folder with its `main.tex`, the compiled PDF, and
a `meta.json` holding the name you chose.

## Commands

| Command | What it does |
|---|---|
| `serve [--host H] [-p PORT] [--no-browser]` | Launch the web UI (accounts + auth-gated PDFs) |
| `build [prompt] [-d FILE] [-s STYLE] [-n NAME] [-o OUT] [--open]` | Build a document end-to-end |
| `chat [-n NAME] [-w DIR]` | Interactive build/refine session |
| `edit NAME` | Re-open a saved resume and keep editing |
| `list` | List saved resumes |
| `rename OLD NEW` | Rename a saved resume |
| `open NAME` | Open a saved resume's PDF |
| `delete NAME` | Delete a saved resume |

Chat commands: `/open`, `/files`, `/rename <new name>`, `/exit`.

## How it works

`resume-agent` runs an agentic loop against the Claude Messages API. Claude is
given four tools over a sandboxed workspace — `write_file`, `read_file`,
`list_files`, and `compile_latex` — and drives them itself: it authors the LaTeX,
compiles with Tectonic, reads any errors, fixes them, and repeats until the PDF
builds. It uses `claude-opus-4-8` with adaptive thinking. All file operations are
confined to the workspace directory.

```
resume_agent/
├── cli.py        # argument parsing + commands
├── agent.py      # the Claude tool loop + system prompt
├── tools.py      # workspace sandbox + tool schemas
├── compiler.py   # Tectonic wrapper
├── library.py    # saved-resume library (named, editable)
└── webapp/       # Flask web UI: accounts, per-user storage, auth-gated PDFs
    ├── __init__.py  # routes + auth
    ├── db.py        # SQLite users + resume metadata
    ├── jobs.py      # background build jobs
    ├── templates/   # HTML
    └── static/      # CSS
```

## Using the output with Overleaf

The generated `main.tex` is standard LaTeX — upload it to an
[Overleaf](https://www.overleaf.com/) project (or paste it in) to keep editing
there. On Overleaf Premium you can also sync via its git bridge.

## License

MIT — see [LICENSE](LICENSE).
