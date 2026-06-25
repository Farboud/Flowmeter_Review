PCSWMM TSF Processing Toolkit
=============================

This repository contains a set of Python scripts for converting, analyzing,
and validating TSF (time series) data used in PCSWMM and hydraulic monitoring workflows.

Contents
--------

The repository includes the following scripts:

1. csv_to_tsf_V3.py
2. Hydrograph_Scatterplot_V2.py
3. Mass_Balance.py

Overview
--------

These tools support a typical monitoring data workflow:

- Convert raw CSV files into PCSWMM-compatible TSF format
- Visualize and assess hydraulic behavior using measured data
- Perform mass balance checks across flow monitoring networks

All scripts operate locally and expect input files to be placed in the same working directory.

---------------------------------------------------------------------

1. csv_to_tsf_V3.py
-------------------

Purpose:
    Converts multiple CSV time series files into TSF format compatible with PCSWMM.

Key Features:
    - Automatically scans the working directory for CSV files
    - Processes files based on naming conventions

File Types:

A) Files starting with "BCOHSC"
    - Skips first 10 rows
    - Uses: Date, Time, LEVEL, TEMPERATURE
    - Outputs: Date/Time, Level, Temperature
    - Rounding:
        Level -> 8 decimals
        Temperature -> 3 decimals

B) Files starting with "BCOHRG"
    - Detects Rain column and DateTime_ET column dynamically
    - Ignores DateTime_MDT
    - Outputs: Date/Time, Rainfall
    - Rounding:
        Rainfall -> 3 decimals

C) All other files
    - Detects columns automatically:
        Date/Time
        Depth (depth/level/lvl)
        Flow
        Velocity (optional)
    - Outputs: Date/Time, Depth, Flow, Velocity
    - Missing velocity is left blank
    - Rounding:
        Depth -> 8 decimals
        Flow -> 9 decimals
        Velocity -> 8 decimals

Additional Behavior:
    - Extracts ID from filename
    - Formats timestamps for PCSWMM
    - Writes TSF structure:
        IDs row
        Header row
        Format row
        Data (no units row)
    - Supports UTF-8 and ANSI encoded files

Usage:
    python csv_to_tsf_V3.py

---------------------------------------------------------------------

2. Hydrograph_Scatterplot_V2.py
-------------------------------

Purpose:
    Provides a graphical interface for visualizing TSF data and comparing
    measured values with theoretical hydraulic relationships.

Key Features:
    - Automatically loads all TSF files in the directory
    - Categorizes files by monitoring type:
        Flow Meter
        Overflow Meter
        Rain Gauge
        Stream Gauge
    - Reads geometry and hydraulic data from Pipe_Information.csv

Plotting Options:

1) Depth vs Velocity
    - Measured values shown as scatter points
    - Theoretical curve computed using Manning's equation
    - Supports:
        Circular pipes
        Rectangular sections

2) Depth vs Area of Flow
    - Measured area calculated as:
        Flow / Velocity
    - Theoretical area computed using pipe geometry
    - Circular pipe calculations account for silt if present

3) Data Table View
    - Displays raw TSF data for validation

Hydraulic Assumptions:
    Manning's equation:
        V = (1/n) * Rh^(2/3) * S^(1/2)

    Circular pipes:
        Based on segment geometry
        Silt reduces effective flow area

    Rectangular channels:
        Area = width * depth

Additional Features:
    - Converts depth units (inches to feet when required)
    - Converts flow units (mgd to cfs when required)
    - Displays metadata in plots:
        ID, shape, slope, roughness, dimensions, silt depth, etc.

Usage:
    python Hydrograph_Scatterplot_V2.py

    Required in the same folder:
        - TSF files
        - Pipe_Information.csv

---------------------------------------------------------------------

3. Mass_Balance.py
------------------

Purpose:
    Performs automated mass balance calculations across a network of flow meters.

Key Features:
    - Reads all TSF files matching IDs in the mass balance configuration
    - For each node (ID):
        - Sums upstream inflows (FMs)
        - Sums upstream outflows (OFs)
        - Computes:
            Inflow - Outflow

Output:
    Generates one TSF file per ID:

        ID_startYYYYMMDD_endYYYYMMDD_Mass_Balance.tsf

    Each output file includes:
        - Date/Time
        - Original flow
        - All inflow time series
        - All outflow time series
        - Inflow (sum)
        - Outflow (sum)
        - Calculated value (Inflow-Outflow)

Additional Features:
    - Optional replacement of negative flows with zero
    - Preserves original timestamps
    - Cross-platform date formatting
    - Generates comparison plots

Usage:
    python Mass_Balance.py

    Configuration:
        Set in script:
            replace_negative_flows = True or False

---------------------------------------------------------------------

Input Requirements
------------------

TSF Files:
    Tab-delimited format:
        Row 1: IDs
        Row 2: Variable names
        Row 3: Units
        Row 4+: Data

Pipe_Information.csv:
    Must include columns such as:
        ID
        Type
        Depth (ft)
        Width (ft)
        Shape
        Slope
        Roughness
        Silt Depth (ft)

---------------------------------------------------------------------

Notes
-----

- TSF formatting follows PCSWMM conventions
- Column detection is flexible and case-insensitive
- Missing or invalid data is skipped where applicable
- Designed for real monitoring datasets and hydraulic validation workflows

---------------------------------------------------------------------

Version
-------
2026
