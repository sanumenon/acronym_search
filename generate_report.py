import pandas as pd
import numpy as np
import os
from search_runner import run_extraction

def generate_master_report(input_csv):
    combined_file = 'combined_api_results.csv' 
    if not os.path.exists(combined_file):
        run_extraction(input_csv, combined_file)
    
    df = pd.read_csv(combined_file, low_memory=False)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    target_col = 'account_name' if 'account_name' in df.columns else ('name' if 'name' in df.columns else df.columns[1])

    def get_rank(expected, found_str):
        if pd.isna(found_str) or str(found_str).strip() == "": return 999
        expected_clean = str(expected).lower().strip()
        results = [n.lower().strip() for n in str(found_str).split('|')]
        for i, name in enumerate(results):
            if expected_clean in name: return i + 1
        return 999

    df['rank_old'] = df.apply(lambda r: get_rank(r[target_col], r['users_api_acronym']), axis=1)
    df['rank_new'] = df.apply(lambda r: get_rank(r[target_col], r['recommended_api_acronym']), axis=1)

    def diagnose(row):
        if row['rank_old'] <= 3 and row['rank_new'] > 3: return "REGRESSION"
        if row['rank_new'] == 999: return "CHECK: Not found"
        if row['rank_new'] > 3: return "TUNING: Low rank"
        return "PASS"

    total = len(df)
    slt_summary = pd.DataFrame({
        "Strategic Metric": [
            "Total Charities Tested", "Search Success (Top 3)", 
            "Previously Invisible Charities", "Acronym Discovery Rate", "Average Result Position"
        ],
        "Baseline (Existing)": [
            total, f"{(len(df[df['rank_old'] <= 3])/total)*100:.1f}%", "---", 
            len(df[df['rank_old'] <= 3]), f"{df[df['rank_old'] != 999]['rank_old'].mean():.2f}"
        ],
        "New System (Search-v1)": [
            total, f"{(len(df[df['rank_new'] <= 3])/total)*100:.1f}%", 
            f"Unlocked {len(df[(df['rank_old'] > 3) & (df['rank_new'] <= 3)])}", 
            len(df[df['rank_new'] <= 3]), f"{df[df['rank_new'] != 999]['rank_new'].mean():.2f}"
        ]
    })

    dev_log = df[df['rank_new'] > 3].copy()
    dev_log['Diagnostic'] = dev_log.apply(diagnose, axis=1)
    
    output_name = "Final_Charity_Impact_Report.xlsx"
    with pd.ExcelWriter(output_name, engine='xlsxwriter') as writer:
        slt_summary.to_excel(writer, sheet_name='Executive_Summary', index=False)
        # Added generated_acronyms library here
        dev_cols = ['bn', target_col, 'acronyms', 'generated_acronyms', 'rank_old', 'rank_new', 'Diagnostic']
        dev_log[dev_cols].to_excel(writer, sheet_name='Dev_Debug', index=False)

    print(f"🎉 Report generated with Hybrid Acronyms: {output_name}")

if __name__ == "__main__":
    generate_master_report('Acronyms_data - Sheet1.csv')