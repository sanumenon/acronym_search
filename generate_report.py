import pandas as pd
import numpy as np
import os
import json
from search_runner import run_extraction

def generate_master_report(input_csv):
    combined_file = 'combined_api_results.csv' 
    if not os.path.exists(combined_file):
        run_extraction(input_csv, combined_file)
    
    df = pd.read_csv(combined_file, low_memory=False)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    target_col = 'account_name' if 'account_name' in df.columns else ('name' if 'name' in df.columns else df.columns[1])

    def get_rank(expected, found_str):
        if pd.isna(found_str) or str(found_str).strip() == "" or found_str == "FAILURE": return 999
        expected_clean = str(expected).lower().strip()
        results = [n.lower().strip() for n in str(found_str).split('|')]
        for i, name in enumerate(results):
            if expected_clean in name: return i + 1
        return 999

    df['rank_old'] = df.apply(lambda r: get_rank(r[target_col], r['users_api_acronym']), axis=1)
    df['rank_new'] = df.apply(lambda r: get_rank(r[target_col], r['recommended_api_acronym']), axis=1)

    # --- SLT SUMMARY (Best Result Logic) ---
    total = len(df)
    slt_summary = pd.DataFrame({
        "Strategic Metric": ["Total Tested", "Search Success (Top 3)", "Previously Invisible", "Avg Position"],
        "Baseline (Existing)": [total, f"{(len(df[df['rank_old'] <= 3])/total)*100:.1f}%", "---", f"{df[df['rank_old'] != 999]['rank_old'].mean():.2f}"],
        "New System (Best Permutation)": [total, f"{(len(df[df['rank_new'] <= 3])/total)*100:.1f}%", len(df[(df['rank_old'] > 3) & (df['rank_new'] <= 3)]), f"{df[df['rank_new'] != 999]['rank_new'].mean():.2f}"]
    })

    # --- DEV DEBUG (Detailed Log Logic) ---
    dev_log = df.copy()
    
    def format_audit(log_str):
        try:
            data = json.loads(log_str)
            lines = []
            for entry in data:
                status = "✅" if entry['rank'] <= 3 else "❌"
                lines.append(f"{status} {entry['term']} (Rank: {entry['rank']})")
            return "\n".join(lines)
        except: return log_str

    dev_log['Full_Permutation_Audit'] = dev_log['permutation_audit_log'].apply(format_audit)
    
    output_name = "Final_Charity_Deep_Impact_Report.xlsx"
    with pd.ExcelWriter(output_name, engine='xlsxwriter') as writer:
        slt_summary.to_excel(writer, sheet_name='Executive_Summary', index=False)
        
        # Dev sheet with detailed columns
        dev_cols = ['bn', target_col, 'winning_acronym', 'rank_new', 'Full_Permutation_Audit', 'all_possible_acronyms']
        dev_log[dev_cols].to_excel(writer, sheet_name='Dev_Debug', index=False)

    print(f"🎉 Deep Report Complete: {output_name}")

if __name__ == "__main__":
    generate_master_report('Acronyms_data - Sheet1.csv')
