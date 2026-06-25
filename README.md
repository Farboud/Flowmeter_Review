PCSWMM TSF Processing Toolkit
This repository contains three Python scripts for converting, analyzing, and validating TSF (time series) data used in PCSWMM and hydraulic monitoring workflows.
Scripts included (in order):

csv_to_tsf_V3.py
Hydrograph_Scatterplot_V2.py
Mass_Balance.py


OVERVIEW
These scripts are designed to work together:

Convert raw CSV monitoring data into TSF format
Visually analyze hydraulic behavior and compare to theory
Perform system-wide mass balance checks

All scripts are intended to run locally using Python 3 and operate on files located in the same directory.


csv_to_tsf_V3.py


Purpose:
Converts multiple CSV files into PCSWMM-compatible TSF files.
Main functionality:

Scans the working directory for all CSV files
Processes files differently based on filename patterns

File types:
A) Files starting with "BCOHSC"

Skips first 10 lines
Uses columns: Date, Time, LEVEL, TEMPERATURE
Outputs:
Date/Time, Level, Temperature
Rounding:
Level → 8 decimals
Temperature → 3 decimals

B) Files starting with "BCOHRG"

Automatically detects:

Rain column (contains "rain")
DateTime_ET column (contains "et")


Ignores DateTime_MDT
Outputs:
Date/Time, Rainfall
Rainfall rounded to 3 decimals

C) All other files

Automatically detects columns:

Date/Time
Depth (depth/level/lvl)
Flow
Velocity (optional)


Outputs:
Date/Time, Depth, Flow, Velocity
If velocity not found, column is left blank
Rounding:
Depth → 8 decimals
Flow → 9 decimals
Velocity → 8 decimals

General behavior:

Extracts ID from filename
Formats dates for PCSWMM compatibility
Writes TSF with:

IDs row
header row
format row
data (no units row)


Handles UTF-8 and ANSI files
Output filename matches input CSV

Usage:

Place script and CSV files in the same folder
Run:
python csv_to_tsf_V3.py



Hydrograph_Scatterplot_V2.py


Purpose:
GUI tool for visualizing TSF data and comparing measured results to theoretical hydraulic behavior.
Main functionality:


Loads all TSF files in the directory


Groups files by monitoring type:

Flow Meter
Overflow Meter
Rain Gauge
Stream Gauge



Reads Pipe_Information.csv for hydraulic properties


Available actions:

Plot Depth vs Velocity


Measured values shown as scatter points
Theoretical curve calculated using Manning’s equation
Supports:

Circular pipes
Rectangular sections




Plot Depth vs Area of Flow


Measured area = Flow / Velocity
Theoretical area computed using pipe geometry
For circular pipes with silt:
effective area = area(water depth) - area(silt depth)


Show Data Table


Displays raw TSF data for validation

Hydraulic assumptions:


Manning’s equation:
V = (1/n) * Rh^(2/3) * S^(1/2)


Circular pipes:
based on segment geometry


Rectangular channels:
Area = width × depth


Other features:

Converts depth units (inches to feet when needed)
Converts flow units (mgd to cfs when needed)
Displays metadata directly on plots:
ID, shape, slope, roughness, silt depth, etc.

Usage:

Place script, TSF files, and Pipe_Information.csv in the same folder
Run:
python Hydrograph_Scatterplot_V2.py
Use GUI to select file and plotting option



Mass_Balance.py


Purpose:
Performs mass balance calculations across a network of flow meters.
Main functionality:


Reads all TSF files that match IDs in the mass balance table


For each node (ID):

Sums upstream inflows (FMs)
Sums upstream outflows (OFs)
Computes:
Inflow - Outflow



Uses timestamps from the original data


Outputs:
For each ID, creates a TSF file:
ID_startYYYYMMDD_endYYYYMMDD_Mass_Balance.tsf
Output includes:

Date/Time
Original flow
Each inflow series
Each outflow series
Inflow (Sum)
Outflow (Sum)
Calculated value (Inflow-Outflow)

Other features:

Optional replacement of negative flows with zero
Cross-platform date formatting (Windows/Linux/Mac)
Plots original vs calculated series

Usage:

Place script and TSF files in the same folder
Configure mass balance table inside the script
Run:
python Mass_Balance.py


INPUT REQUIREMENTS
TSF files:

Tab-delimited format:
Row 1: IDs
Row 2: variable names
Row 3: units
Row 4+: data

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


NOTES

All scripts assume consistent TSF formatting for PCSWMM
Column detection is flexible and case-insensitive
Missing or invalid data is skipped where applicable
Designed for real monitoring datasets and hydraulic validation workflows


VERSION
2026
