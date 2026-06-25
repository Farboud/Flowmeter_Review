"""
TSF Pipe Flow Analyzer GUI - Version 3

Description:
-------------
This Python GUI tool allows you to select and visualize data from TSF (tab-separated) monitoring files
and compare measured flow behavior against theoretical hydraulic relationships using pipe geometry and
properties from a separate Pipe_Information.csv file.

The application reads TSF files from the same folder as the script, groups them by monitoring device type,
and provides plotting tools for flow meters and other supported file types. Pipe information is matched to
each file using the extracted file ID.

Key Features:
-------------
- Automatically finds all `.tsf` files in the script folder.
- Categorizes files into:
    - Flow Meter
    - Overflow Meter
    - Rain Gauge
    - Stream Gauge
- Extracts the monitoring ID from the filename.
- Reads `Pipe_Information.csv` from the same folder.
- Converts TSF depth values from inches to feet when the TSF units row indicates inches.
- Displays the selected TSF file in tabular form for validation.
- Plots:
    1. Depth vs Velocity
        - Measured data shown as scatter points
        - Theoretical velocity curve shown using Manning's equation
        - Supports:
            - Circular pipes
            - Rectangular channels/pipes
    2. Depth vs Area of Flow
        - Measured depth points plotted using measured area = Flow / Velocity
        - Theoretical area curve derived from pipe geometry
        - For circular pipes with silt, theoretical area is calculated as:
              Area at water depth - Area at silt depth
- Displays plot metadata directly inside the plot:
    - ID
    - Type
    - Diameter
    - Width
    - Shape
    - Slope
    - Roughness
    - Silt Depth
    - Monitoring period

Hydraulic Assumptions:
----------------------
- Circular pipes:
    - Theoretical area is based on circular segment geometry.
    - If silt is present, the effective flow area is computed by subtracting the area up to silt depth
      from the area up to the water depth.
- Rectangular sections:
    - Area = width × effective water depth
    - Wetted perimeter = width + 2 × effective water depth
- Theoretical velocity is computed using Manning's equation:
      V = (1/n) * Rh^(2/3) * S^(1/2)

Input File Requirements:
------------------------
1. TSF files:
    - Tab-delimited
    - Expected format:
        Row 1: IDs
        Row 2: variable names
        Row 3: units
        Row 4+: data
2. Pipe_Information.csv:
    - Comma-delimited
    - Must contain columns such as:
        ID, Type, Depth (ft), Width (ft), Shape, Slope, Roughness, Silt Depth (ft)

How to Use:
-----------
1. Place this script in the same folder as:
    - your `.tsf` files
    - `Pipe_Information.csv`
2. Run the script.
3. Select a file category and file name from the GUI.
4. Choose one of the following actions:
    - Plot Depth vs Velocity
    - Plot Depth vs Area of Flow
    - Show Data Table

Notes:
------
- Measured area in the Depth vs Area of Flow plot is calculated as:
      measured area = measured flow / measured velocity
- Flow is converted from mgd to cfs when needed.
- All plot information is embedded directly in the plot window.

Date: 2026
"""

import os
import glob
import csv
import re
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

import tkinter as tk
from tkinter import ttk, messagebox

def categorize_file(filename):
    if filename.startswith('FL900_BCOHOF26'):
        return "Overflow Meter"
    elif filename.startswith('BCOHFM26'):
        return "Flow Meter"
    elif filename.startswith('BCOHRG'):
        return "Rain Gauge"
    elif filename.startswith('BCOHSC'):
        return "Stream Gauge"
    else:
        return "Unknown"

def extract_file_id(filename):
    name = os.path.splitext(filename)[0]
    m = re.search(r'_(?=\d)', name)
    if m:
        return name[:m.start()]
    else:
        return name

def read_tsf_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f]
    var_names = lines[1].split('\t')
    units_row = lines[2].split('\t')
    data = []
    for line in lines[3:]:
        values = line.split('\t')
        if len(values) < len(var_names):
            values += [''] * (len(var_names) - len(values))
        data.append(dict(zip(var_names, values)))
    return var_names, units_row, data

def get_monitoring_period(data, var_names):
    date_col = None
    for name in var_names:
        key = name.lower().replace(" ", "")
        if key in ('date/time', 'datetime', 'date'):
            date_col = name
            break
    if not date_col or len(data) < 1:
        return None, None
    dt_objs = []
    for row in data:
        raw = row.get(date_col, '').strip()
        if not raw:
            continue
        for fmt in ("%m/%d/%Y %I:%M:%S %p",
                    "%m/%d/%Y %H:%M",
                    "%Y-%m-%d %H:%M:%S"):
            try:
                dt_objs.append(datetime.strptime(raw, fmt))
                break
            except:
                continue
    if not dt_objs:
        return None, None
    return min(dt_objs), max(dt_objs)

def get_pipe_info(pipe_info_file, meter_id):
    if not os.path.exists(pipe_info_file):
        print("Pipe information file not found")
        return None
    with open(pipe_info_file, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=',')
        headers = next(reader)
        norm = [h.strip().lower().replace('\ufeff', '') for h in headers]
        def find_col(candidates):
            for c in candidates:
                if c in norm:
                    return norm.index(c)
            return None
        idx_id    = find_col(['id'])
        idx_type  = find_col(['type'])
        idx_diam  = find_col(['depth (ft)', 'diameter (ft)', 'depth'])
        idx_width = find_col(['width (ft)', 'width'])
        idx_shape = find_col(['shape'])
        idx_slope = find_col(['slope'])
        idx_rough = find_col(['roughness'])
        idx_silt  = find_col(['silt depth (ft)', 'silt depth', 'silt'])
        if None in [idx_id, idx_type, idx_diam, idx_width, idx_shape, idx_slope, idx_rough, idx_silt]:
            print("Could not find all required columns")
            return None
        for row in reader:
            if len(row) <= max(idx_id, idx_type, idx_diam, idx_width, idx_shape, idx_slope, idx_rough, idx_silt):
                continue
            rid = row[idx_id].strip()
            if rid == meter_id:
                try:
                    return {
                        'ID': row[idx_id].strip(),
                        'Type': row[idx_type].strip(),
                        'Diameter_ft': float(row[idx_diam]),
                        'Width_ft': float(row[idx_width]),
                        'Shape': row[idx_shape].strip(),
                        'Slope': float(row[idx_slope]),
                        'Roughness': float(row[idx_rough]),
                        'Silt_Depth_ft': float(row[idx_silt])
                    }
                except Exception as exc:
                    print("Error reading pipe info for", meter_id, exc)
                    return None
    print(f"ID {meter_id} not found in {pipe_info_file}")
    return None

def velocity_profile_circular(D, S, n, silt_depth=0, n_points=80):
    depths = np.linspace(0, D, n_points)
    velocities = np.zeros_like(depths)
    r = D / 2.0
    for i, y in enumerate(depths):
        y_eff = max(0.0, y - silt_depth)
        if y_eff <= 0.0:
            velocities[i] = 0.0
            continue
        if y_eff >= D:
            theta = 2.0 * np.pi
        else:
            arg = 1.0 - 2.0 * y_eff / D
            arg = max(-1.0, min(1.0, arg))
            theta = 2.0 * np.arccos(arg)
        area = (r**2 / 2.0) * (theta - np.sin(theta))
        perimeter = r * theta
        if perimeter <= 0.0:
            velocities[i] = 0.0
            continue
        Rh = area / perimeter
        V = (1.49 / n) * (Rh ** (2.0/3.0)) * (S ** 0.5)
        velocities[i] = V
    return depths, velocities

def velocity_profile_rectangular(D, W, S, n, silt_depth=0, n_points=80):
    depths = np.linspace(0, D, n_points)
    velocities = np.zeros_like(depths)
    for i, y in enumerate(depths):
        y_eff = max(0.0, y - silt_depth)
        if y_eff <= 0:
            velocities[i] = 0.0
            continue
        area = W * y_eff
        perimeter = W + 2 * y_eff
        if perimeter == 0:
            velocities[i] = 0.0
            continue
        Rh = area / perimeter
        V = (1.49 / n) * (Rh ** (2.0/3.0)) * (S ** 0.5)
        velocities[i] = V
    return depths, velocities

def area_profile_circular(D, silt_depth=0, n_points=80):
    """
    Returns (depths, areas) for a partially filled circular pipe, subtracting silt prism.
    D: diameter (ft)
    silt_depth: silt prism depth from invert (ft)
    """
    depths = np.linspace(0, D, n_points)
    areas = np.zeros_like(depths)
    r = D / 2.0

    def segment_area(h):
        if h <= 0:
            return 0.0
        if h >= D:
            return np.pi * r * r
        theta = 2.0 * np.arccos(1.0 - 2.0 * h / D)
        return (r ** 2 / 2.0) * (theta - np.sin(theta))

    silt_area = segment_area(silt_depth)
    for i, y in enumerate(depths):
        area = segment_area(y) - silt_area
        areas[i] = max(0.0, area)
    return depths, areas

def area_profile_rectangular(D, W, silt_depth=0, n_points=80):
    depths = np.linspace(0, D, n_points)
    areas = np.zeros_like(depths)
    for i, y in enumerate(depths):
        y_eff = max(0.0, y - silt_depth)
        if y_eff <= 0:
            areas[i] = 0.0
        else:
            areas[i] = W * y_eff
    return depths, areas

# --- GUI setup and behavior ---
folder = os.path.dirname(os.path.abspath(__file__))
tsf_files = glob.glob(os.path.join(folder, '*.tsf'))
categorized = {}
file_id_map = {}
for tsf in tsf_files:
    fn = os.path.basename(tsf)
    fid = extract_file_id(fn)
    file_id_map[fn] = fid
    cat = categorize_file(fn)
    categorized.setdefault(cat, []).append(tsf)

root = tk.Tk()
root.title("TSF Pipe Flow Analyzer")

ttk.Label(root, text="Select Type:").grid(row=0, column=0, padx=8, pady=8)
type_var = tk.StringVar()
type_cb = ttk.Combobox(root, textvariable=type_var, state="readonly")
type_cb['values'] = sorted(list(categorized.keys()))
type_cb.grid(row=0, column=1, padx=8, pady=8)

ttk.Label(root, text="Select File:").grid(row=1, column=0, padx=8, pady=8)
file_var = tk.StringVar()
file_cb = ttk.Combobox(root, textvariable=file_var, state="readonly")
file_cb.grid(row=1, column=1, padx=8, pady=8)

def update_files(*args):
    t = type_var.get()
    files = categorized.get(t, [])
    file_cb['values'] = [os.path.basename(f) for f in files]
    file_var.set('')

type_cb.bind('<<ComboboxSelected>>', update_files)

def show_table():
    sel_type = type_var.get()
    sel_file = file_var.get()
    if not sel_file:
        messagebox.showinfo("No file selected", "Please select a file.")
        return
    files = categorized.get(sel_type, [])
    filepath = None
    for f in files:
        if os.path.basename(f) == sel_file:
            filepath = f
            break
    if not filepath:
        messagebox.showinfo("File not found", "Selected file not found.")
        return
    var_names, units_row, data = read_tsf_file(filepath)
    if not var_names or not data:
        messagebox.showinfo("File error", "Could not read data from file.")
        return
    win = tk.Toplevel(root)
    win.title(f"Data Table: {sel_file}")
    frame = ttk.Frame(win)
    frame.pack(fill='both', expand=True)
    tree = ttk.Treeview(frame, columns=var_names, show='headings')
    for col in var_names:
        tree.heading(col, text=col)
        tree.column(col, width=120, anchor='center')
    for row in data[:2000]:
        values = [row.get(col, '') for col in var_names]
        tree.insert('', 'end', values=values)
    tree.pack(side='left', fill='both', expand=True)
    vsb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    vsb.pack(side='right', fill='y')
    tree.configure(yscrollcommand=vsb.set)
    hsb = ttk.Scrollbar(win, orient='horizontal', command=tree.xview)
    hsb.pack(side='bottom', fill='x')
    tree.configure(xscrollcommand=hsb.set)

def plot_depth_vs_area():
    sel_type = type_var.get()
    sel_file = file_var.get()
    if not sel_file:
        messagebox.showinfo("No file selected", "Please select a file.")
        return
    files = categorized.get(sel_type, [])
    filepath = None
    for f in files:
        if os.path.basename(f) == sel_file:
            filepath = f
            break
    if not filepath:
        messagebox.showinfo("File not found", "Selected file not found.")
        return

    var_names, units_row, data = read_tsf_file(filepath)
    if not var_names or not data:
        messagebox.showinfo("File error", "Could not read data from file.")
        return

    if 'Depth' not in var_names or 'Flow' not in var_names or 'Velocity' not in var_names:
        messagebox.showinfo("Columns missing", "This file must have 'Depth', 'Flow', and 'Velocity' columns in row 2 of the TSF.")
        return

    depth_col_idx = var_names.index('Depth')
    depth_is_in_inches = False
    if units_row and len(units_row) > depth_col_idx:
        depth_unit_raw = units_row[depth_col_idx].strip().lower()
        depth_is_in_inches = depth_unit_raw in ["in", "inch", "inches"]

    flow_col_idx = var_names.index('Flow')
    flow_unit = None
    flow_to_cfs = 1.0
    if units_row and len(units_row) > flow_col_idx:
        flow_unit = units_row[flow_col_idx].strip().lower()
        if flow_unit == "mgd":
            flow_to_cfs = 1.54723
        elif flow_unit in ("cfs", "ft3/s", "ft^3/s"):
            flow_to_cfs = 1.0

    measured_depths = []
    measured_areas = []
    for row in data:
        try:
            d = float(row.get('Depth', '').strip())
            v = float(row.get('Velocity', '').strip())
            q = float(row.get('Flow', '').strip())
            if depth_is_in_inches:
                d = d / 12.0
            if v == 0 or np.isnan(d) or np.isnan(q) or np.isnan(v):
                continue
            q_cfs = q * flow_to_cfs
            area = q_cfs / v
            if area > 0:
                measured_depths.append(d)
                measured_areas.append(area)
        except Exception:
            continue

    if not measured_depths:
        messagebox.showinfo("No valid data", "No valid Depth/Area pairs found.")
        return

    file_id = file_id_map.get(sel_file, extract_file_id(sel_file))
    pipe_info_file = os.path.join(folder, 'Pipe_Information.csv')
    pipe = get_pipe_info(pipe_info_file, file_id)
    shape = pipe['Shape'].lower() if pipe else ''
    if not pipe or (not (shape.startswith('circ') or shape.startswith('rect'))):
        messagebox.showinfo("Unavailable", "Area curve only available for circular or rectangular pipes.")
        return

    info_lines = [
        f"ID: {pipe['ID']}",
        f"Type: {pipe['Type']}",
        f"Diameter (ft): {pipe['Diameter_ft']}",
        f"Width (ft): {pipe['Width_ft']}",
        f"Shape: {pipe['Shape']}",
        f"Slope: {pipe['Slope']}",
        f"Roughness: {pipe['Roughness']}",
        f"Silt Depth (ft): {pipe['Silt_Depth_ft']}"
    ]
    info_text = "\n".join(info_lines)

    if shape.startswith('circ'):
        D = pipe['Diameter_ft']
        silt = pipe['Silt_Depth_ft']
        depths_theory, areas_theory = area_profile_circular(D, silt, n_points=200)
    elif shape.startswith('rect'):
        D = pipe['Diameter_ft']
        W = pipe['Width_ft']
        silt = pipe['Silt_Depth_ft']
        depths_theory, areas_theory = area_profile_rectangular(D, W, silt, n_points=200)
    else:
        messagebox.showinfo("Unavailable", "Area curve only available for circular or rectangular pipes.")
        return

    plt.figure(figsize=(8,6))
    plt.scatter(measured_areas, measured_depths, color='orange', label='Measured Depth', zorder=3)
    plt.plot(areas_theory, depths_theory, 'b-', linewidth=2, label='Theoretical Area (ft²)', zorder=4)

    plt.xlabel("Area of Flow (ft²)")
    plt.ylabel("Depth (ft)")
    plt.title(f"{file_id}\nDepth vs Area of Flow ({pipe['Type']})")

    plt.gca().text(
        0.02, 0.98, info_text,
        transform=plt.gca().transAxes,
        fontsize=10,
        verticalalignment='top',
        horizontalalignment='left',
        bbox=dict(facecolor='white', edgecolor='gray', alpha=0.8)
    )

    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

def plot_scatter():
    sel_type = type_var.get()
    sel_file = file_var.get()
    if not sel_file:
        messagebox.showinfo("No file selected", "Please select a file.")
        return
    files = categorized.get(sel_type, [])
    filepath = None
    for f in files:
        if os.path.basename(f) == sel_file:
            filepath = f
            break
    if not filepath:
        messagebox.showinfo("File not found", "Selected file not found.")
        return

    var_names, units_row, data = read_tsf_file(filepath)
    if not var_names or not data:
        messagebox.showinfo("File error", "Could not read data from file.")
        return

    if 'Depth' not in var_names or 'Velocity' not in var_names:
        messagebox.showinfo("Columns missing", "This file must have 'Depth' and 'Velocity' columns in row 2 of the TSF.")
        return

    depth_col_idx = var_names.index('Depth')
    depth_is_in_inches = False
    if units_row and len(units_row) > depth_col_idx:
        depth_unit_raw = units_row[depth_col_idx].strip().lower()
        depth_is_in_inches = depth_unit_raw in ["in", "inch", "inches"]

    measured_depths = []
    measured_vels = []
    for row in data:
        try:
            d = float(row.get('Depth', '').strip())
            v = float(row.get('Velocity', '').strip())
            if depth_is_in_inches:
                d = d / 12.0
            if not (np.isnan(d) or np.isnan(v)):
                measured_depths.append(d)
                measured_vels.append(v)
        except Exception:
            continue

    if not measured_depths:
        messagebox.showinfo("No valid data", "No valid Depth/Velocity pairs found.")
        return

    dt_start, dt_end = get_monitoring_period(data, var_names)
    period_str = "Unknown"
    if dt_start and dt_end:
        period_str = f"{dt_start.strftime('%Y-%m-%d %H:%M:%S')}  to  {dt_end.strftime('%Y-%m-%d %H:%M:%S')}"

    file_id = file_id_map.get(sel_file, extract_file_id(sel_file))

    pipe_info_file = os.path.join(folder, 'Pipe_Information.csv')
    theory_depths = theory_vels = None
    pipe_info_display = {
        "ID": file_id,
        "Type": "N/A",
        "Diameter (ft)": "N/A",
        "Width (ft)": "N/A",
        "Shape": "N/A",
        "Slope": "N/A",
        "Roughness": "N/A",
        "Silt Depth (ft)": "N/A"
    }
    pipe = get_pipe_info(pipe_info_file, file_id)
    show_theory = False
    if pipe:
        pipe_info_display = {
            "ID": pipe['ID'],
            "Type": pipe['Type'],
            "Diameter (ft)": pipe['Diameter_ft'],
            "Width (ft)": pipe['Width_ft'],
            "Shape": pipe['Shape'],
            "Slope": pipe['Slope'],
            "Roughness": pipe['Roughness'],
            "Silt Depth (ft)": pipe['Silt_Depth_ft']
        }
        shape = pipe['Shape'].lower()
        if shape.startswith('circ') and float(pipe['Diameter_ft']) > 0:
            D = pipe['Diameter_ft']
            S = pipe['Slope']
            n_m = pipe['Roughness']
            silt = pipe['Silt_Depth_ft']
            theory_depths, theory_vels = velocity_profile_circular(D, S, n_m, silt, n_points=200)
            show_theory = True
        elif shape.startswith('rect') and float(pipe['Diameter_ft']) > 0 and float(pipe['Width_ft']) > 0:
            D = pipe['Diameter_ft']
            W = pipe['Width_ft']
            S = pipe['Slope']
            n_m = pipe['Roughness']
            silt = pipe['Silt_Depth_ft']
            theory_depths, theory_vels = velocity_profile_rectangular(D, W, S, n_m, silt, n_points=200)
            show_theory = True

    info_lines = [
        f"ID: {pipe_info_display['ID']}",
        f"Type: {pipe_info_display['Type']}",
        f"Diameter (ft): {pipe_info_display['Diameter (ft)']}",
        f"Width (ft): {pipe_info_display['Width (ft)']}",
        f"Shape: {pipe_info_display['Shape']}",
        f"Slope (%): {pipe_info_display['Slope']*100:.3f}",
        #f"Slope: {pipe_info_display['Slope']}",
        f"Roughness: {pipe_info_display['Roughness']}",
        f"Silt Depth (ft): {pipe_info_display['Silt Depth (ft)']}",
        f"Monitoring: {period_str}"
    ]
    info_text = "\n".join(info_lines)

    plt.figure(figsize=(8,6))
    plt.scatter(measured_vels, measured_depths, alpha=0.7, label='Measured Data', zorder=3)
    if show_theory and theory_depths is not None and theory_vels is not None:
        plt.plot(theory_vels, theory_depths, 'r--', linewidth=2, label='Theoretical Velocity (Manning)', zorder=4)
        if pipe and pipe['Shape'].lower().startswith('circ'):
            plt.axhline(y=pipe['Diameter_ft'], color='red', linestyle=':', linewidth=1.5,
                        label='Pipe Diameter (ft)', zorder=1)
        elif pipe and pipe['Shape'].lower().startswith('rect'):
            plt.axhline(y=pipe['Diameter_ft'], color='red', linestyle=':', linewidth=1.5,
                        label='Pipe Height (ft)', zorder=1)
    plt.xlabel("Velocity (ft/s)")
    plt.ylabel("Depth (ft)")
    plt.title(f"{file_id}\nDepth vs Velocity ({pipe_info_display['Type']})")
    plt.gca().text(
        0.02, 0.98, info_text,
        transform=plt.gca().transAxes,
        fontsize=10,
        verticalalignment='top',
        horizontalalignment='left',
        bbox=dict(facecolor='white', edgecolor='gray', alpha=0.8)
    )
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

btn_plot = ttk.Button(root, text="Plot Depth vs Velocity", command=plot_scatter)
btn_plot.grid(row=2, column=0, columnspan=2, padx=8, pady=8)

btn_area = ttk.Button(root, text="Plot Depth vs Area of Flow", command=plot_depth_vs_area)
btn_area.grid(row=3, column=0, columnspan=2, padx=8, pady=8)

btn_table = ttk.Button(root, text="Show Data Table", command=show_table)
btn_table.grid(row=4, column=0, columnspan=2, padx=8, pady=8)

root.mainloop()