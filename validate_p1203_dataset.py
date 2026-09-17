import csv
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "open-dataset"
RESULTS = ROOT / "validation" / "results"

MODES = ["mode0", "mode1", "mode2", "mode3"]
TOLERANCES = [0.001, 0.01, 0.05]
SCALARS = ["O23", "O35", "O46"]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def flatten_numeric(value):
    if isinstance(value, list):
        return [safe_float(x) for x in value]
    x = safe_float(value)
    return [] if x is None else [x]


def scalar_metrics(pred, ref):
    p = safe_float(pred)
    r = safe_float(ref)
    if p is None or r is None:
        return None
    e = abs(p - r)
    return {
        "prediction": p,
        "reference": r,
        "absolute_error": e,
        "squared_error": (p - r) ** 2,
        "within_0.001": e <= 0.001,
        "within_0.01": e <= 0.01,
        "within_0.05": e <= 0.05,
    }


def sequence_metrics(pred, ref):
    p = flatten_numeric(pred)
    r = flatten_numeric(ref)
    n = min(len(p), len(r))

    if n == 0:
        return {
            "prediction_length": len(p),
            "reference_length": len(r),
            "compared_length": 0,
            "length_match": len(p) == len(r),
            "mae": None,
            "rmse": None,
            "max_error": None,
            "within_0.001_pct": None,
            "within_0.01_pct": None,
            "within_0.05_pct": None,
        }

    errors = [abs(p[i] - r[i]) for i in range(n)]
    sq = [(p[i] - r[i]) ** 2 for i in range(n)]

    return {
        "prediction_length": len(p),
        "reference_length": len(r),
        "compared_length": n,
        "length_match": len(p) == len(r),
        "mae": sum(errors) / n,
        "rmse": math.sqrt(sum(sq) / n),
        "max_error": max(errors),
        "within_0.001_pct": 100 * sum(e <= 0.001 for e in errors) / n,
        "within_0.01_pct": 100 * sum(e <= 0.01 for e in errors) / n,
        "within_0.05_pct": 100 * sum(e <= 0.05 for e in errors) / n,
    }


def run_model(input_path):
    code = (
        "import json,sys; "
        "from itu_p1203.p1203_standalone import P1203Standalone; "
        "p=json.load(open(sys.argv[1],encoding='utf-8')); "
        "r=P1203Standalone(p,debug=False,quiet=True)"
        ".calculate_complete(print_intermediate=False); "
        "print(json.dumps(r))"
    )

    proc = subprocess.run(
        [sys.executable, "-c", code, str(input_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            "P.1203 failed: " + (proc.stderr.strip() or proc.stdout.strip())
        )

    return json.loads(proc.stdout)


def parse_pvs_context(input_path):
    name = input_path.name
    stem = name[:-len("-input.json")]

    context = None

    for c in ("mobile", "pc"):
        if stem.endswith("-" + c):
            context = c
            break

    pvs_id = stem

    if context:
        pvs_id = stem[:-(len(context) + 1)]

    # Dataset filenames contain the leading dataset number "046-",
    # while MOS uses the PVS ID without that prefix.
    if pvs_id.startswith("046-"):
        pvs_id = pvs_id[4:]

    return pvs_id, context


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def rank(values):
    indexed = sorted(enumerate(values), key=lambda z: z[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg
        i = j + 1
    return ranks


def spearman(xs, ys):
    if len(xs) < 2:
        return None
    return pearson(rank(xs), rank(ys))


def load_mos():
    candidates = [
        DATASET / "subjective_scores" / "mos.csv",
        DATASET / "mos.csv",
    ]

    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return {}

    rows = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            pvs = row.get("pvs_id")
            context = (row.get("context") or "").lower()
            mos = safe_float(row.get("mos"))
            if pvs and context and mos is not None:
                rows[(pvs, context)] = mos
    return rows


def write_csv(path, rows, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        if fieldnames:
            with open(path, "w", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=fieldnames).writeheader()
        return

    if fieldnames is None:
        fieldnames = list(rows[0].keys())

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def validate_mode(mode):
    mode_dir = DATASET / mode
    inputs = sorted(mode_dir.glob("*-input.json"))

    detailed = []
    mos_rows = []
    failures = []

    mos_map = load_mos()

    for idx, input_path in enumerate(inputs, 1):
        reference_path = Path(str(input_path).replace("-input.json", ".json"))
        pvs_id, context = parse_pvs_context(input_path)

        base = {
            "mode": mode,
            "file": input_path.name,
            "pvs_id": pvs_id,
            "context": context or "",
            "status": "OK",
            "error": "",
        }

        try:
            if not reference_path.exists():
                raise FileNotFoundError(
                    f"Reference output missing: {reference_path.name}"
                )

            reference = load_json(reference_path)
            generated = run_model(input_path)

            row = dict(base)

            for key in SCALARS:
                m = scalar_metrics(generated.get(key), reference.get(key))
                if m is None:
                    row[f"{key}_error"] = ""
                    row[f"{key}_within_0.01"] = ""
                else:
                    row[f"{key}_generated"] = m["prediction"]
                    row[f"{key}_reference"] = m["reference"]
                    row[f"{key}_error"] = m["absolute_error"]
                    row[f"{key}_within_0.001"] = m["within_0.001"]
                    row[f"{key}_within_0.01"] = m["within_0.01"]
                    row[f"{key}_within_0.05"] = m["within_0.05"]

            o34 = sequence_metrics(generated.get("O34"), reference.get("O34"))
            for k, v in o34.items():
                row["O34_" + k] = v

            # Also check the per-sample O21/O22 sequences when present.
            for key in ("O21", "O22"):
                if key in generated and key in reference:
                    sm = sequence_metrics(generated[key], reference[key])
                    row[f"{key}_mae"] = sm["mae"]
                    row[f"{key}_rmse"] = sm["rmse"]
                    row[f"{key}_max_error"] = sm["max_error"]
                    row[f"{key}_length_match"] = sm["length_match"]
                    row[f"{key}_within_0.01_pct"] = sm["within_0.01_pct"]

            mos = mos_map.get((
                pvs_id.strip(),
                (context or "").strip().lower()
            ))
            if mos is not None and safe_float(generated.get("O46")) is not None:
                pred_o46 = float(generated["O46"])
                mos_rows.append({
                    "mode": mode,
                    "pvs_id": pvs_id,
                    "context": context or "",
                    "O46": pred_o46,
                    "MOS": mos,
                    "absolute_error": abs(pred_o46 - mos),
                    "squared_error": (pred_o46 - mos) ** 2,
                })

            detailed.append(row)

        except Exception as exc:
            base["status"] = "FAILED"
            base["error"] = str(exc)
            detailed.append(base)
            failures.append(base)

        if idx % 10 == 0 or idx == len(inputs):
            print(f"[{mode}] {idx}/{len(inputs)} processed")

    # Scalar summary
    summary = []
    for key in SCALARS:
        vals = [
            (r[f"{key}_generated"], r[f"{key}_reference"])
            for r in detailed
            if r.get("status") == "OK"
            and r.get(f"{key}_generated") != ""
            and r.get(f"{key}_reference") != ""
        ]

        if vals:
            errors = [abs(a - b) for a, b in vals]
            summary.append({
                "mode": mode,
                "metric": key,
                "cases": len(vals),
                "mae": sum(errors) / len(errors),
                "rmse": math.sqrt(sum(e * e for e in errors) / len(errors)),
                "max_error": max(errors),
                "within_0.001_pct": 100 * sum(e <= 0.001 for e in errors) / len(errors),
                "within_0.01_pct": 100 * sum(e <= 0.01 for e in errors) / len(errors),
                "within_0.05_pct": 100 * sum(e <= 0.05 for e in errors) / len(errors),
            })

    o34_rows = [r for r in detailed if r.get("O34_mae") is not None]
    if o34_rows:
        summary.append({
            "mode": mode,
            "metric": "O34_sequence",
            "cases": len(o34_rows),
            "mae": sum(r["O34_mae"] for r in o34_rows) / len(o34_rows),
            "rmse": math.sqrt(
                sum(r["O34_rmse"] ** 2 for r in o34_rows) / len(o34_rows)
            ),
            "max_error": max(r["O34_max_error"] for r in o34_rows),
            "within_0.001_pct": sum(r["O34_within_0.001_pct"] for r in o34_rows) / len(o34_rows),
            "within_0.01_pct": sum(r["O34_within_0.01_pct"] for r in o34_rows) / len(o34_rows),
            "within_0.05_pct": sum(r["O34_within_0.05_pct"] for r in o34_rows) / len(o34_rows),
        })

    # MOS comparison
    mos_summary = {}
    if mos_rows:
        xs = [r["O46"] for r in mos_rows]
        ys = [r["MOS"] for r in mos_rows]
        errors = [abs(x - y) for x, y in zip(xs, ys)]
        mos_summary = {
            "mode": mode,
            "cases": len(mos_rows),
            "MAE": sum(errors) / len(errors),
            "RMSE": math.sqrt(
                sum((x - y) ** 2 for x, y in zip(xs, ys)) / len(xs)
            ),
            "Pearson": pearson(xs, ys),
            "Spearman": spearman(xs, ys),
        }

    write_csv(RESULTS / f"{mode}_detailed.csv", detailed)
    write_csv(RESULTS / f"{mode}_summary.csv", summary)
    write_csv(RESULTS / f"{mode}_mos_comparison.csv", mos_rows)

    return {
        "mode": mode,
        "input_cases": len(inputs),
        "successful": sum(r["status"] == "OK" for r in detailed),
        "failed": len(failures),
        "summary": summary,
        "mos": mos_summary,
    }


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)

    all_results = []

    for mode in MODES:
        print()
        print("=" * 70)
        print(f"VALIDATING {mode.upper()}")
        print("=" * 70)
        all_results.append(validate_mode(mode))

    overall_rows = []

    for result in all_results:
        for row in result["summary"]:
            overall_rows.append(row)

    write_csv(RESULTS / "overall_summary.csv", overall_rows)

    with open(RESULTS / "validation_summary.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print()
    print("=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)

    for r in all_results:
        print(
            f'{r["mode"]}: '
            f'{r["successful"]}/{r["input_cases"]} successful, '
            f'{r["failed"]} failed'
        )

        for m in r["summary"]:
            print(
                f'  {m["metric"]}: '
                f'MAE={m["mae"]:.10f}, '
                f'RMSE={m["rmse"]:.10f}, '
                f'Max={m["max_error"]:.10f}, '
                f'±0.01={m["within_0.01_pct"]:.2f}%'
            )

        if r["mos"]:
            print(
                f'  O46 vs MOS: '
                f'MAE={r["mos"]["MAE"]:.6f}, '
                f'RMSE={r["mos"]["RMSE"]:.6f}, '
                f'Pearson={r["mos"]["Pearson"]}, '
                f'Spearman={r["mos"]["Spearman"]}'
            )

    print()
    print(f"Reports: {RESULTS}")


if __name__ == "__main__":
    main()
