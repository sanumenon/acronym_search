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

# Charity Search Accuracy Tool (v1 & v2 Comparison)

## The Business Case: "Reducing Friction for Donors"

Donors often search for charities using shorthand names, acronyms, or partial titles (e.g., searching for **"MTYP"** instead of **"Manitoba's Theatre for Young People Inc."**). If our search engine doesn't recognize these variations, we lose potential donations.

This tool was built to validate and prove the impact of our new **Search-v1 API**. By using AI-generated acronyms and "hybrid" name combinations, we are moving the needle from a **30% success rate** to nearly **91%**, ensuring that when a donor wants to give, they find their charity instantly.

---

## What do these files do?

### `search_runner.py` (The Engine)

This is the workhorse of the project.

* **Hybrid Acronym Generation:** It takes the official name of a charity and logically creates permutations. It generates full acronyms (**MTYP**), dotted versions (**M.T.Y.P.**), and hybrid versions (**Manitoba T for Young People**).
* **Parallel API Execution:** To handle large datasets (like 200,000+ records), it uses 25 parallel threads to call the Old and New APIs simultaneously.
* **Incremental Saving:** It processes data in batches of 1,000 and saves as it goes. If the power cuts out or the internet drops, you won’t lose your progress.
* **Progress Tracking:** Includes a real-time progress bar (tqdm) showing speed and ETA.

### `generate_report.py` (The Brain)

This script turns raw data into a narrative that leadership can understand.

* **Rank Logic:** It compares the search results against the "Official Name" to see if the charity appeared in the Top 3 results.
* **Executive Summary:** Automatically generates a high-level dashboard for Senior Leadership (SLT) showing metrics like "Unlocked Charities" and "Discovery Rate."
* **Developer Debug Log:** Flags specific issues like **Regressions** (where the old search performed better than the new) or **Tuning** (where a match was found but ranked too low).

---

## How to Run It

### 1. Setup

Ensure you have Python installed and the required libraries:

```bash
pip install -r requirements.txt

```

### 2. Prepare your Data

Place your source file (e.g., `Acronyms_data - Sheet1.csv`) in the same folder. Ensure it has a column for the charity name and business number.

### 3. Run the Report

You only need to run the report script. It will automatically trigger the search runner if it doesn't find a results file:

```bash
python generate_report.py

```

---

## Understanding the Output

The process will generate **`Final_Charity_Impact_Report.xlsx`**, which contains:

1. **Executive Summary Tab:** For management. Shows the % improvement and how many "invisible" charities we have now made searchable.
2. **Dev Debug Tab:** For engineers. Shows every failed search, the generated acronyms used, and a specific "Diagnostic" (Check, Tuning, or Regression) to guide the next technical sprint.

---
**Target Goal:** 100% Acronym Discovery Rate.

-----------------------------------------
Code updated to perfrom permutaion and combination serach

Key Highlights of this "Deep" Version:
Winner Takes All: The Executive Summary reports the Best Possible Result we can give a donor if we use the right acronym.

Permutation Audit Log: In the Dev_Debug sheet, there is a new column that lists every single acronym tried and whether it was a success (✅) or a failure (❌).

Winning Acronym Column: Specifically identifies which acronym variation actually "won" the search, allowing developers to see which patterns (like Dotted vs. Hybrid) are most effective.

Automatic Detection: If a charity was invisible in the old system but was found by any of our new permutations, it is counted as "Unlocked."
