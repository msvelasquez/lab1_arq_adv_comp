import os
import re
import pandas as pd

csv_path = "explored_configs.csv"
stats_dir = "collected"
mcpat_dir = "mcpat_salidas"
out_csv = "explored_configs_with_edp.csv"

df = pd.read_csv(csv_path)

edp_values = []

for idx, row in df.iterrows():
    alu   = int(row["num_fu_intALU"])
    r     = int(row["num_fu_read"])
    w     = int(row["num_fu_write"])
    size  = int(row["l1d_size"])
    a     = int(row["l1d_assoc"])

    ident = f"ALU{alu}_R{r}_W{w}_L1D{size}kB_A{a}"

    mcpat_file = os.path.join(mcpat_dir, f"output_{ident}.txt")
    stats_file = os.path.join(stats_dir, f"stats_{ident}.txt")

    try:
        with open(mcpat_file, "r") as f:
            text = f.read()
        leak_match = re.search(r"Total Leakage\s*=\s*([\d\.Ee+-]+)", text)
        run_match  = re.search(r"Runtime Dynamic\s*=\s*([\d\.Ee+-]+)", text)
        if not leak_match or not run_match:
            print(f"Missing power values for {ident}")
            edp_values.append(None)
            continue
        total_leak = float(leak_match.group(1))
        runtime_dyn = float(run_match.group(1))

        with open(stats_file, "r") as f:
            text = f.read()
        cpi_match = re.search(r"system\.cpu\.cpi\s+([\d\.Ee+-]+)", text)
        if not cpi_match:
            print(f"Missing CPI for {ident}")
            edp_values.append(None)
            continue
        cpi = float(cpi_match.group(1))

        edp = (total_leak + runtime_dyn) * cpi
        edp_values.append(edp)

    except FileNotFoundError:
        print(f"Missing files for {ident}")
        edp_values.append(None)

df.insert(df.columns.get_loc("cost")+1, "EDP", edp_values)

df.to_csv(out_csv, index=False)
print(f"Saved with EDP column -> {out_csv}")

