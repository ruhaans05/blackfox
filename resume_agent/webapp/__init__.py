"""Flask web UI for resume-agent: accounts, per-user resumes, auth-gated PDFs."""

from __future__ import annotations

import functools

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, jobs


def create_app() -> Flask:
    app = Flask(__name__)
    db.init_db()
    app.secret_key = db.secret_key()

    # -- auth helpers --------------------------------------------------------

    def current_user():
        uid = session.get("user_id")
        return db.get_user(uid) if uid else None

    def login_required(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)

        return wrapped

    def owned_resume(resume_id: int):
        """Return the resume row iff it belongs to the signed-in user, else 404."""
        r = db.get_resume(resume_id)
        if r is None or r["user_id"] != session.get("user_id"):
            abort(404)
        return r

    @app.context_processor
    def inject_user():
        return {"user": current_user()}

    # -- auth routes ---------------------------------------------------------

    @app.route("/")
    def index():
        return redirect(url_for("dashboard" if session.get("user_id") else "login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            pw = request.form.get("password") or ""
            if "@" not in email or "." not in email:
                flash("Enter a valid email address.")
            elif len(pw) < 6:
                flash("Password must be at least 6 characters.")
            elif db.get_user_by_email(email):
                flash("An account with that email already exists.")
            else:
                uid = db.create_user(email, generate_password_hash(pw))
                session.clear()
                session["user_id"] = uid
                return redirect(url_for("dashboard"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            pw = request.form.get("password") or ""
            user = db.get_user_by_email(email)
            if user and check_password_hash(user["password_hash"], pw):
                session.clear()
                session["user_id"] = user["id"]
                nxt = request.args.get("next")
                return redirect(nxt or url_for("dashboard"))
            flash("Incorrect email or password.")
        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # -- resume routes -------------------------------------------------------

    @app.route("/dashboard")
    @login_required
    def dashboard():
        resumes = db.list_resumes(session["user_id"])
        return render_template("dashboard.html", resumes=resumes)

    @app.route("/resumes", methods=["POST"])
    @login_required
    def create_resume():
        name = (request.form.get("name") or "").strip()
        description = (request.form.get("description") or "").strip()
        if not name or not description:
            flash("Give your resume a name and describe what you want.")
            return redirect(url_for("dashboard"))
        rid = db.create_resume(session["user_id"], name)
        jobs.start_build(session["user_id"], rid, description)
        return redirect(url_for("resume", resume_id=rid))

    @app.route("/resumes/<int:resume_id>")
    @login_required
    def resume(resume_id: int):
        r = owned_resume(resume_id)
        has_pdf = db.resume_pdf(r["user_id"], resume_id) is not None
        return render_template("resume.html", r=r, has_pdf=has_pdf)

    @app.route("/resumes/<int:resume_id>/status")
    @login_required
    def resume_status(resume_id: int):
        r = owned_resume(resume_id)
        return {
            "status": r["status"],
            "has_pdf": db.resume_pdf(r["user_id"], resume_id) is not None,
        }

    @app.route("/resumes/<int:resume_id>/refine", methods=["POST"])
    @login_required
    def refine_resume(resume_id: int):
        r = owned_resume(resume_id)
        change = (request.form.get("description") or "").strip()
        if change:
            jobs.start_build(r["user_id"], resume_id, change, refine=True)
        return redirect(url_for("resume", resume_id=resume_id))

    @app.route("/resumes/<int:resume_id>/rename", methods=["POST"])
    @login_required
    def rename_resume(resume_id: int):
        owned_resume(resume_id)
        name = (request.form.get("name") or "").strip()
        if name:
            db.rename_resume(resume_id, name)
        return redirect(url_for("resume", resume_id=resume_id))

    @app.route("/resumes/<int:resume_id>/delete", methods=["POST"])
    @login_required
    def delete_resume(resume_id: int):
        owned_resume(resume_id)
        db.delete_resume(resume_id)
        return redirect(url_for("dashboard"))

    @app.route("/resumes/<int:resume_id>/pdf")
    @login_required
    def resume_pdf_file(resume_id: int):
        r = owned_resume(resume_id)  # 404 unless the signed-in user owns it
        pdf = db.resume_pdf(r["user_id"], resume_id)
        if pdf is None:
            abort(404)
        download = request.args.get("download")
        return send_file(
            pdf,
            mimetype="application/pdf",
            as_attachment=bool(download),
            download_name=f"{r['slug']}.pdf",
        )

    return app
