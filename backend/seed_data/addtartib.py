import json

darslar = []

with open('src/db/oraliqdarslar.json', 'r', encoding='utf-8') as f:
    darslar = json.load(f)

questions = []

with open('src/db/oraliqdarslarquestion.json', 'r', encoding='utf-8') as f:
    questions = json.load(f)


new_questions = []

for d in darslar:
    d_questions = [q for q in questions if q['oraliq_dars'] == d['id']]

    for idx, q in enumerate(d_questions, start=1):
        q["tartib"] = idx
        new_questions.append(q)

def _id_key(q):
            v = q.get('id')
            try:
                return int(v)
            except Exception:
                return v if v is not None else 0

new_questions.sort(key=_id_key)
print(f'total questions before: {len(questions)}')
print(f'Total questions: {len(new_questions)}')

with open('oraliqdarslarquestiontartib.json', 'w', encoding='utf-8') as f:
    json.dump(new_questions, f, ensure_ascii=False, indent=4)