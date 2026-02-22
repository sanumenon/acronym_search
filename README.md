# acronym_search
Script to search, compare , analyse and generate acronym results from existing and new api versions of API

### 1. `requirements.txt`

```text
pandas
requests
tqdm
numpy
xlsxwriter
openpyxl

```

---

### 2. `README.md`

To help your developers act on the findings quickly, here is the updated **README.md** including the **Elasticsearch Boosting** section and a comprehensive breakdown of the project requirements, file functions, and business context.

---

#  Charity Search Discovery & Relevancy Engine

## 1. Business Case: "The Discovery Gap"

Donors predominantly use shorthand—acronyms, partial names, or dotted variations—when searching for charities (e.g., **"MTYP"** or **"M.T.Y.P."** instead of **"Manitoba Theatre for Young People"**). If the search engine fails to map these shorthand terms to official legal names, donors see "No Results," leading to lost donation opportunities. This tool identifies those gaps by testing every possible naming permutation against our APIs to ensure a **100% Discovery Rate**.

---

## 2. Project Requirements

* **Input Data**: A CSV or Excel file containing charity names and known acronyms.
* **Testing Environment**: Access to Staging APIs for both the existing search and the new v1 search.
* **Accuracy Threshold**: Target success is a **Rank #1** result for all common shorthand permutations.

---

## 3. Installation & Setup

### Prerequisites

* **Python 3.12+**
* **Required Libraries**: `pandas`, `requests`, `tqdm`, `xlsxwriter`

### Steps

1. **Clone the repository** to your local environment.
2. **Install dependencies**:
```bash
pip install pandas requests tqdm xlsxwriter

```


3. **Configuration**: Update `BASIC_AUTH`, `USER_ID`, and `IMPACT_ID` in `search_runner.py` with valid staging credentials.

---

## 4. File Functional Details

### 🛠️ `search_runner.py` (Multi-Permutation Engine)

* **Permutation Generator**: Automatically creates 5+ variations of every name, including Standard, Dotted, and various Hybrid variations.
* **Multi-API Auditor**: Tests every generated term against the **Existing API** and the **New Search-v1 API** simultaneously.
* **Concurrency**: Uses `ThreadPoolExecutor` to process large datasets (thousands of requests) efficiently.

### 📊 `generate_report.py` (Diagnostic Brain)

* **Data Exploder**: Transforms JSON results into a row-wise format so every acronym permutation is visible for individual evaluation.
* **Success Metric Logic**: Specifically identifies "Unlocked" charities that failed in the old system but passed in the new one.
* **Diagnostic Engine**: Assigns technical "Action Plans" to every failure to guide engineering fixes.

---

## 5. Output (O/P) Structure

The tool generates **`Final_Technical_Audit_Report.xlsx`** with two primary layers:

### Tab 1: Executive_Summary (For Leadership)

* **Total Charities Tested**: Total count of the dataset.
* **Search Success (Top 3)**: Percentage of charities found in the top 3 results.
* **Previously Invisible Charities**: Charities discoverable *only* via the New System.
* **Acronym Discovery Rate**: Raw count of successful acronym-to-charity matches.
* **Average Result Position**: The average rank (1.0 is the goal).

### Tab 2: Developer_Action_Log (For Engineering)

* **Tested Term**: The specific permutation used for that row (e.g., `D.C.D.L.`).
* **Rank Old vs. Rank New**: Direct performance comparison for that specific term.
* **Diagnostic Plan**: Clear instructions (e.g., *" Priority Fix: Regression"* or *"⚖️ Boost Relevancy"*).
* **Comment**: Contextual explanation of the failure or success.

---

## 6. How to Interpret Elasticsearch "Boosting"

When the report suggests **"⚖️ Boost Relevancy,"** it indicates that the charity was found, but not at Rank #1. Developers should:

1. **Increase Field Weight**: Increase the `boost` value for the `acronym` or `alternative_name` fields in the Elasticsearch query.
2. **Exact Match Multiplier**: Implement a higher weight for "Exact Matches" on acronyms vs. "Partial Matches" on full names.
3. **Dot Normalization**: Ensure the analyzer treats dotted acronyms (`D.B.D.C.I.`) and plain acronyms (`DBDCI`) with equal weight.
