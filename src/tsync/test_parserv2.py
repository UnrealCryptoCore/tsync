import bs4


class Answer:
    def __init__(self, id, value, text=None, text_hash=None):
        self.id: str = id
        if text_hash is None:
            self.hash: str = hash(text)
        else:
            self.hash = text_hash
        self.value: str = value


class ETest:
    def __init__(self, cmid, name, answers, html):
        self.cmid: str = cmid
        self.name: str = name
        self.answers: list[Answer] = answers
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
    imgs = tag.findAll('img')
    res = "\n".join([img['href'] for img in imgs])
    return res + tag.get_text()


def get_answer(soup, inp, text):
    if 'id' not in inp.attrs:
        return None
    id = inp['id']

    if 'type' not in inp.attrs:
        return None
    t = inp['type']
    if t == "hidden":
        return None
    value = inp['value']
    if t in ["radio", "checkbox"]:
        value = 'checked' in inp.attrs

    text += get_text(inp.parent)
    others = soup.new_tag("div")
    others.string = f"%{id.upper()}%"
    inp.parent.append(others)

    return Answer(id, value, text=text)


def get_answers(soup, inps, text):
    answers = []
    for inp in inps:
        res = get_answer(soup, inp, text)
        if res is not None:
            answers.append(res)
    return answers


def parse_okutable(soup, tables):
    answers = []
    for table in tables:
        trs = table.findAll('tr')
        for tr in trs:
            question = tr.find('td', attrs={'class': 'question'})
            answer = tr.find('td', attrs={'class': 'answers'})
            if question is None or answer is None:
                continue
            text = get_text(question)
            inps = answer.findAll('input')
            answers.extend(get_answers(soup, inps, text))

    return answers


def parse_answers(soup, answs, text):
    answers = []
    for ans in answs:
        inps = ans.findAll('input')
        answers.extend(get_answers(soup, inps, text))
    return answers


def parse_subquestions(soup, subques, text):
    answers = []
    for subque in subques:
        inps = subque.findAll('input')
        answers.extend(get_answers(soup, inps, text))
    return answers


def parse_test(content: str) -> ETest:
    content = make_compatible(content)
    soup = bs4.BeautifulSoup(content, 'html.parser')

    form = soup.body.find('form')
    if form is None:
        return None

    assists = form.findAll('span', attrs={'class': 'MJX_Assistive_MathML'})
    for a in assists:
        a.decompose()

    cmid = get_cmid(form)
    name = get_name(soup)
    answers = []
    for que in form.findAll('div', attrs={'class': 'que'}):
        que = que.find('div', attrs={'class': 'content'})
        if que is None:
            continue

        text = get_text(que)

        okutables = que.findAll('div', attrs={'class': 'okutable'})
        res = parse_okutable(soup, okutables)
        answers.extend(res)

        # okutables can contain subquestions
        # and we dont want to parse them twice
        if len(res) > 0:
            continue

        answs = que.findAll(['div', 'span'], attrs={'class': 'answer'})
        answers.extend(parse_answers(soup, answs, text))

        subques = que.findAll(['div', 'span'], attrs={'class': 'subquestion'})
        answers.extend(parse_subquestions(soup, subques, text))

    answers = list(filter(lambda x: x is not None, answers))
    return ETest(cmid, name, answers, str(form))
