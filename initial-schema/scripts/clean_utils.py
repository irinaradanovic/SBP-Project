import pandas as pd
import ast
from datetime import datetime

def parse_date(date_val, date_format='%Y-%m-%d'):
    """Pomoćna funkcija za pretvaranje stringa u datetime objekat"""
    if pd.isna(date_val) or str(date_val).strip() == '':
        return None
    try:
        # Ako je timestamp sa vremenom 
        if ' ' in str(date_val):
            return datetime.strptime(str(date_val).split('.')[0], '%Y-%m-%d %H:%M:%S')
        return datetime.strptime(str(date_val).strip(), date_format)
    except Exception:
        return None

def parse_list(list_val):
    """Pomoćna funkcija za pretvaranje string zapisa liste u pravu Python listu."""
    if pd.isna(list_val) or str(list_val).strip() == '':
        return None
    try:
        return ast.literal_eval(str(list_val))
    except (ValueError, SyntaxError):
        # Ako ast ne uspe, splitujemo po zarezu i čistimo razmake
        cleaned = str(list_val).replace('[', '').replace(']', '').replace("'", "")
        return [x.strip() for x in cleaned.split(',') if x.strip()]
