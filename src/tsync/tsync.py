from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    current_app,
    session,
    jsonify,
    g,
)
from markupsafe import Markup
from .auth import login_required, api_key_required
from .db import get_db
from .test_parserv2 import (
    parse_test as parse_testv2,
    ETest as Etestv2,
    Answer as Answer_v2,
)

bp = Blueprint("tsync", __name__)


def get_etest_v2(cmid, user_id):
    db = get_db()
    res = db.cursor().execute(
        "SELECT name, html FROM etest_v2 WHERE cmid=? AND user_id=?", (cmid, user_id))
    etest = res.fetchone()
    if etest is None:
        return None, None
    etest = Etestv2(cmid, etest[0], [], etest[1])
    res = db.cursor().execute(
        "SELECT id, hash, value FROM answer_v2 WHERE cmid=? AND user_id=?", (cmid, user_id))
    answers = res.fetchall()
    groups = []
    for i, ans in enumerate(answers):
        ans = Answer_v2(ans[0], ans[2], text_hash=ans[1])
        answers[i] = ans
        res = db.cursor().execute(
            """
            SELECT
                answer_v2.value, user.username
            FROM
                answer_v2, user
            WHERE
                answer_v2.hash=?
                AND user.id=answer_v2.user_id
            """,
            (ans.hash, ))
        res = res.fetchall()
        group = {
            ans.value: []
        }
        for v in res:
            if v[0] in group:
                group[v[0]].append(v[1])
            else:
                group[v[0]] = [v[1]]
        groups.append(group)
    etest.answers = answers
    return etest, groups


def save_etest(user_id, etest):
    db = get_db()
    db.cursor().execute("INSERT into etest_v2 (user_id, cmid, name, html) VALUES (?, ?, ?, ?)",
                        (user_id, etest.cmid, etest.name, etest.html))
    for quest in etest.answers:
        db.cursor().execute("INSERT into answer_v2 (cmid, id, user_id, hash, value) VALUES (?, ?, ?, ?, ?)",
                            (etest.cmid, quest.id, user_id, quest.hash, quest.value))
    db.commit()


def backup_test(etest, content):
    pass


def handle_upload_v2(content: str, user_id: str):
    try:
        etest = parse_testv2(content)
    except Exception:
        return None, ("Input file is invalid.", 400)
    save_etest(user_id, etest)
    backup_test(etest, content)
    return etest.cmid, None


def get_history(user_id):
    db = get_db()
    res = db.cursor().execute(
        "SELECT cmid, name FROM etest_v2 WHERE user_id=?", (user_id, ))
    res = res.fetchall()

    return res


def answer_to_html(ans, group):
    s = ""
    for v in group:
        if ans.value == v:
            if len(group[v]) == 1:
                tp = "answer-unknown"
            else:
                tp = "answer-same"
        else:
            tp = "answer-different"
        s += f"<div class='{tp}'>{v}: {", ".join(group[v])}</div>"
    return s


@bp.get("/test/<testid>")
@login_required
def test_page(testid):
    user_id = session['id']
    test, groups = get_etest_v2(testid, user_id)
    if test is None:
        return render_template("testnotfoundtmpl.html"), 404
    render = test.html
    for ans, group in zip(test.answers, groups):
        s = answer_to_html(ans, group)
        render = render.replace(f"%{ans.id.upper()}%", s)
    render = Markup(render)
    return render_template("testtmpl_v2.html", name=test.name, test_render=render)


@bp.post('/upload')
@login_required
def upload_file():
    user_id = session["id"]
    f = request.files['file']
    content = f.read()
    id, err = handle_upload_v2(content, user_id)
    if err:
        flash(err[0], 'error')
        return render_template("indextmpl.html"), err[1]
    return redirect(f"/test/{id}")


@bp.post("/api/upload")
@api_key_required
def api_upload():
    user_id = g.user_id
    content = request.get_data()
    id, err = handle_upload_v2(content, user_id)
    if err:
        return err
    return jsonify({"testid": id}), 200


@bp.get("/api/solutions/<cmid>")
@api_key_required
def api_solutions(cmid):
    user_id = g.user_id
    test, groups = get_etest_v2(cmid, user_id)
    if test is None:
        return None, 404

    res = {}
    for ans, group in zip(test.answers, groups):
        res[ans.id] = answer_to_html(ans, group)
    return jsonify(res), 200


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
    user_id = session["id"]
    hist = get_history(user_id)
    return render_template("indextmpl.html", hist=hist)
