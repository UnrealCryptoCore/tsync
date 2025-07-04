import functools
import secrets
import bcrypt

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    session,
    url_for,
    current_app,
)
from werkzeug.security import check_password_hash, generate_password_hash

from tsync.db import get_db

bp = Blueprint('auth', __name__)


def login_required(view):
    """View decorator that redirects anonymous users to the login page."""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'id' not in session:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view


@bp.get("/account")
def account():
    if 'id' not in session:
        return redirect("/login"), 401
    id = session['id']
    username = session['username']
    passfail = request.args.get('passfail') in ['true', 'True', '1']
    usekey = request.args.get('key') in ['true', 'True', '1']
    key = ""
    if usekey:
        db = get_db()
        res = db.execute("SELECT api_key FROM user WHERE id=?", (id,))
        res = res.fetchone()
        if res:
            key = res[0]
    return render_template("accounttmpl.html", passfail=passfail, username=username, id=id, key=key)


@bp.post("/resetpass")
def reset_pass():
    if 'id' not in session:
        return redirect("/login")
    id = session['id']
    op = request.form['opass']
    np = request.form['npass']
    rp = request.form['rpass']
    if rp != np:
        return redirect("/account?passfail=true")

    db = get_db()
    ohash = bcrypt.hashpw(op.encode("utf-8"), current_app.config['PEPPER'])
    nhash = bcrypt.hashpw(np.encode("utf-8"), current_app.config['PEPPER'])
    res = db.cursor().execute(
        "SELECT passhash FROM user WHERE id=? AND passhash=?", (id, ohash))
    res = res.fetchone()
    if res is None:
        return redirect("/account?passfail=true")

    res = db.cursor().execute(
        "UPDATE user SET passhash=? WHERE id=? AND passhash=?", (nhash, id, ohash))
    res = db.commit()
    return redirect("/account")


@bp.post("/apikey-create")
def make_apikey():
    if 'id' not in session:
        return redirect("/login")

    id = session['id']
    key = secrets.token_urlsafe(32)

    db = get_db()
    db.cursor().execute("UPDATE user SET api_key=? WHERE id=?", (key, id))
    db.commit()
    return redirect("/account?key=True")


@bp.post("/apikey-delete")
def delete_apikey():
    if 'id' not in session:
        return redirect("/login")

    id = session['id']
    db = get_db()
    db.cursor().execute("UPDATE user SET api_key=NULL WHERE id=?", (id,))
    db.commit()

    return redirect("/account")


@bp.get("/login")
def login():
    return render_template("logintmpl.html")


@bp.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@bp.post("/login")
def p_login():
    username = request.form['username']
    password = request.form['password']
    hash = bcrypt.hashpw(password.encode("utf-8"), current_app.config['PEPPER'])
    res = get_db().cursor().execute(
        "SELECT id, username, admin FROM user WHERE username=? AND passhash=?", (username, hash,))
    user = res.fetchone()
    if user is None:
        return render_template("logintmpl.html", invalid=True)
    session["id"] = user[0]
    session["username"] = user[1]
    session["admin"] = user[2]
    return redirect("/")


@bp.get("/register/<username>")
def register(username):
    return username
