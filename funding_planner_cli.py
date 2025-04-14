# funding_planner_cli.py
import yaml
import os
import pandas as pd
from collections import defaultdict
from datetime import datetime
from rich import print
from rich.table import Table
import argparse

def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m")

def load_yaml(file_path):
    if not os.path.exists(file_path):
        print(f"[bold red]File not found:[/bold red] {file_path}")
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        if not content.strip():
            print(f"[bold red]File is empty or contains only whitespace:[/bold red] {file_path}")
            return {}
        return yaml.safe_load(content)

def convert_excel_to_yaml(excel_path):
    personnel_plans = {}
    xls = pd.ExcelFile(excel_path)
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name, header=0)  # Take first row as header (default)
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
    yaml_path = os.path.splitext(excel_path)[0] + ".yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(personnel_plans, f, sort_keys=False)
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

def generate_report(source_usage, funding_sources):
    table = Table(title="Funding Source Usage Report")
    table.add_column("Source")
    table.add_column("Used")
    table.add_column("Budget")
    table.add_column("Remaining")

    for source, usage in source_usage.items():
        budget = funding_sources[source]['budget']
        table.add_row(source, f"${usage:,.2f}", f"${budget:,.2f}", f"${budget-usage:,.2f}")

    print(table)

def main():
    parser = argparse.ArgumentParser(description="Funding Planning Validator")
    parser.add_argument("--sources", required=True, help="Path to funding_sources.yaml")
    parser.add_argument("--plans", required=True, help="Path to personnel_plans.yaml or .xlsx")
    args = parser.parse_args()

    sources = load_yaml(args.sources)
    plans = None

    if args.plans.endswith(".xlsx"):
        plans = convert_excel_to_yaml(args.plans)
    else:
        plans = load_yaml(args.plans)

    if not sources or not plans:
        print("[bold red]Error loading input files.[/bold red]")
        return

    usage, errs = validate(sources, plans)

    if errs:
        print("[bold red]Validation Errors:[/bold red]")
        for e in errs:
            print(f" - {e}")
    else:
        print("[bold green]All checks passed.[/bold green]")

    generate_report(usage, sources)

if __name__ == "__main__":
    main()
