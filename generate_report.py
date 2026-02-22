import pandas as pd
import json
import os
from search_runner import run_extraction

def generate_master_report(input_csv):
    combined_file = 'combined_api_results.csv' 
    if not os.path.exists(combined_file):
        run_extraction(input_csv, combined_file)
    
    df = pd.read_csv(combined_file)
    df.columns = df.columns.str.strip().str.lower()
    target_col = 'account_name' if 'account_name' in df.columns else df.columns[1]

    audit_rows = []
    summary_data = []

    for _, row in df.iterrows():
        audit_list = json.loads(row['audit_json'])
        best_old = min([a['rank_old'] for a in audit_list])
        best_new = min([a['rank_new'] for a in audit_list])
        summary_data.append({'old': best_old, 'new': best_new})

        for item in audit_list:
            status = "PASS"
            action = "No Action"
            if item['rank_new'] == 999:
                status = "FAIL"
                action = "🔍 Check Indexing"
            elif item['rank_old'] <= 3 and item['rank_new'] > 3:
                status = "REGRESSION"
                action = "🔥 Priority Fix: Regression"
            elif item['rank_new'] > 1:
                status = "SUB-OPTIMAL"
                action = "⚖️ Boost Relevancy"

            audit_rows.append({
                'BN': row['bn'],
                'Charity Name': row[target_col],
                'Given Acronym': row['acronyms'],
                'Tested Term': item['term'],
                'Rank Old': item['rank_old'],
                'Rank New': item['rank_new'],
                'Status': status,
                'Diagnostic Plan': action,
                'Comment': f"Comparison for {item['term']}"
            })

    # --- SLT SUMMARY (Now with 5 Metrics) ---
    df_sum = pd.DataFrame(summary_data)
    total = len(df_sum)
    slt_summary = pd.DataFrame({
        "Strategic Metric": [
            "Total Charities Tested", 
            "Search Success (Top 3)", 
            "Previously Invisible Charities", 
            "Acronym Discovery Rate", 
            "Average Result Position"
        ],
        "Baseline (Existing Best)": [
            total, 
            f"{(len(df_sum[df_sum['old'] <= 3])/total)*100:.1f}%", 
            "---", 
            len(df_sum[df_sum['old'] <= 3]),
            f"{df_sum[df_sum['old'] != 999]['old'].mean():.2f}"
        ],
        "New System (Search-v1 Best)": [
            total, 
            f"{(len(df_sum[df_sum['new'] <= 3])/total)*100:.1f}%", 
            len(df_sum[(df_sum['old'] > 3) & (df_sum['new'] <= 3)]), 
            len(df_sum[df_sum['new'] <= 3]),
            f"{df_sum[df_sum['new'] != 999]['new'].mean():.2f}"
        ]
    })

    output_name = "Final_Technical_Audit_Report.xlsx"
    with pd.ExcelWriter(output_name, engine='xlsxwriter') as writer:
        slt_summary.to_excel(writer, sheet_name='Executive_Summary', index=False)
        pd.DataFrame(audit_rows).to_excel(writer, sheet_name='Developer_Action_Log', index=False)

    print(f"🎉 Complete Report Ready: {output_name}")

if __name__ == "__main__":
    generate_master_report('Acronyms_data - Sheet1.csv')
