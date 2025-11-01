import os
import subprocess

mcpat_exec = "./mcpat"        # path to your McPAT binary
xml_dir = "xml_files"          # folder with config_ALU*.xml
out_dir = "mcpat_salidas"     # output folder

os.makedirs(out_dir, exist_ok=True)

# collect xml files
xml_files = [f for f in os.listdir(xml_dir) if f.startswith("config_ALU") and f.endswith(".xml")]

for xml_file in xml_files:
    try:
        # extract identifier (ALU... etc.)
        identifier = xml_file.replace("config_", "").replace(".xml", "")
        out_file = os.path.join(out_dir, f"output_{identifier}.txt")

        xml_path = os.path.join(xml_dir, xml_file)

        cmd = [mcpat_exec, "-infile", xml_path, "-print_level", "1"]
        print(f"Running: {' '.join(cmd)} -> {out_file}")

        with open(out_file, "w") as outf:
            subprocess.run(cmd, stdout=outf, stderr=subprocess.PIPE, check=True)

    except subprocess.CalledProcessError as e:
        print(f"McPAT failed for {xml_file}: {e.stderr.decode(errors='ignore')}")
    except Exception as e:
        print(f"Error with {xml_file}: {e}")

