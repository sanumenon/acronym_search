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
BATCH_SIZE = 500 # Smaller batch size because we are doing multiple calls per row

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
    variations.append(acr) # MTYP
    variations.append(".".join(list(acr)) + ".") # M.T.Y.P.
    variations.append(f"{words[0].capitalize()} {''.join([w[0].upper() for w in words[1:]])}") # Manitoba TYP
    variations.append(f"{words[0][0].upper()} {' '.join(words[1:])}") # M Theatre for Young People
    variations.append(f"{' '.join(words[:-1])} {words[-1][0].upper()}") # Manitoba Theatre for Young P
    return list(dict.fromkeys(variations)) # Remove duplicates

def fetch_single_call(url, term, expected_name):
    payload = {"text": term, "filter": [{"field": "class_name", "value": ["Beneficiary"]}]}
    try:
        response = session.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            items = response.json().get('data', [])
            names = [item.get('attributes', {}).get('name', 'Unknown') for item in items[:5]]
            
            # Find Rank
            rank = 999
            for i, name in enumerate(names):
                if str(expected_name).lower().strip() in name.lower():
                    rank = i + 1
                    break
            return {"term": term, "rank": rank, "results": "|".join(names)}
    except:
        pass
    return {"term": term, "rank": 999, "results": "FAILURE"}

def process_row(index, row, name_col, acr_col):
    full_name = str(row.get(name_col, ""))
    orig_acr = str(row.get(acr_col, ""))
    
    # Generate terms
    terms = generate_complex_acronyms(full_name)
    if orig_acr and orig_acr.lower() != 'null' and orig_acr not in terms:
        terms.insert(0, orig_acr)

    # Search Baseline (Old API) - Only search original acronym
    old_res = fetch_single_call(URL_EXISTING, orig_acr if orig_acr else terms[0], full_name)
    
    # Search New API - TRY ALL PERMUTATIONS
    all_attempts = []
    for t in terms:
        attempt = fetch_single_call(URL_NEW_V1, t, full_name)
        all_attempts.append(attempt)
    
    # Find the BEST attempt
    best_attempt = min(all_attempts, key=lambda x: x['rank'])
    
    # Format detailed log for developers
    detailed_log = json.dumps(all_attempts)
    
    return (index, 
            " | ".join(terms), 
            old_res['results'], 
            best_attempt['results'], 
            best_attempt['term'], 
            detailed_log)

def run_extraction(input_file, output_file):
    df = pd.read_csv(input_file) if input_file.endswith('.csv') else pd.read_excel(input_file)
    df.columns = df.columns.str.strip().str.lower()
    
    name_col = next((c for c in df.columns if 'name' in c), df.columns[1])
    acr_col = next((c for c in df.columns if 'acronym' in c), df.columns[2])

    if os.path.exists(output_file): os.remove(output_file)
    
    total = len(df)
    with tqdm(total=total, desc="Deep Permutation Search") as pbar:
        for i in range(0, total, BATCH_SIZE):
            batch_df = df.iloc[i : i + BATCH_SIZE].copy()
            batch_res = {}
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {executor.submit(process_row, idx, row, name_col, acr_col): idx for idx, row in batch_df.iterrows()}
                for f in as_completed(futures):
                    idx, terms, r_old, r_new, winner, log = f.result()
                    batch_res[idx] = [terms, r_old, r_new, winner, log]
                    pbar.update(1)

            batch_df['all_possible_acronyms'] = [batch_res[idx][0] for idx in batch_df.index]
            batch_df['users_api_acronym'] = [batch_res[idx][1] for idx in batch_df.index]
            batch_df['recommended_api_acronym'] = [batch_res[idx][2] for idx in batch_df.index]
            batch_df['winning_acronym'] = [batch_res[idx][3] for idx in batch_df.index]
            batch_df['permutation_audit_log'] = [batch_res[idx][4] for idx in batch_df.index]

            batch_df.to_csv(output_file, mode='a', header=not os.path.exists(output_file), index=False)
