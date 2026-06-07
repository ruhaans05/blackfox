"""Background resume-build jobs so web requests don't block on the agent."""

from __future__ import annotations

import threading
import traceback

from resume_agent.agent import ResumeAgent

from . import db


def _instruction(description: str, refine: bool) -> str:
    base = description.strip() + (
        "\n\nBuild the document end to end and compile it to PDF (main.tex). "
        "Use clear placeholders for any missing personal details; never invent facts."
    )
    if refine:
        return "Read the current main.tex first, then apply this change:\n\n" + base
    return base


def start_build(user_id: int, resume_id: int, description: str, refine: bool = False) -> None:
    rdir = db.resume_dir(user_id, resume_id)

    def work() -> None:
        try:
            db.set_status(resume_id, "building")
            agent = ResumeAgent(rdir)
            agent.run_turn(_instruction(description, refine))
            db.set_status(resume_id, "ready" if agent.ws.latest_pdf() else "error")
        except Exception:
            traceback.print_exc()
            db.set_status(resume_id, "error")

    threading.Thread(target=work, daemon=True).start()
