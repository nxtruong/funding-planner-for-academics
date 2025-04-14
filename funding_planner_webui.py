# funding_planner_webui.py
import streamlit as st
import yaml
from datetime import datetime
from collections import defaultdict
import pandas as pd
import os

def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m")

def convert_excel_to_yaml(uploaded_excel):
    personnel_plans = {}
    xls = pd.ExcelFile(uploaded_excel)
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name, header=0)
        entries = []
        for _, row in df.iterrows():
            start = row.iloc[0]
            end = row.iloc[1]
            salary = row.iloc[2]
            allocations = {}
            for i in range(3, len(row), 2):
                source = row.iloc[i]
                amount = row.iloc[i+1] if i+1 < len(row) else 0
                if pd.notna(source) and pd.notna(amount):
                    allocations[str(source)] = float(amount)
            entries.append({
                "start": start,
                "end": end,
                "salary": salary,
                "allocations": allocations
            })
        personnel_plans[sheet_name] = entries
    return personnel_plans

def validate(funding_sources, personnel_plans):
    source_usage = defaultdict(float)
    errors = []

    for person, periods in personnel_plans.items():
        for period in periods:
            start, end = parse_date(period['start']), parse_date(period['end'])
            salary = period['salary']
            allocations = period['allocations']
            total_allocated = sum(allocations.values())

            if abs(total_allocated - salary) > 1:
                errors.append(f"[{person}] Salary mismatch in {period['start']}–{period['end']}: Expected {salary}, got {total_allocated}")

            for source, amount in allocations.items():
                fs = funding_sources[source]
                fs_start, fs_end = parse_date(fs['start']), parse_date(fs['end'])

                if start < fs_start or end > fs_end:
                    errors.append(f"[{person}] Allocation from {source} is out of bounds: {period['start']}–{period['end']}")

                source_usage[source] += amount

    for source, used in source_usage.items():
        budget = funding_sources[source]['budget']
        if used > budget:
            errors.append(f"[{source}] Over budget: used {used}, budget {budget}")

    return source_usage, errors

def display_report(source_usage, funding_sources):
    data = []
    for source, used in source_usage.items():
        budget = funding_sources[source]['budget']
        remaining = budget - used
        data.append({
            "Source": source,
            "Used": float(used),
            "Budget": float(budget),
            "Remaining": float(remaining)
        })
    df = pd.DataFrame(data)
    for col in ["Used", "Budget", "Remaining"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    st.dataframe(df.style.format({"Used": "${:,.2f}", "Budget": "${:,.2f}", "Remaining": "${:,.2f}"}))

def main():
    st.title("Funding Allocation Planner")

    sources_file = st.file_uploader("Upload funding_sources.yaml", type="yaml")
    plans_file = st.file_uploader("Upload personnel_plans (YAML or Excel)", type=["yaml", "xlsx"])

    if sources_file and plans_file:
        funding_sources = yaml.safe_load(sources_file)

        if plans_file.name.endswith(".xlsx"):
            personnel_plans = convert_excel_to_yaml(plans_file)
        else:
            personnel_plans = yaml.safe_load(plans_file)

        usage, errors = validate(funding_sources, personnel_plans)

        if errors:
            st.error("Validation Errors:")
            for err in errors:
                st.markdown(f"- {err}")
        else:
            st.success("All checks passed.")

        st.subheader("Funding Usage Report")
        display_report(usage, funding_sources)

if __name__ == '__main__':
    main()
