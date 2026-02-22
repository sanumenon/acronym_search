import pandas as pd
import requests
import os
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# --- CONFIGURATION ---
BASIC_AUTH = "Basic YWRtaW46WTJoaGJtZGxiV1U9"
USER_ID = "73277"
IMPACT_ID = "324682"
MAX_WORKERS = 25 
BATCH_SIZE = 1000 

URL_EXISTING = f"https://api.stg.charitableimpact.com/search/v2/charities-groups-impactaccounts?page[size]=20&page[number]=1&impact_account_id={IMPACT_ID}&user_id={USER_ID}"
URL_NEW_V1 = f"https://api.stg.charitableimpact.com/search-v1/v2/charities-groups-impactaccounts?page[size]=20&page[number]=1&impact_account_id={IMPACT_ID}&user_id={USER_ID}"

session = requests.Session()
session.headers.update({"Authorization": BASIC_AUTH, "Content-Type": "application/json"})

def generate_complex_acronyms(name):
    """Generates MTYP, M.T.Y.P, Manitoba T for Young People, etc."""
    if pd.isna(name) or str(name).strip() == "": return ""
    
    # Clean name and split into words
    clean_name = re.sub(r'[^\w\s]', '', str(name))
    words = clean_name.split()
    if len(words) < 2: return str(name).upper()

    variations = []
    
    # A. Pure Acronym (MTYP)
    acr = "".join([w[0].upper() for w in words])
    variations.append(acr)

    # B. Dotted (M.T.Y.P.)
    variations.append(".".join(list(acr)) + ".")

    # C. Hybrid: First word full + rest initials (Manitoba TYP)
    variations.append(f"{words[0].capitalize()} {''.join([w[0].upper() for w in words[1:]])}")

    # D. Hybrid: Initials + last word full (MTY People)
    variations.append(f"{''.join([w[0].upper() for w in words[:-1]])} {words[-1].capitalize()}")

    # E. Hybrid: First Initial + rest full (M Theatre for Young People)
    variations.append(f"{words[0][0].upper()} {' '.join(words[1:])}")

    # F. Partial Shortening (Manitoba T for Young People)
    if len(words) > 2:
        mid_short = words.copy()
        mid_short[1] = words[1][0].upper()
        variations.append(" ".join(mid_short))

    return "|".join(variations)

def fetch_search_results(url, query):
    if not query or str(query).strip().upper() in ["", "NAN", "N/A"]: return "N/A"
    # For testing, we use the first (most standard) generated acronym
    search_term = str(query).split('|')[0]
    
    payload = {"text": search_term, "filter": [{"field": "class_name", "value": ["Beneficiary"]}]}
    try:
        response = session.post(url, json=payload, timeout=12)
        if response.status_code == 200:
            items = response.json().get('data', [])
            names = [item.get('attributes', {}).get('name', 'Unknown') for item in items[:5]]
            return "|".join(names) if names else "NO_RESULTS"
        return f"ERROR_{response.status_code}"
    except:
        return "CONNECTION_FAILURE"

def process_row(index, row, name_col, acr_col, alt_col):
    full_name = str(row.get(name_col, ""))
    orig_acr = str(row.get(acr_col, ""))
    
    # Generate all variations
    gen_acr_str = generate_complex_acronyms(full_name)
    
    # Logic: If original acronym exists, use it. Otherwise, use generated.
    search_term = orig_acr if (orig_acr and orig_acr.lower() != 'null') else gen_acr_str.split('|')[0]
    
    return (index, gen_acr_str,
            fetch_search_results(URL_EXISTING, search_term),
            fetch_search_results(URL_NEW_V1, search_term),
            fetch_search_results(URL_EXISTING, row.get(alt_col, "")),
            fetch_search_results(URL_NEW_V1, row.get(alt_col, "")))

def run_extraction(input_file, output_file):
    df = pd.read_csv(input_file) if input_file.endswith('.csv') else pd.read_excel(input_file)
    df.columns = df.columns.str.strip().str.lower()
    
    name_col = next((c for c in df.columns if 'name' in c), df.columns[1])
    acr_col = next((c for c in df.columns if 'acronym' in c), df.columns[2])
    alt_col = next((c for c in df.columns if 'alternat' in c), 'alternatives')

    if os.path.exists(output_file): os.remove(output_file)
    
    total = len(df)
    with tqdm(total=total, desc="Extracting & Generating") as pbar:
        for i in range(0, total, BATCH_SIZE):
            batch_df = df.iloc[i : i + BATCH_SIZE].copy()
            batch_res = {}
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {executor.submit(process_row, idx, row, name_col, acr_col, alt_col): idx for idx, row in batch_df.iterrows()}
                for f in as_completed(futures):
                    idx, g_acr, r_ao, r_an, r_lo, r_ln = f.result()
                    batch_res[idx] = [g_acr, r_ao, r_an, r_lo, r_ln]
                    pbar.update(1)

            batch_df['generated_acronyms'] = [batch_res[idx][0] for idx in batch_df.index]
            batch_df['users_api_acronym'] = [batch_res[idx][1] for idx in batch_df.index]
            batch_df['recommended_api_acronym'] = [batch_res[idx][2] for idx in batch_df.index]
            batch_df['users_api_alternative'] = [batch_res[idx][3] for idx in batch_df.index]
            batch_df['recommended_api_alternative'] = [batch_res[idx][4] for idx in batch_df.index]

            batch_df.to_csv(output_file, mode='a', header=not os.path.exists(output_file), index=False)