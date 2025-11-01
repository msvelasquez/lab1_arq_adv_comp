import os
import subprocess

# paths
converter = "gem5toMcPAT_cortexA76.py"   # adjust path if needed
input_dir = "collected"
arch_xml  = "ARM_A76_2.1GHz.xml"         # baseline architecture XML

# gather all stats files
stats_files = [f for f in os.listdir(input_dir) if f.startswith("stats_ALU") and f.endswith(".txt")]

for stats_file in stats_files:
    try:
        # extract identifier
        identifier = stats_file.replace("stats_", "").replace(".txt", "")
        config_file = f"config_{identifier}.json"

        stats_path  = os.path.join(input_dir, stats_file)
        config_path = os.path.join(input_dir, config_file)
        xml_out     = os.path.join(input_dir, f"config_{identifier}.xml")

        # check existence of both files
        if not os.path.exists(config_path):
            print(f"Skipping {identifier}: config missing")
            continue

        # run conversion command
        cmd = [
            "python3", converter,
            stats_path,
            config_path,
            arch_xml
        ]
        print(f"Running: {' '.join(cmd)} -> {xml_out}")

        with open(xml_out, "w") as out:
            subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE, check=True)

    except subprocess.CalledProcessError as e:
        print(f"Conversion failed for {identifier}: {e.stderr.decode(errors='ignore')}")
    except Exception as e:
        print(f"Error with {identifier}: {e}")

