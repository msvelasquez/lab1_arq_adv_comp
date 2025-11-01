import subprocess, os, re, math, random, csv
from datetime import datetime

# --- gem5 paths ---
GEM5_PATH = "../build/ARM/gem5.opt"
A76_SCRIPT_PATH = "scripts/CortexA76_scripts_gem5/CortexA76.py"
OUTPUTS_PATH = "outputs/sa_jpg2k/"
os.makedirs(OUTPUTS_PATH, exist_ok=True)

# --- workload (jpeg2k decoder only) ---
WORKLOADS_BASE = "workloads/jpeg2k_dec/"
BINARY = "jpg2k_dec"
WORKLOAD_PARAMS = f'-i {WORKLOADS_BASE}jpg2kdec_testfile.j2k -o {OUTPUTS_PATH}image.pgm'

# --- stat to minimize ---
TARGET_STAT = r"simSeconds\s+(\d+(\.\d+)?)"

# --- search space ---
FU_BOUNDS = {
    "num_fu_intALU": (1, 6),
    "num_fu_read":   (1, 8),
    "num_fu_write":  (1, 8),
}
L1D_SIZES = [64, 128, 256, 512]   # kB
L1D_ASSOCS = [2, 4, 8, 16]        # realistic associativities
LINE_SIZE = 64                    # bytes

CSV_FILE = "annealing_results.csv"
CSV_EXPLORED = "explored_configs.csv"


# -------- helper functions --------
def is_power_of_two(x):
    return x > 0 and (x & (x - 1)) == 0

def valid_cache(size_kb, assoc):
    sets = (size_kb * 1024) // (LINE_SIZE * assoc)
    return sets > 0 and is_power_of_two(sets)

def cfg_key(cfg):
    return (
        cfg["num_fu_intALU"],
        cfg["num_fu_read"],
        cfg["num_fu_write"],
        cfg["l1d_size"],
        cfg["l1d_assoc"],
    )

def outdir_for(cfg):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return os.path.join(
        OUTPUTS_PATH,
        f"cfg_ALU{cfg['num_fu_intALU']}_R{cfg['num_fu_read']}_W{cfg['num_fu_write']}"
        f"_L1D{cfg['l1d_size']}kB_A{cfg['l1d_assoc']}_{stamp}"
    )

def build_cmd(cfg, outdir):
    return (
        f"{GEM5_PATH} --outdir={outdir} {A76_SCRIPT_PATH} "
        f"--cmd={WORKLOADS_BASE}{BINARY} "
        f'--options="{WORKLOAD_PARAMS}" '
        f"--num_fu_intALU={cfg['num_fu_intALU']} "
        f"--num_fu_read={cfg['num_fu_read']} "
        f"--num_fu_write={cfg['num_fu_write']} "
        f"--l1d_size={cfg['l1d_size']}kB "
        f"--l1d_assoc={cfg['l1d_assoc']}"
    )

def parse_sim_seconds(stats_path):
    if not os.path.exists(stats_path):
        return None
    with open(stats_path, "r") as f:
        for line in f:
            m = re.search(TARGET_STAT, line)
            if m:
                return float(m.group(1))
    return None

def run_config(cfg, cache):
    key = cfg_key(cfg)
    if key in cache:
        print("Cache hit:", cfg, "cost:", cache[key])
        return cache[key], None

    if not valid_cache(cfg["l1d_size"], cfg["l1d_assoc"]):
        print("Invalid cache config skipped:", cfg)
        cache[key] = float("inf")
        return float("inf"), None

    outdir = outdir_for(cfg)
    cmd = build_cmd(cfg, outdir)
    print("Launching:", cmd)
    p = subprocess.Popen(cmd, shell=True)
    p.wait()
    stats_path = os.path.join(outdir, "stats.txt")
    cost = parse_sim_seconds(stats_path)
    if cost is None or cost == 0.0:
        cost = float("inf")
    print("Finished config:", cfg, "cost:", cost)
    cache[key] = cost
    return cost, outdir

def all_neighbors(cfg, max_neighbors=12):
    """Generate up to max_neighbors valid unique neighbors."""
    neighs = set()
    def add(new_cfg):
        if valid_cache(new_cfg["l1d_size"], new_cfg["l1d_assoc"]):
            neighs.add(tuple(new_cfg.items()))

    # FU neighbors
    for k, (lo, hi) in FU_BOUNDS.items():
        for step in [-1, 1]:
            v = cfg[k] + step
            if lo <= v <= hi:
                new_cfg = dict(cfg)
                new_cfg[k] = v
                add(new_cfg)

    # Cache size neighbors
    sizes = L1D_SIZES
    idx = sizes.index(cfg["l1d_size"])
    for step in [-1, 1]:
        new_idx = idx + step
        if 0 <= new_idx < len(sizes):
            new_cfg = dict(cfg)
            new_cfg["l1d_size"] = sizes[new_idx]
            add(new_cfg)

    # Cache assoc neighbors
    idx_a = L1D_ASSOCS.index(cfg["l1d_assoc"])
    for step in [-1, 1]:
        new_idx = idx_a + step
        if 0 <= new_idx < len(L1D_ASSOCS):
            new_cfg = dict(cfg)
            new_cfg["l1d_assoc"] = L1D_ASSOCS[new_idx]
            add(new_cfg)

    neighbors = [dict(items) for items in neighs]

    # Pad with random valid samples if fewer than max_neighbors
    while len(neighbors) < max_neighbors:
        new_cfg = dict(cfg)
        for k in FU_BOUNDS.keys():
            lo, hi = FU_BOUNDS[k]
            new_cfg[k] = random.randint(lo, hi)
        new_cfg["l1d_size"] = random.choice(L1D_SIZES)
        new_cfg["l1d_assoc"] = random.choice(L1D_ASSOCS)
        if new_cfg != cfg and valid_cache(new_cfg["l1d_size"], new_cfg["l1d_assoc"]):
            if new_cfg not in neighbors:
                neighbors.append(new_cfg)

    random.shuffle(neighbors)
    return neighbors[:max_neighbors]

def run_parallel(candidates, cache):
    procs = {}
    results = {}

    for cfg in candidates:
        key = cfg_key(cfg)
        if key in cache:
            print("Cache hit (parallel):", cfg, "cost:", cache[key])
            results[key] = (cfg, cache[key], None)
            continue
        if not valid_cache(cfg["l1d_size"], cfg["l1d_assoc"]):
            print("Invalid cache config skipped (parallel):", cfg)
            cache[key] = float("inf")
            results[key] = (cfg, float("inf"), None)
            continue

        outdir = outdir_for(cfg)
        cmd = build_cmd(cfg, outdir)
        print("Launching neighbor:", cfg, "->", cmd)
        p = subprocess.Popen(cmd, shell=True)
        procs[p] = (cfg, outdir)

    for p, (cfg, outdir) in procs.items():
        p.wait()
        stats_path = os.path.join(outdir, "stats.txt")
        cost = parse_sim_seconds(stats_path)
        if cost is None or cost == 0.0:
            cost = float("inf")
        cache[cfg_key(cfg)] = cost
        results[cfg_key(cfg)] = (cfg, cost, outdir)
        print("Neighbor finished:", cfg, "cost:", cost)

    return results


# -------- annealing loop --------
def anneal_all_neighbors(start_cfg, rounds=10, T0=10.0, alpha=0.9, max_neighbors=12):
    cache = {}
    curr_cfg = dict(start_cfg)
    curr_cost, _ = run_config(curr_cfg, cache)
    best_cfg, best_cost = dict(curr_cfg), curr_cost
    T = T0

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["round","best_cfg","best_cost"])

        for r in range(rounds):
            neighbors = all_neighbors(curr_cfg, max_neighbors=max_neighbors)
            results = run_parallel(neighbors, cache)

            print(f"\n=== Round {r} ===")
            print("Current cfg:", curr_cfg, "cost:", curr_cost)
            accepted = []

            for _, (cfg, cost, outdir) in results.items():
                delta = cost - curr_cost
                prob = math.exp(-delta / max(T,1e-9)) if delta > 0 else 1.0
                print(f"Neighbor {cfg} -> cost={cost:.6f}, delta={delta:.6f}, accept_prob={prob:.4f}")
                if delta < 0 or (prob > random.random()):
                    accepted.append((cfg, cost))

            if accepted:
                chosen, chosen_cost = random.choice(accepted)
                print("Accepted neighbor:", chosen, "with cost", chosen_cost)
            else:
                chosen, chosen_cost = curr_cfg, curr_cost
                print("No neighbor accepted, staying at current config")

            curr_cfg, curr_cost = chosen, chosen_cost
            if curr_cost < best_cost:
                best_cfg, best_cost = dict(curr_cfg), curr_cost
                print("New best:", best_cfg, "with cost", best_cost)

            writer.writerow([r, best_cfg, best_cost])
            f.flush()
            print(f"End of round {r}: curr_cost={curr_cost}, best_cost={best_cost}, T={T:.3f}")
            T *= alpha

    print("Finished. Results in", CSV_FILE)

    # dump all explored configs to explored_configs.csv
    with open(CSV_EXPLORED, "w", newline="") as f2:
        writer2 = csv.writer(f2)
        writer2.writerow(["num_fu_intALU","num_fu_read","num_fu_write","l1d_size","l1d_assoc","cost"])
        for (alu, rd, wr, size, assoc), cost in cache.items():
            writer2.writerow([alu, rd, wr, size, assoc, cost])

    return best_cfg, best_cost


# -------- main --------
if __name__ == "__main__":
    random.seed(0)
    start = {
        "num_fu_intALU": 2,
        "num_fu_read": 2,
        "num_fu_write": 1,
        "l1d_size": 64,    # kB
        "l1d_assoc": 4     # realistic default
    }
    best_cfg, best_cost = anneal_all_neighbors(start, rounds=10, T0=8.0, alpha=0.92, max_neighbors=12)
    print("\nBest configuration:", best_cfg, "cost:", best_cost)

