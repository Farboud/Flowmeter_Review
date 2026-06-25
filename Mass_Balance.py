"""
Mass Balance Timeseries Processor
=================================

This script performs automated mass balance calculations for a network of flow meters.

How it works:
-------------
1. **Reads all .tsf files in the script's directory** that match any ID in the mass balance table below (including inflows and outflows).
2. **For each ID (master node):**
    - Sums all "FMs Upstream" flow series (inflows).
    - Sums all "OFs Upstream" flow series (outflows).
    - At each timestep, computes: `Inflow-Outflow = sum(FMs Upstream) - sum(OFs Upstream)`.
    - Only uses timestamps present in the original data for that ID.
    - Optionally replaces negative flows with zero (default: ON, configurable in `main()`).
    - Plots **only the original timeseries and the calculated mass balance timeseries**.
3. **Writes a TSF file** for each ID, named:
       `ID_startYYYYMMDD_endYYYYMMDD_Mass_Balance.tsf`
    - The TSF file includes:
        - Date/Time column
        - Original flow for the ID
        - All inflow timeseries (one column per inflow ID)
        - All outflow timeseries (one column per outflow ID)
        - Inflow (Sum)
        - Outflow (Sum)
        - Calculated flow (named "Inflow-Outflow")
    - The second header row (column names) is always "Flow" for all columns except Date/Time.
4. Units are assumed to be mgd (million gallons per day).
5. Cross-platform compatibility for date formatting in TSF files (Windows/Linux/Mac).

How to use:
-----------
- Place this script in the same directory as your .tsf files.
- Run the script with Python 3.
- Adjust the mass balance table as needed.
- Set `replace_negative_flows=True` or `False` in the main function as desired.

Date: 2026
"""

import pathlib
import pandas as pd
import matplotlib.pyplot as plt
import sys

BASE_DIR = pathlib.Path(__file__).parent

# --------- Mass Balance Table ----------
id_table = {
    "BCOHFM26-04": {
        "FMs": ["BCOHFM26-15"],
        "OFs": ["BCOHOF26-17"]
    },
    "BCOHFM26-07": {
        "FMs": ["BCOHFM26-01"],
        "OFs": []
    },
    "BCOHFM26-08": {
        "FMs": ["BCOHFM26-03"],
        "OFs": []
    },
    "BCOHFM26-12": {
        "FMs": ["BCOHFM26-09", "BCOHFM26-10", "BCOHFM26-11", "BCOHFM26-14"],
        "OFs": ["BCOHOF26-03", "BCOHOF26-09", "BCOHOF26-13"]
    },
    "BCOHFM26-13": {
        "FMs": ["BCOHFM26-12", "BCOHFM26-04", "BCOHFM26-05", "BCOHFM26-02"],
        "OFs": ["BCOHOF26-19", "BCOHOF26-22", "BCOHOF26-23"]
    },
    "BCOHFM26-15": {
        "FMs": ["BCOHFM26-08"],
        "OFs": []
    },
    "WWTP": {
        "FMs": ["BCOHFM26-06", "BCOHFM26-13", "BCOHFM26-07"],
        "OFs": ["BCOHOF26-26", "BCOHOF26-25", "BCOHOF26-24"]
    }
}

def split_row_flexible(line):
    parts = line.rstrip("\n").split("\t")
    if len(parts) <= 1:
        parts = line.split()
    return [p.strip() for p in parts]

def get_all_ids(id_table):
    ids = set()
    for main_id, v in id_table.items():
        ids.add(main_id)
        for x in v["FMs"]:
            ids.add(x)
        for x in v["OFs"]:
            ids.add(x)
    return ids

def read_selected_flows(relevant_ids):
    """Return a dict: {ID: pandas.Series indexed by timestamp} for relevant IDs only"""
    flows_by_id = {}
    for f in sorted(BASE_DIR.glob("*.tsf")):
        with f.open("r", encoding="utf-8", errors="replace") as fh:
            id_row = split_row_flexible(fh.readline() or "")
            header_row = split_row_flexible(fh.readline() or "")
            _units_row = fh.readline()
            # Find Flow column index
            flow_idx = None
            for i, h in enumerate(header_row):
                if h.strip().lower() == "flow":
                    flow_idx = i
                    break
            if flow_idx is None:
                continue
            this_id = id_row[flow_idx] if flow_idx < len(id_row) and id_row[flow_idx] else header_row[flow_idx]
            if this_id not in relevant_ids:
                continue  # Skip files not matching needed IDs
            # Read data
            records = []
            for raw in fh:
                if not raw.strip():
                    continue
                parts = split_row_flexible(raw)
                if flow_idx >= len(parts):
                    continue
                raw_ts = parts[0]
                raw_flow = parts[flow_idx]
                try:
                    ts = pd.to_datetime(raw_ts)
                    flow_val = float(raw_flow)
                    records.append((ts, flow_val))
                except Exception:
                    continue
            if records:
                s = pd.Series(
                    [f for (t, f) in records],
                    index=pd.DatetimeIndex([t for (t, f) in records])
                ).sort_index()
                flows_by_id[this_id] = s
    return flows_by_id

def align_all_ids(flows_by_id):
    """Return DataFrame: columns=all IDs, index=all timestamps (union), values=flows (NaN where missing)."""
    return pd.DataFrame(flows_by_id)

def plot_original_and_calc(id_: str, orig: pd.Series, calc: pd.Series):
    plt.figure(figsize=(12,5))
    orig.plot(label=f'Original {id_}', alpha=0.7)
    calc.plot(label='Inflow-Outflow', linestyle='--', alpha=0.7)
    plt.title(f"ID: {id_} - Original and Mass Balance (Inflow-Outflow)")
    plt.ylabel("Flow (mgd)")
    plt.xlabel("Timestamp")
    plt.legend()
    plt.tight_layout()
    plt.show()

def format_datetime(dt):
    if sys.platform.startswith("win"):
        return dt.strftime("%#m/%#d/%Y %H:%M")
    else:
        return dt.strftime("%-m/%-d/%Y %H:%M")

def write_tsf(id_, orig, inflow, outflow, calc, inflow_ids, outflow_ids, df):
    # Compose DataFrame
    data = {
        'Date/Time': orig.index,
        id_: orig.values
    }
    # Add inflow columns (individual timeseries)
    for inflow_id in inflow_ids:
        s = df[inflow_id].loc[orig.index] if inflow_id in df.columns else pd.Series(index=orig.index, dtype='float64')
        data[inflow_id] = s.values
    # Add outflow columns (individual timeseries)
    for outflow_id in outflow_ids:
        s = df[outflow_id].loc[orig.index] if outflow_id in df.columns else pd.Series(index=orig.index, dtype='float64')
        data[outflow_id] = s.values
    # Add inflow sum, outflow sum, and calculated flow (renamed to Inflow-Outflow)
    data['Inflow (Sum)'] = inflow.values
    data['Outflow (Sum)'] = outflow.values
    data['Inflow-Outflow'] = calc.values

    df_out = pd.DataFrame(data)
    if df_out.empty:
        print(f"No data to write for {id_}")
        return

    start_date = df_out['Date/Time'].min().strftime("%Y%m%d")
    end_date = df_out['Date/Time'].max().strftime("%Y%m%d")
    out_path = BASE_DIR / f"{id_}_start{start_date}_end{end_date}_Mass_Balance.tsf"
    with out_path.open("w", encoding="utf-8") as f:
        # First header row: IDs (for each column except Date/Time)
        header_ids = [id_] + inflow_ids + outflow_ids + ['Inflow (Sum)', 'Outflow (Sum)', 'Inflow-Outflow']
        f.write("IDs:\t" + "\t".join(header_ids) + "\n")
        # Second header row: all "Flow" except first column
        header_names = ["Date/Time"] + ["Flow"] * (len(df_out.columns) - 1)
        f.write("\t".join(header_names) + "\n")
        # Third header row: units
        units = ["M/d/yyyy H:mm"] + ["mgd"] * (len(df_out.columns) - 1)
        f.write("\t".join(units) + "\n")
        # Data rows
        for _, row in df_out.iterrows():
            dt_str = format_datetime(row['Date/Time'])
            f.write(dt_str)
            for col in df_out.columns[1:]:
                val = row[col]
                f.write(f"\t{val:.6f}" if pd.notna(val) else "\t")
            f.write("\n")

def main(replace_negative_flows=True):
    relevant_ids = get_all_ids(id_table)
    flows_by_id = read_selected_flows(relevant_ids)
    if not flows_by_id:
        print("No flow data found for relevant IDs!")
        return
    df = align_all_ids(flows_by_id)
    for id_, v in id_table.items():
        inflow_ids = v["FMs"]
        outflow_ids = v["OFs"]
        if id_ not in df.columns:
            print(f"Skipping {id_}: no data found.")
            continue
        orig = df[id_].dropna()
        fm_sum = df[inflow_ids].sum(axis=1, skipna=True) if inflow_ids else pd.Series(0, index=df.index)
        of_sum = df[outflow_ids].sum(axis=1, skipna=True) if outflow_ids else pd.Series(0, index=df.index)
        inflow = fm_sum.loc[orig.index]
        outflow = of_sum.loc[orig.index]
        calc = inflow - outflow

        if replace_negative_flows:
            orig = orig.clip(lower=0)
            inflow = inflow.clip(lower=0)
            outflow = outflow.clip(lower=0)
            calc = calc.clip(lower=0)

        plot_original_and_calc(id_, orig, calc)
        write_tsf(id_, orig, inflow, outflow, calc, inflow_ids, outflow_ids, df)

if __name__ == "__main__":
    main(replace_negative_flows=True) #True: Replaces negative values with zero, False: Keeps negative values unchanged