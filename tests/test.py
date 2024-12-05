try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup


def answers(phtml):
    anst = phtml.body.findAll('td', attrs={'class': 'answers'})
    ans = []
    for a in anst:
        ans.append(a.find('input').get('value'))
    return ans


def questions(phtml):
    qst = parsed_html.body.findAll('td', attrs={'class': 'question'})
    qs = []
    for a in qst:
        qs.append(a.get_text())
    return qs


html = open("data/bl5.html", "r").read()
parsed_html = BeautifulSoup(html, 'html.parser')
a = answers(parsed_html)
q = questions(parsed_html)
print(a)
print(q)
print(zip(a, q))

# print(parsed_html.body.find('div', attrs={'class': 'container'}).text)
