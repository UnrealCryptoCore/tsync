import bs4
import copy


class Answer:
    def __init__(self, id, value, text, tp, question_text=None, text_hash=None):
        self.id: str = id
        self.text = text
        if text_hash is not None:
            self.hash = text_hash
        else:
            self.hash: str = hash(question_text)
        self.value: str = value
        self.type: str = tp


class Question:
    def __init__(self, text):
        self.text = text
        self.hash = hash(text)
        self.answers: list[Answer] = []


class ETest:
    def __init__(self, cmid, name, answers, questions, html, page=None):
        self.cmid: str = cmid
        self.page = page
        self.name: str = name
        self.answers: list[Answer] = answers
        self.questions: list[Question] = questions
        self.html: str = html


def make_compatible(content):
    return content.decode('utf-8').replace('\r\n', '\n').replace('\n', ' ')


def path(phtml):
    path = phtml.body.findAll('li', attrs={'class': 'breadcrumb-item'})
    names = []
    for n in path:
        names.append(n.get_text().strip())
    return names


def get_name(phtml):
    p = path(phtml)
    if len(p) == 0:
        return "Unkown name"

    return "/".join(p)


def parse_query_params(params):
    res = {}
    for p in params.split('&'):
        kv = p.split('=')
        if len(kv) != 2:
            continue
        res[kv[0]] = kv[1]
    return res


def get_page(soup):
    data = soup.body.find('input', attrs={'class': 'questionflagpostdata'})
    if data is None:
        return None

    value = data['value']
    values = parse_query_params(value)
    if 'slot' not in values:
        return None
    return values['slot']


def get_cmid(form):
    cmid = form['action']
    if cmid is None:
        return

    cmid = cmid.split('?')
    if len(cmid) < 2:
        return

    cmid = cmid[1].split('&')
    if len(cmid) < 1:
        return

    for arg in cmid:
        arg = arg.split('=')
        if len(arg) < 2:
            continue
        if arg[0] == "cmid":
            return int(arg[1])

    return None


def get_text(tag):
    tag = copy.deepcopy(tag)

    selects = tag.findAll('select')
    for select in selects:
        select.decompose()

    res = []
    imgs = tag.findAll('img')
    for img in imgs:
        key = None
        if img.has_attr('href'):
            key = 'href'
        if key is not None:
            res.append(img[key])
    res = "\n".join(res)
    return (res + tag.get_text()).strip()


def find_inputs(e):
    inps = list(filter(lambda x: x['type'] != "hidden", e.findAll('input')))
    inps.extend(e.findAll('textarea') + e.findAll('select'))
    return inps


def add_solutions(soup, e, id):
    others = soup.new_tag("div")
    others.string = f"%{id.upper()}%"
    e.parent.append(others)


def add_eqation_id(soup, e, id):
    others = soup.new_tag("span")
    others.string = id
    others['style'] = "display: none;"
    e.parent.append(others)


def parse_input(soup, inp, id, qtext):
    t = inp['type']
    value = inp['value']
    if t in ["radio", "checkbox"]:
        value = '1' if 'checked' in inp.attrs else '0'

    text = get_text(inp.parent)

    return Answer(id, value, text, t, qtext)


def parse_textarea(soup, e, id, qtext):
    value = e.get_text()
    t = "textarea"
    text = get_text(e.parent.parent)
    return Answer(id, value, text, t, qtext)


def parse_select(soup, e, id, qtext):
    value = "<no selection>"
    for opt in e.findAll('option'):
        if 'selected' in opt.attrs:
            value = get_text(opt)
    t = "select"
    label = e.parent.find('label')
    if label is not None:
        label.decompose()
    text = get_text(e.parent.parent)
    return Answer(id, value, text, t, qtext)


def get_answer(soup, inp, qtext):
    if 'id' not in inp.attrs:
        return None
    id = inp['id']

    if 'type' in inp.attrs:
        return parse_input(soup, inp, id, qtext)

    if inp.name == "textarea":
        return parse_textarea(soup, inp, id, qtext)

    if inp.name == "select":
        return parse_select(soup, inp, id, qtext)

    return None


def get_answers(soup, inps, text):
    answers = []
    for inp in inps:
        res = get_answer(soup, inp, text)
        if res is not None:
            answers.append(res)
    return answers


def parse_okutable(soup, tables):
    answers = []
    questions = []
    question_text = None
    for table in tables:
        trs = table.findAll('tr')
        for tr in trs:
            extext = tr.find('td', attrs={'class': 'extext'})
            if extext is not None:
                question_text = get_text(extext)

            question = tr.find('td', attrs={'class': 'question'})
            answer = tr.find('td', attrs={'class': 'answers'})
            if question is None or answer is None:
                continue

            text = question_text+get_text(question)
            inps = find_inputs(answer)
            answers.extend(get_answers(soup, inps, text))
            questions.append(Question(text))

    return answers, questions


def parse_answers(soup, answs, text):
    answers = []
    for ans in answs:
        inps = find_inputs(ans)
        answers.extend(get_answers(soup, inps, text))
    return answers


def parse_subquestions(soup, subques, text):
    answers = []
    for subque in subques:
        inps = find_inputs(subque)
        answers.extend(get_answers(soup, inps, text))
    return answers


def parse_mathjaxloader_equations(soup, eqs, text):
    answers = []
    ht = hash(text)
    for eq in eqs:
        inps = find_inputs(eq)
        for i, inp in enumerate(inps):
            add_eqation_id(soup, inp, f"{ht}-{i}")
        answers.extend(get_answers(soup, inps, text))
    return answers


def handleLatex(soup):
    math = soup.findAll(['span', 'div'], attrs={'class': 'MathJax'})
    for e in math:
        e = e.parent
        latex = e.find('script')
        if latex is None:
            e = e.parent
            latex = e.find('script')
        e.string = latex.get_text()


def remove_tsync(soup):
    es = soup.select('[class^="tsync-"]')
    for e in es:
        e.decompose()


def remove_answerN(soup):
    ans = soup.findAll(['div', 'span'], attrs={'class': 'answernumber'})
    for an in ans:
        an.decompose()


def parse_test(content: str) -> ETest:
    content = make_compatible(content)
    soup = bs4.BeautifulSoup(content, 'html.parser')
    remove_tsync(soup)
    remove_answerN(soup)

    form = soup.body.find('form')
    if form is None:
        return None

    handleLatex(form)
    page = get_page(soup)
    cmid = get_cmid(form)
    name = get_name(soup)
    answers = []
    questions = []
    for que in form.findAll('div', attrs={'class': 'que'}):
        content = que.find('div', attrs={'class': 'content'})
        if content is None:
            continue
        outcome = content.find('div', attrs={'class': 'outcome'})
        if outcome:
            outcome.decompose()

        no = ""
        info = que.find('div', attrs={'class': 'info'})
        if info is not None:
            qno = info.find('span', attrs={'class': 'qno'})
            if qno is not None:
                no = qno.get_text()

        okutables = content.findAll('div', attrs={'class': 'okutable'})
        oku_answers, oku_questions = parse_okutable(soup, okutables)
        answers.extend(oku_answers)
        questions.extend(oku_questions)

        # okutables can contain subquestions
        # and we dont want to parse them twice
        if len(oku_questions) > 0:
            continue

        qtext = content.find('div', attrs={'class': 'qtext'})
        if qtext is not None:
            text = get_text(qtext)
            questions.append(Question(text))
        else:
            text = no  # question is somehow in the answer

        answs = content.findAll(['div', 'span', 'table'], attrs={'class': 'answer'})
        answers.extend(parse_answers(soup, answs, text))

        # subques = content.findAll(['div', 'span'], attrs={'class': 'subquestion'})
        # answers.extend(parse_subquestions(soup, subques, text))

        answs = content.findAll(['div', 'span'], attrs={
                            'class': 'filter_mathjaxloader_equation'})
        answers.extend(parse_mathjaxloader_equations(soup, answs, text))

    answers = list(filter(lambda x: x is not None, answers))
    for id in map(lambda x: x.id, answers):
        e = soup.find(id=id)
        add_solutions(soup, e, id)
    return ETest(cmid, name, answers, questions, str(form), page)
