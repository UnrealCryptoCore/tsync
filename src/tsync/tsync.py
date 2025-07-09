import uuid
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    current_app,
    session,
    jsonify
)
from .auth import login_required
from .db import get_db
from .test_parser import (
    ETest, Question, TopQuestion, Answer, parse_test
)

bp = Blueprint("tsync", __name__)


def get_etest(id, user_id) -> ETest:
    db = get_db()
    res = db.cursor().execute("SELECT ttype, name FROM etest WHERE id=?", (id,))
    testpath = res.fetchone()
    if testpath is None:
        return None
    res = db.cursor().execute(
        "SELECT id, question, html_question FROM top_question WHERE tid=?", (id,))
    tqs = res.fetchall()
    topqs = []
    test = ETest(testpath[0], testpath[1], topqs)
    for tq in tqs:
        topq = TopQuestion(tq[1], tq[2], [])
        res = db.cursor().execute(
            "SELECT question, html_question, answer, answer.sort_id, question.id FROM question, answer WHERE answer.q_id=question.id AND topid=? AND answer.user_id=?", (tq[0], user_id))
        qs = res.fetchall()
        questions = []
        for q in qs:
            quest = Question(
                q[0], q[1], Answer(q[2], q[3]))
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


def save_top_question(user_id, tid, tqs: [TopQuestion]):
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
        etest = parse_test(content)
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


@bp.get("/test/<testid>")
@login_required
def test_page(testid):
    if 'id' not in session:
        return render_template("testnotfoundtmpl.html"), 401
    user_id = session['id']
    test = get_etest(testid, user_id)
    if test is None:
        return render_template("testnotfoundtmpl.html"), 404
    return render_template("testtmpl.html", test=test, enumerate=enumerate)


@bp.post('/upload')
@login_required
def upload_file():
    # if "id" not in session:
    # return redirect("/login")
    user_id = session["id"]
    f = request.files['file']
    content = f.read()
    id, err = handle_upload(content, user_id)
    if err:
        flash(err[0], 'error')
        return render_template("indextmpl.html"), err[1]
    return redirect(f"/test/{id}")


@bp.post("/api/upload")
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


@bp.get("/tsync.user.js")
def tm_script():
    if "username" not in session:
        return redirect("/login")
    return render_template("tsync.user.js", url=current_app.config['URL']), 200, {
        'Content-Type': 'application/javascript'
    }


@bp.route("/helloworld")
def hello_world():
    return "<p>Hello, World!</p>"


@bp.get("/resources")
def resources():
    return render_template("resourcestmpl.html", res_links=current_app.config['RESOURCE_LINKS'])


@bp.get("/tampermonkey")
def tampermonkey():
    return render_template("tampermonkeytmpl.html")


@bp.route("/")
@login_required
def index():
    hist = get_history()
    return render_template("indextmpl.html", hist=hist)
