from google import genai
import dotenv
import pydantic
import json
import time

ALPHABET = [chr(i) for i in range(ord('A'), ord('Z')+1)]


class SingleChoice(pydantic.BaseModel):
    number: int
    confidence: float
    text: str


class MultipleChoice(pydantic.BaseModel):
    numbers: list[bool]
    confidence: float


class TextAnswer(pydantic.BaseModel):
    answer: str
    confidence: float


class AIModel:
    def __init__(self):
        self.client = genai.Client()
        with open("ai_template.txt") as f:
            self.templ = f.read()

    def make_content(self, question, anserType, answers):
        if answers is not None:
            answers = [f"{i+1}) {a}" for i, a in enumerate(answers)]
            answers = "\n".join(answers)
        else:
            answers = ""
        content = self.templ.replace("$question", question).replace("$answers", answers)
        return content

    def answer_question(self, question, answerType, answers=None):
        content = self.make_content(question, answerType, answers)
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            config=genai.types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=answerType),
            contents=content,
        )
        return json.loads(response.text)

    def answer_question_demo(self, question, answerType, answers=None, sleeptime=None):
        content = self.make_content(question, answerType, answers)
        if sleeptime is not None:
            time.sleep(sleeptime)
        print(content)
        if answerType == TextAnswer:
            key = 'answer'
            values = '42'
        elif answerType == SingleChoice:
            key = 'number'
            values = 1
        elif answerType == MultipleChoice:
            key = 'numbers'
            values = [False for _ in answers]
        return {
            key: values,
            'confidence': 1.0,
        }


if __name__ == "__main__":
    quest = """
    Bestimmen Sie das größtmögliche R≥0

, so dass die Reihe

∑k=1∞xkk2

für alle x∈R
mit |x|<R

absolut konvergiert.

Geben Sie Ihr Ergebnis ggf. auf drei Nachkommastellen genau ein und verwenden Sie ein Komma statt eines Punktes bei der Angabe von Dezimalzahlen.
   """
    dotenv.load_dotenv()
    model = AIModel()
    res = model.answer_question(quest, [])
    print(res)
