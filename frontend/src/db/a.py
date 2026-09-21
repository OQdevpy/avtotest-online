import json

# Faylni o'qib olish
with open('/home/avtotest/Desktop/new/src/db/new_question.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Ma'lumotlarni qayta ishlash (bo'laklarga bo'lingan holda)
len_n = (len(data) // 20) + 1
new_data = []

for i in range(len_n):
    # Bo'laklarni olish
    new_data_chunk = data[i*20:20*(i+1)]

    for k in new_data_chunk:
        k['var_id']=int(i)
    
    new_data.append({
        "var_id": int(i),
        "data": new_data_chunk  # To'g'ri bo'lakni qo'shish
    })

# Ma'lumotlarni o'zgarishsiz Unicode shaklida saqlash
with open('/home/avtotest/Desktop/new/src/db/question.json', 'w', encoding='utf-8') as file:
    json.dump(new_data, file, indent=4, ensure_ascii=False)

print("Ma'lumotlar Unicode formatda saqlandi.")
