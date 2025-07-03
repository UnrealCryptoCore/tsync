from flask import Flask, redirect, render_template, request, session, g, flash, jsonify
from dotenv import load_dotenv
import sqlite3
import bcrypt
import os
import uuid
import sys
import secrets

#import utils
from . import utils

app = Flask(__name__)
app.secret_key = os.getenv("SECRET").encode("utf-8")
app.config['UPLOAD_FOLDER'] = './data/'

salt = os.getenv("SALT").encode("utf-8")
res_links = utils.load_resource_links()
URL = os.getenv("URL")

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route("/helloworld")
def hello_world():
    return "<p>Hello, World!</p>"

@app.get("/resources")
def resources():
    return render_template("resourcestmpl.html", res_links=res_links)

@app.get("/tampermonkey")
def tamper_monkey():
    return render_template("tampermonkeytmpl.html")

@app.get("/account")
def account():
    if 'id' not in session:
        return redirect("/login"), 401
    id = session['id']
    username = session['username']
    passfail = request.args.get('passfail') in ['true', 'True', '1']
    usekey = request.args.get('key') in ['true', 'True', '1']
    key = ""
    if usekey:
        db = utils.get_db()
        res = db.execute("SELECT api_key FROM user WHERE id=?", (id,))
        res = res.fetchone()
        if res:
            key = res[0]
    return render_template("accounttmpl.html", passfail=passfail, username=username, id=id, key=key)

@app.post("/resetpass")
def reset_pass():
    if 'id' not in session:
        return redirect("/login")
    id = session['id']
    op = request.form['opass']
    np = request.form['npass']
    rp = request.form['rpass']
    if rp != np:
        return redirect("/account?passfail=true")

    db = utils.get_db()
    ohash = bcrypt.hashpw(op.encode("utf-8"), salt)
    nhash = bcrypt.hashpw(np.encode("utf-8"), salt)
    res = db.cursor().execute(
        "SELECT passhash FROM user WHERE id=? AND passhash=?", (id, ohash))
    res = res.fetchone()
    if res is None:
        return redirect("/account?passfail=true")

    res = db.cursor().execute(
        "UPDATE user SET passhash=? WHERE id=? AND passhash=?", (nhash, id, ohash))
    res = db.commit()
    return redirect("/account")

@app.post("/apikey-create")
def make_apikey():
    if 'id' not in session:
        return redirect("/login")

    id = session['id']
    key = secrets.token_urlsafe(32)

    db = utils.get_db()
    db.cursor().execute("UPDATE user SET api_key=? WHERE id=?", (key, id))
    db.commit()
    return redirect("/account?key=True")

@app.post("/apikey-delete")
def delete_apikey():
    if 'id' not in session:
        return redirect("/login")

    id = session['id']
    db = utils.get_db()
    db.cursor().execute("UPDATE user SET api_key=NULL WHERE id=?", (id,))
    db.commit()

    return redirect("/account")

@app.get("/login")
def login():
    return render_template("logintmpl.html")

@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.post("/login")
def p_login():
    username = request.form['username']
    password = request.form['password']
    hash = bcrypt.hashpw(password.encode("utf-8"), salt)
    res = utils.get_db().cursor().execute(
        "SELECT id, username, admin FROM user WHERE username=? AND passhash=?", (username, hash,))
    user = res.fetchone()
    if user is None:
        return render_template("logintmpl.html", invalid=True)
    session["id"] = user[0]
    session["username"] = user[1]
    session["admin"] = user[2]
    return redirect("/")

@app.get("/register/<username>")
def register(username):
    return username


@app.get("/test/<testid>")
def test_page(testid):
    if 'id' not in session:
        return render_template("testnotfoundtmpl.html"), 401
    user_id = session['id']
    test = utils.get_etest(testid, user_id)
    if test is None:
        return render_template("testnotfoundtmpl.html"), 404
    return render_template("testtmpl.html", test=test, enumerate=enumerate)


@app.post('/upload')
def upload_file():
    if "id" not in session:
        return redirect("/login")
    user_id = session["id"]
    f = request.files['file']
    content = f.read()
    id, err = utils.handle_upload(content, user_id)
    if err:
        flash(err[0], 'error')
        return render_template("indextmpl.html"), err[1]
    return redirect(f"/test/{id}")


@app.post("/api/upload")
def api_upload():
    key = request.headers.get("tsync-api-key")
    db = utils.get_db()

    res = db.cursor().execute("SELECT id FROM user WHERE api_key=?", (key,))
    res = res.fetchone()
    if res is None:
        return "Unauthorized: Invalid API Key", 401
    user_id = res[0]
    content = request.get_data()
    id, err = handle_upload(content, user_id)
    if err:
        return err
    return jsonify({"testid": id}), 200

@app.get("/tsync.user.js")
def tm_script():
    if "username" not in session:
        return redirect("/login")
    return render_template("tsync.user.js", url=URL), 200, {
        'Content-Type': 'application/javascript'
    }

@app.route("/")
def index():
    if "username" not in session:
        return redirect("/login")
    hist = utils.get_history()
    return render_template("indextmpl.html", hist=hist)
