import pandas as pd
import requests
import os
import time
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# --- CONFIGURATION ---
BASIC_AUTH = "Basic YWRtaW46WTJoaGJtZGxiV1U9"
USER_ID = "73277"
IMPACT_ID = "324682"
MAX_WORKERS = 20 

URL_EXISTING = f"https://api.stg.charitableimpact.com/search/v2/charities-groups-impactaccounts?page[size]=20&page[number]=1&impact_account_id={IMPACT_ID}&user_id={USER_ID}"
URL_NEW_V1 = f"https://api.stg.charitableimpact.com/search-v1/v2/charities-groups-impactaccounts?page[size]=20&page[number]=1&impact_account_id={IMPACT_ID}&user_id={USER_ID}"

session = requests.Session()
session.headers.update({"Authorization": BASIC_AUTH, "Content-Type": "application/json"})

def generate_complex_acronyms(name):
    if pd.isna(name) or str(name).strip() == "": return []
    clean_name = re.sub(r'[^\w\s]', '', str(name))
    words = clean_name.split()
    if len(words) < 2: return [str(name).upper()]
    variations = []
    acr = "".join([w[0].upper() for w in words])
    variations.append(acr)
    variations.append(".".join(list(acr)) + ".")
    variations.append(f"{words[0].capitalize()} {''.join([w[0].upper() for w in words[1:]])}")
    variations.append(f"{words[0][0].upper()} {' '.join(words[1:])}")
    variations.append(f"{' '.join(words[:-1])} {words[-1][0].upper()}")
    return list(dict.fromkeys(variations))

def fetch_single_call(url, term, expected_name):
    payload = {"text": term, "filter": [{"field": "class_name", "value": ["Beneficiary"]}]}
    try:
        response = session.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            items = response.json().get('data', [])
            names = [item.get('attributes', {}).get('name', 'Unknown') for item in items[:5]]
            rank = 999
            for i, name in enumerate(names):
                if str(expected_name).lower().strip() in name.lower():
                    rank = i + 1; break
            return {"term": term, "rank": rank}
    except: pass
    return {"term": term, "rank": 999}

def process_row(index, row, name_col, acr_col):
    full_name = str(row.get(name_col, ""))
    given_acr = str(row.get(acr_col, ""))
    terms = generate_complex_acronyms(full_name)
    if given_acr and given_acr.lower() != 'null' and given_acr not in terms:
        terms.insert(0, given_acr)
    
    audit_data = []
    for t in terms:
        old_res = fetch_single_call(URL_EXISTING, t, full_name)
        new_res = fetch_single_call(URL_NEW_V1, t, full_name)
        audit_data.append({"term": t, "rank_old": old_res['rank'], "rank_new": new_res['rank'], "is_given": (t == given_acr)})
    
    return (index, json.dumps(audit_data))

def run_extraction(input_file, output_file):
    df = pd.read_csv(input_file) if input_file.endswith('.csv') else pd.read_excel(input_file)
    df.columns = df.columns.str.strip().str.lower()
    name_col = next((c for c in df.columns if 'name' in c), df.columns[1])
    acr_col = next((c for c in df.columns if 'acronym' in c), df.columns[2])
    if os.path.exists(output_file): os.remove(output_file)
    results = {}
    with tqdm(total=len(df), desc="Deep Audit Search") as pbar:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(process_row, idx, row, name_col, acr_col): idx for idx, row in df.iterrows()}
            for f in as_completed(futures):
                idx, audit_json = f.result(); results[idx] = audit_json; pbar.update(1)
    df['audit_json'] = [results[i] for i in df.index]
    df.to_csv(output_file, index=False)
