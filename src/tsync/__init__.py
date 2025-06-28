from flask import Flask, redirect, render_template, request, session, g, flash, jsonify
from dotenv import load_dotenv
import sqlite3
import bcrypt
import os
import uuid
import sys
import secrets


def load_resource_links():
    try:
        lines = open("resourcelinks.txt").readlines()
        links = [line.split("=") for line in lines]
        links = [(link[0].strip(), link[1].strip()) for link in links]
        print(links)
        return links
    except FileNotFoundError:
        return []


def create_app():
    from . import test_parser

    load_dotenv()
    res_links = load_resource_links()

    salt = os.getenv("SALT").encode("utf-8")
    DATABASE = 'tsync.db'
    URL = os.getenv("URL")

    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET").encode("utf-8")
    app.config['UPLOAD_FOLDER'] = './data/'

    def get_db():
        db = getattr(g, '_database', None)
        if db is None:
            db = g._database = sqlite3.connect(DATABASE)
        return db

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
            db = get_db()
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

        db = get_db()
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

        db = get_db()
        db.cursor().execute("UPDATE user SET api_key=? WHERE id=?", (key, id))
        db.commit()
        return redirect("/account?key=True")

    @app.post("/apikey-delete")
    def delete_apikey():
        if 'id' not in session:
            return redirect("/login")

        id = session['id']
        db = get_db()
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
        res = get_db().cursor().execute(
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

    def get_etest(id, user_id) -> test_parser.ETest:
        db = get_db()
        res = db.cursor().execute("SELECT ttype, name FROM etest WHERE id=?", (id,))
        testpath = res.fetchone()
        if testpath is None:
            return None
        res = db.cursor().execute(
            "SELECT id, question, html_question FROM top_question WHERE tid=?", (id,))
        tqs = res.fetchall()
        topqs = []
        test = test_parser.ETest(testpath[0], testpath[1], topqs)
        for tq in tqs:
            topq = test_parser.TopQuestion(tq[1], tq[2], [])
            res = db.cursor().execute(
                "SELECT question, html_question, answer, answer.sort_id, question.id FROM question, answer WHERE answer.q_id=question.id AND topid=? AND answer.user_id=?", (tq[0], user_id))
            qs = res.fetchall()
            questions = []
            for q in qs:
                quest = test_parser.Question(
                    q[0], q[1], test_parser.Answer(q[2], q[3]))
                questions.append(quest)
                res = db.cursor().execute(
                    "SELECT answer, user.username FROM answer, user WHERE user_id!=? AND user.id=answer.user_id AND answer.tid=? AND answer.q_id=?", (user_id, id, q[4]))
                others = res.fetchall()
                quest.others = {}
                for other in others:
                    if other[0] in quest.others:
                        quest.others[other[0]].append(other[1])
                    else:
                        quest.others[other[0]] = [other[1]]

            topq.q = questions
            topqs.append(topq)
        test.sort()
        return test

    @app.get("/test/<testid>")
    def test_page(testid):
        if 'id' not in session:
            return render_template("testnotfoundtmpl.html"), 401
        user_id = session['id']
        test = get_etest(testid, user_id)
        if test is None:
            return render_template("testnotfoundtmpl.html"), 404
        return render_template("testtmpl.html", test=test, enumerate=enumerate)

    def get_test_by_path(ttype, name, mktest):
        db = get_db()
        res = db.cursor().execute(
            "SELECT id FROM etest WHERE ttype=? AND name=?", (ttype, name))

        test = res.fetchone()
        if test is None and mktest:
            id = str(uuid.uuid4())
            res = db.cursor().execute(
                "INSERT INTO etest (id, ttype, name) VALUES (?, ?, ?)", (id, ttype, name))
            db.commit()
            test = id
        else:
            test = test[0]
        return test

    def clear_questions(user_id, tid):
        db = get_db()
        db.cursor().execute("DELETE FROM answer WHERE user_id=? AND tid=?", (user_id, tid))
        db.commit()

    def save_top_question(user_id, tid, tqs: [test_parser.TopQuestion]):
        db = get_db()
        res = db.cursor().execute(
            "SELECT id FROM top_question WHERE tid=? AND question=?", (tid, tqs.h))
        id = res.fetchone()
        if id is None:
            id = str(uuid.uuid4())
            db.cursor().execute(
                "INSERT INTO top_question (id, tid, user_id, question, html_question) VALUES (?, ?, ?, ?, ?)", (id, tid, user_id, tqs.h, tqs.html_h))
        else:
            id = id[0]
        for q in tqs.q:
            res = db.cursor().execute(
                "SELECT id FROM question WHERE topid=? AND question=?", (id, q.q))
            res = res.fetchone()
            if res is None:
                qid = str(uuid.uuid4())
                db.cursor().execute(
                    "INSERT INTO question (id, topid, user_id, question, html_question) VALUES (?, ?, ?, ?, ?)", (qid, id, user_id, q.q, q.html_q))
            else:
                qid = res[0]
                db.cursor().execute(
                    "DELETE FROM answer WHERE tid=? AND q_id=? AND user_id=?", (tid, qid, user_id))
            aid = str(uuid.uuid4())
            db.cursor().execute(
                "INSERT INTO answer (id, tid, q_id, user_id, answer, sort_id) VALUES (?, ?, ?, ?, ?, ?)", (aid, tid, qid, user_id, q.a.val, q.a.sortId))

        db.commit()

    def handle_upload(content: str, user_id: str):
        try:
            etest = test_parser.parse_test(content)
        except Exception:
            return None, ("Input file is invalid", 400)
        # mktest = 'admin' in session and session['admin']
        mktest = True
        id = get_test_by_path(etest.ttype, etest.name, mktest)
        if id is None:
            return None, ("Test does not exist", 403)
        for tq in etest.q:
            save_top_question(user_id, id, tq)
        return id, None

    @app.post('/upload')
    def upload_file():
        if "id" not in session:
            return redirect("/login")
        user_id = session["id"]
        f = request.files['file']
        content = f.read()
        id, err = handle_upload(content, user_id)
        if err:
            flash(err[0], 'error')
            return render_template("indextmpl.html"), err[1]
        return redirect(f"/test/{id}")

    def get_history():
        db = get_db()
        res = db.cursor().execute("SELECT id, name, ttype FROM etest")
        res = res.fetchall()

        modules = {
            'afi': [],
            'ds': [],
            'ti': [],
            'la': [],
            'fosap': []}

        for (id, name, ttype) in res:
            modules[ttype].append((id, name, ttype))

        return modules

    @app.post("/api/upload")
    def api_upload():
        key = request.headers.get("tsync-api-key")
        db = get_db()

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
        hist = get_history()
        return render_template("indextmpl.html", hist=hist)

    return app


if __name__ == "__main__":
    app = create_app()
    if len(sys.argv) == 2 and sys.argv[1] == 'release':
        app.run(host='0.0.0.0', port=25566)
    else:
        app.run(debug=True)
