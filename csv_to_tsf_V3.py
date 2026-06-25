import pandas as pd
import os
import re
from datetime import datetime

"""
Batch CSV to PCSWMM TSF Converter (Version 3, Final Velocity Fix)
-----------------------------------------------------------------

This script automates the conversion of multiple CSV timeseries files into 
PCSWMM-compatible TSF files.

How it works:
-------------
1. Scans the script's directory for all CSV files.

2. For files whose name starts with "BCOHSC":
    - Skips the first 10 lines of the file.
    - Expects columns: Date, Time, LEVEL, TEMPERATURE.
    - Concatenates Date and Time into a single "Date/Time" column and formats it.
    - Outputs columns: Date/Time, Level, Temperature
        - Level: numeric LEVEL, rounded to 8 decimals
        - Temperature: numeric TEMPERATURE, rounded to 3 decimals
    - IDs row: "IDs:" in the first cell, then ID repeated for each data column (no ID for Date/Time)
    - Format row: M/d/yyyy	ft	F

3. For files whose name starts with "BCOHRG":
    - Dynamically finds the "Rain" column (contains "rain") and the "DateTime_ET" column (contains "et"), case-insensitive, anywhere in the header row.
    - Ignores the "DateTime_MDT" column.
    - Skips rows where DateTime_ET or Rain is missing/blank or unparseable.
    - Outputs columns: Date/Time, Rainfall
        - Rainfall: numeric value, rounded to 3 decimals
    - IDs row: "IDs:" in the first cell, then ID in the second cell
    - Format row: M/d/yyyy	in

4. For all other files:
    - Identifies columns for:
        - Date/Time (any column containing "date" or "time")
        - Depth     (any column containing "depth", "level", "lvl")
        - Flow      (any column containing "flow")
        - Velocity  (any column containing "velocity" or "vel")
      (Column names are case-insensitive and flexible.)
    - Renames columns for TSF output as: Date/Time, Depth, Flow, Velocity
    - If Velocity is not found, the output Velocity column is filled with blanks.
    - Formats 'Date/Time' as 'M/d/yyyy h:mm:ss AM/PM'
    - Rounds numeric columns per PCSWMM conventions:
        - Depth:    8 decimal places
        - Flow:     9 decimal places
        - Velocity: 8 decimal places
    - IDs row: "IDs:" in the first cell, then ID repeated for each data column (no ID for Date/Time)
    - Format row: M/d/yyyy	in	mgd	ft/s

5. The output TSF filename matches the CSV (except for extension).
6. The TSF header ID is extracted flexibly from the filename (letters/numbers-dash/underscore before the first date group).
7. Output is always: IDs row, header row, format row, and data (no units row).
8. Handles both UTF-8 and latin1 (ANSI) encoded input files.

How to use:
-----------
1. Place this script and your CSV files in the same folder.
2. Optionally, set ENABLE_DATE_CHECK to True to enable date validation (for standard files).
3. Run with Python 3.
4. For each CSV, a TSF file will be created in the same folder.

Date: 2026
"""

ENABLE_DATE_CHECK = False

def safe_read_csv(path, **kwargs):
    try:
        return pd.read_csv(path, encoding="utf-8", **kwargs)
    except UnicodeDecodeError:
        try:
            print(f"  [!] UTF-8 decode failed for {os.path.basename(path)}, trying latin1...")
            return pd.read_csv(path, encoding="latin1", **kwargs)
        except Exception as e:
            print(f"  [!] Failed to read {os.path.basename(path)}: {e}")
            raise

def extract_id(filename):
    fname = os.path.splitext(filename)[0]
    fname = re.sub(r'\s*to\s*.*$', '', fname)
    match = re.search(r'([A-Z0-9]+[-_][0-9]{2,})', fname, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r'(_\d{4}([-_]\d{2,})*)', fname)
    if match:
        return fname[:match.start()]
    return fname

def format_datetime(dt_str):
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M %p"):
        try:
            dt = datetime.strptime(dt_str, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Unrecognized date format: {dt_str}")
    m = str(dt.month)
    d = str(dt.day)
    y = str(dt.year)
    hour = dt.strftime("%I").lstrip('0') or '0'
    minute = dt.strftime("%M")
    ampm = dt.strftime("%p")
    return f"{m}/{d}/{y} {hour}:{minute}:00 {ampm}"

def find_column_ci(df, name_keywords):
    for col in df.columns:
        lcol = col.lower()
        if any(kw in lcol for kw in name_keywords):
            return col
    return None

def all_columns_ci(df, name_keywords):
    """Return a list of all columns matching any of the keywords."""
    matches = []
    for col in df.columns:
        lcol = col.lower()
        if any(kw in lcol for kw in name_keywords):
            matches.append(col)
    return matches

def find_column(df, keywords):
    for col in df.columns:
        lcol = col.lower()
        if any(k in lcol for k in keywords):
            return col
    return None

script_dir = os.path.dirname(os.path.abspath(__file__))

csv_files = [f for f in os.listdir(script_dir) if f.lower().endswith('.csv')]
total_files = len(csv_files)
processed_files = 0

for filename in csv_files:
    input_path = os.path.join(script_dir, filename)
    output_name = os.path.splitext(filename)[0] + ".tsf"
    output_path = os.path.join(script_dir, output_name)
    sample_id = extract_id(filename)

    try:
        if filename.startswith("BCOHSG"):
            df = safe_read_csv(input_path, skiprows=11, sep=',', engine='python')
            if not all(x in df.columns for x in ['Date', 'Time', 'LEVEL', 'TEMPERATURE']):
                print(f"  [!] Skipping {filename}: Required columns not found after skipping 10 lines.")
                continue
            df["Date/Time"] = df["Date"].astype(str) + " " + df["Time"].astype(str)
            df["Date/Time"] = df["Date/Time"].apply(format_datetime)
            df["Level"] = pd.to_numeric(df["LEVEL"], errors='coerce').round(8)
            df["Temperature"] = pd.to_numeric(df["TEMPERATURE"], errors='coerce').round(3)
            df = df[["Date/Time", "Level", "Temperature"]]
            format_row = ["M/d/yyyy", "ft", "F"]
            with open(output_path, "w") as f:
                f.write("IDs:" + ("\t" + "\t".join([sample_id] * (len(df.columns)-1)) if len(df.columns) > 1 else "") + "\n")
                f.write("\t".join(df.columns) + "\n")
                f.write("\t".join(format_row) + "\n")
                for _, row in df.iterrows():
                    f.write("\t".join(str(row[col]) for col in df.columns) + "\n")
        elif filename.startswith("BCOHRG"):
            df = safe_read_csv(input_path)
            rain_col = find_column_ci(df, ["rain"])
            dt_col = find_column_ci(df, ["et"])
            if rain_col is None or dt_col is None:
                print(f"  [!] Skipping {filename}: Could not find Rain or DateTime_ET columns.")
                continue
            out_rows = []
            for _, row in df.iterrows():
                date_val = str(row[dt_col]).strip()
                rain_val = row[rain_col]
                if date_val == "" or pd.isna(date_val):
                    continue
                try:
                    date_fmt = format_datetime(date_val)
                except Exception:
                    continue
                try:
                    rain_num = round(float(rain_val), 3)
                except Exception:
                    continue
                out_rows.append({'Date/Time': date_fmt, 'Rainfall': rain_num})
            outdf = pd.DataFrame(out_rows, columns=["Date/Time", "Rainfall"])
            format_row = ["M/d/yyyy", "in"]
            with open(output_path, "w") as f:
                f.write("IDs:" + ("\t" + "\t".join([sample_id] * (len(outdf.columns)-1)) if len(outdf.columns) > 1 else "") + "\n")
                f.write("\t".join(outdf.columns) + "\n")
                f.write("\t".join(format_row) + "\n")
                for _, row in outdf.iterrows():
                    f.write("\t".join(str(row[col]) for col in outdf.columns) + "\n")
        else:
            df = safe_read_csv(input_path)
            # Find the best match for each column, ensuring no duplicates
            date_col = find_column(df, ['date', 'time'])
            depth_cols = all_columns_ci(df, ['depth', 'level', 'lvl'])
            flow_cols = all_columns_ci(df, ['flow'])
            velocity_cols = all_columns_ci(df, ['velocity', 'vel'])
            # Assume first match for each, but ensure distinct columns if possible
            depth_col = depth_cols[0] if depth_cols else None
            flow_col = flow_cols[0] if flow_cols else None
            velocity_col = None
            for vcol in velocity_cols:
                if vcol != depth_col:
                    velocity_col = vcol
                    break
            if not velocity_col and velocity_cols:
                velocity_col = velocity_cols[0]  # fallback: use it even if same as depth

            colmap = {
                'Date/Time': date_col,
                'Depth': depth_col,
                'Flow': flow_col,
                'Velocity': velocity_col
            }
            missing = [k for k, v in colmap.items() if v is None]
            if missing:
                print(f"  [!] Skipping {filename}: Could not find columns: {', '.join(missing)}")
                continue

            df_out = pd.DataFrame()
            df_out["Date/Time"] = df[date_col].apply(format_datetime)
            df_out["Depth"] = df[depth_col].round(8)
            df_out["Flow"] = df[flow_col].round(9)
            # Use actual velocity column if distinct from depth, else blank
            if velocity_col and velocity_col != depth_col:
                df_out["Velocity"] = df[velocity_col].round(8)
            else:
                df_out["Velocity"] = [""] * len(df)
            format_row = ["M/d/yyyy", "in", "mgd", "ft/s"]
            with open(output_path, "w") as f:
                f.write("IDs:" + ("\t" + "\t".join([sample_id] * (len(df_out.columns)-1)) if len(df_out.columns) > 1 else "") + "\n")
                f.write("\t".join(df_out.columns) + "\n")
                f.write("\t".join(format_row) + "\n")
                for _, row in df_out.iterrows():
                    f.write("\t".join(str(row[col]) for col in df_out.columns) + "\n")
        print(f"Converted {filename} → {output_name}")
        processed_files += 1
    except Exception as e:
        print(f"  [!] Failed to process {filename}: {e}")

if total_files == 0:
    print("No CSV files found.")
elif processed_files == total_files:
    print(f"All {total_files} files were processed.")
else:
    print(f"Found {total_files} files, processed {processed_files} files.")