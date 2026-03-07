"""
Script de diagnóstico: revisa qué hay en la tabla reses_details de la BD de producción.
Ejecutar con: python check_reses_db.py
"""
import os, sys
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'caza_2026_v2_backend', '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Pegar aquí la DATABASE_URL de Render si no está en .env
    DATABASE_URL = input("Pegar la DATABASE_URL de Render: ").strip()

import psycopg2

url = DATABASE_URL.replace("postgres://", "postgresql://")
conn = psycopg2.connect(url)
cur = conn.cursor()

print("=== TABLA reses_details ===")
cur.execute("SELECT res_id, amount, is_paid, last_updated FROM reses_details ORDER BY last_updated DESC LIMIT 20;")
rows = cur.fetchall()
if rows:
    print(f"{'res_id':<35} {'amount':>10} {'is_paid':>8} {'last_updated'}")
    print("-" * 80)
    for r in rows:
        print(f"{str(r[0]):<35} {str(r[1]):>10} {str(r[2]):>8} {r[3]}")
else:
    print("  (tabla vacía)")

print()
print("=== Filas con is_paid = True ===")
cur.execute("SELECT res_id, amount FROM reses_details WHERE is_paid IS TRUE;")
paid = cur.fetchall()
if paid:
    for r in paid:
        print(f"  res_id={r[0]}  amount={r[1]}")
else:
    print("  Ninguna fila tiene is_paid=True")

print()
print("=== Columnas de reses_details ===")
cur.execute("""
    SELECT column_name, data_type, column_default, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'reses_details'
""")
cols = cur.fetchall()
for c in cols:
    print(f"  {c[0]}: {c[1]} | default={c[2]} | nullable={c[3]}")

cur.close()
conn.close()
