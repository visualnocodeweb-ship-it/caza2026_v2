with open('c:/Users/emanuel/Desktop/Codigos/caza_2026_v2/caza_2026_v2_backend/main_api.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(510, 522):
        print(f"{i+1}: {repr(lines[i])}")
