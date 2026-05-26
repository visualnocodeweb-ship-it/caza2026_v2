import os
import sys
import json
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Define paths
base_path = r"c:\Users\emanuel\Desktop\Codigos\caza_2026_v2\caza_2026_v2_backend"
load_dotenv(os.path.join(base_path, ".env"))

service_account_file = os.path.join(base_path, "service_account.json")

def get_data():
    if not os.path.exists(service_account_file):
        print(f"No se encuentra {service_account_file}")
        return

    creds = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )
    service = build('sheets', 'v4', credentials=creds)

    sheet_id = "1Hl99DUx5maPEHkC5JNJqq2SZLa8UgVQBJbeia5jk1VI"
    tab_name = "cabeza_1"
    guia_id = "gt1_fau69dfdc5724244"

    range_name = f"'{tab_name}'!A:ZZ"
    
    print(f"Reading {sheet_id} / {range_name}...")
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=range_name
    ).execute()
    values = result.get('values', [])

    if not values:
        print("No values found.")
        return

    headers = values[0]
    df = pd.DataFrame(values[1:], columns=headers)
    
    row = df[df['ID'].astype(str) == str(guia_id)]
    if row.empty:
        print(f"Guía {guia_id} no encontrada.")
    else:
        print(row.to_dict(orient='records')[0])

if __name__ == "__main__":
    get_data()
