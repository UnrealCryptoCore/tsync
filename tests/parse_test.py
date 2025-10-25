import sys
sys.path.insert(1, 'src/tsync')
import test_parserv2

html = open("data/afi13.html", "r").read().encode()
test = test_parserv2.parse_test(html)
print(test.cmid)
print(test.name)
for q in test.questions:
    print(q.text)
for a in test.answers:
    print(a.text)
    print()
