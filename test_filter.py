import pandas as pd
import math

# Simular datos
data = [
    {"nombre": "Estancia Pilolil", "id": "1"},
    {"nombre": "Nahuel Mapi", "id": "2"},
    {"nombre": "San Pedro", "id": "3"}
]
df = pd.DataFrame(data)

search = "Pilolil"
if search:
    search_str = search.lower()
    # ESTO ES LO QUE TENGO EN EL CODIGO
    mask = df.apply(lambda row: row.astype(str).str.contains(search_str, case=False).any(), axis=1)
    df_filtered = df[mask]
    print(f"Filtered DF length: {len(df_filtered)}")
    print(df_filtered)
else:
    print("No search")
