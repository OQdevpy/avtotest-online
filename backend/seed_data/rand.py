import json 
import random

qs = json.load(open('/home/avtotest/Desktop/new/src/db/oraliqdarslarquestion.json'))
random.shuffle(qs)


with open('/home/avtotest/Desktop/new/src/db/new_question.json', 'w', encoding='utf-8') as file:
    json.dump(qs, file, indent=4, ensure_ascii=False)
