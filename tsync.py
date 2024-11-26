from flask import Flask, redirect, render_template, request, session, g
from dotenv import load_dotenv
import sqlite3
import bcrypt
import os
import uuid
import test_parser
import sys


class User:
    def __init__(self, id, username):
        self.id = id
        self.username = username


load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET").encode("utf-8")
app.config['UPLOAD_FOLDER'] = './data/'
salt = os.getenv("SALT").encode("utf-8")

DATABASE = 'tsync.db'


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


@app.get("/account")
def account():
    if 'id' not in session:
        return redirect("/login"), 401
    id = session['id']
    username = session['username']
    passfail = request.args.get('passfail') in ['true', 'True', '1']
    return render_template("accounttmpl.html", passfail=passfail, username=username, id=id)


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
    print(res)
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
            "SELECT question, html_question, answer, question.id FROM question, answer WHERE answer.q_id=question.id AND topid=? AND answer.user_id=?", (tq[0], user_id))
        qs = res.fetchall()
        questions = []
        for q in qs:
            quest = test_parser.Question(q[0], q[1], q[2])
            questions.append(quest)
            res = db.cursor().execute("SELECT answer, user.username FROM answer, user WHERE user_id!=? AND user.id=answer.user_id AND answer.tid=? AND answer.q_id=?", (user_id, id, q[3]))
            '''res = db.cursor().execute(
                "SELECT question.answer, user.username FROM question, user WHERE question.topid=? AND question.question=? AND question.user_id!=? and user.id=question.user_id", (tq[0], q[0], user_id))'''
            others = res.fetchall()
            quest.others = {}
            print(id, others)
            for other in others:
                if other[0] in quest.others:
                    quest.others[other[0]].append(other[1])
                else:
                    quest.others[other[0]] = [other[1]]

        topq.q = questions
        topqs.append(topq)
    return test


@app.get("/test/<testid>")
def test_page(testid):
    if 'id' not in session:
        return render_template("testnotfoundtmpl.html"), 401
    user_id = session['id']
    test = get_etest(testid, user_id)
    if test is None:
        return render_template("testnotfoundtmpl.html"), 404
    return render_template("testtmpl.html", test=test)


def get_test_by_path(ttype, name, mktest):
    db = get_db()
    res = db.cursor().execute(
        "SELECT id FROM etest WHERE ttype=? AND name=?", (ttype, name))

    test = res.fetchone()
    print(test)
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


def save_top_question(user_id, tid, tq: [test_parser.TopQuestion]):
    db = get_db()
    res = db.cursor().execute(
        "SELECT id FROM top_question WHERE tid=? AND question=?", (tid, tq.h))
    id = res.fetchone()
    if id is None:
        id = str(uuid.uuid4())
        db.cursor().execute(
            "INSERT INTO top_question (id, tid, user_id, question, html_question) VALUES (?, ?, ?, ?, ?)", (id, tid, user_id, tq.h, tq.html_h))
    else:
        id = id[0]
    for q in tq.q:
        res = db.cursor().execute(
            "SELECT id FROM question WHERE topid=? AND question=?", (id, q.q))
        res = res.fetchone()
        if res is None:
            qid = str(uuid.uuid4())
            db.cursor().execute(
                "INSERT INTO question (id, topid, user_id, question, html_question) VALUES (?, ?, ?, ?, ?)", (qid, id, user_id, q.q, q.html_q))
        else:
            qid = res[0]
        aid = str(uuid.uuid4())
        db.cursor().execute(
            "INSERT INTO answer (id, tid, q_id, user_id, answer) VALUES (?, ?, ?, ?, ?)", (aid, tid, qid, user_id, q.a))

    db.commit()


@app.post('/upload')
def upload_file():
    f = request.files['file']
    content = f.read()
    try:
        etest = test_parser.parse_test(content)
    except Exception:
        return redirect("/?badfile=true"), 402
    mktest = 'admin' in session and session['admin']
    id = get_test_by_path(etest.ttype, etest.name, mktest)
    if id is None:
        return "Test does not exist", 403
    user_id = session["id"]
    for tq in etest.q:
        save_top_question(user_id, id, tq)
    return redirect(f"/test/{id}")


def get_history():
    db = get_db()
    res = db.cursor().execute("SELECT id, name, ttype FROM etest")
    res = res.fetchall()
    return res


@app.route("/")
def index():
    if "username" not in session:
        return redirect("/login")
    hist = get_history()
    badfile = request.args.get('badfile') in ['True', 'true']
    return render_template("indextmpl.html", hist=hist, badfile=badfile)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == 'release':
        app.run(host='0.0.0.0', port=25566)
    else:
        app.run(debug=True)
