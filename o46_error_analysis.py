import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "validation" / "results"
ANALYSIS = RESULTS / "o46_analysis"

MODES = ["mode0", "mode1", "mode2", "mode3"]


# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        print(f"[SKIP] No rows for {path.name}")
        return

    fieldnames = list(rows[0].keys())

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[WRITE] {path}")


def mean(values):
    values = [x for x in values if x is not None]

    if not values:
        return None

    return sum(values) / len(values)


def rmse(values):
    values = [x for x in values if x is not None]

    if not values:
        return None

    return math.sqrt(sum(x * x for x in values) / len(values))


def pearson(xs, ys):
    pairs = [
        (x, y)
        for x, y in zip(xs, ys)
        if x is not None and y is not None
    ]

    if len(pairs) < 2:
        return None

    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]

    mx = mean(xs)
    my = mean(ys)

    numerator = sum(
        (x - mx) * (y - my)
        for x, y in zip(xs, ys)
    )

    denominator_x = math.sqrt(
        sum((x - mx) ** 2 for x in xs)
    )

    denominator_y = math.sqrt(
        sum((y - my) ** 2 for y in ys)
    )

    if denominator_x == 0 or denominator_y == 0:
        return None

    return numerator / (denominator_x * denominator_y)


# ------------------------------------------------------------
# Load detailed validation results
# ------------------------------------------------------------

def load_all_detailed():
    rows = []

    for mode in MODES:
        path = RESULTS / f"{mode}_detailed.csv"

        if not path.exists():
            print(f"[WARNING] Missing {path}")
            continue

        data = read_csv(path)

        for row in data:
            row["mode"] = mode

        rows.extend(data)

    return rows


# ------------------------------------------------------------
# 1. Basic O46 error dataset
# ------------------------------------------------------------

def build_o46_error_dataset(rows):
    output = []

    for row in rows:
        if row.get("status") != "OK":
            continue

        generated = safe_float(row.get("O46_generated"))
        reference = safe_float(row.get("O46_reference"))
        error = safe_float(row.get("O46_error"))

        if generated is None or reference is None:
            continue

        signed_error = generated - reference

        output.append({
            "mode": row.get("mode", ""),
            "file": row.get("file", ""),
            "pvs_id": row.get("pvs_id", ""),
            "context": row.get("context", ""),
            "O46_generated": generated,
            "O46_reference": reference,
            "O46_error": error,
            "O46_signed_error": signed_error,
            "O46_overestimated": signed_error > 0,
            "O46_underestimated": signed_error < 0,
            "O46_exact_direction": (
                "overestimate"
                if signed_error > 0
                else "underestimate"
                if signed_error < 0
                else "exact"
            ),
        })

    return output


# ------------------------------------------------------------
# 2. Overall error direction
# ------------------------------------------------------------

def over_under_summary(rows):
    output = []

    grouped = defaultdict(list)

    for row in rows:
        grouped[row["mode"]].append(row)

    grouped["ALL"] = rows

    for mode, data in grouped.items():
        signed = [
            safe_float(r["O46_signed_error"])
            for r in data
        ]

        signed = [x for x in signed if x is not None]

        if not signed:
            continue

        positive = sum(x > 0 for x in signed)
        negative = sum(x < 0 for x in signed)
        exact = sum(x == 0 for x in signed)

        output.append({
            "mode": mode,
            "cases": len(signed),
            "mean_signed_error": mean(signed),
            "median_signed_error": statistics.median(signed),
            "overestimated_cases": positive,
            "overestimated_pct": 100 * positive / len(signed),
            "underestimated_cases": negative,
            "underestimated_pct": 100 * negative / len(signed),
            "exact_cases": exact,
            "exact_pct": 100 * exact / len(signed),
        })

    return output


# ------------------------------------------------------------
# 3. Error by context
# ------------------------------------------------------------

def error_by_context(rows):
    groups = defaultdict(list)

    for row in rows:
        groups[(row["mode"], row["context"])].append(row)

    output = []

    for (mode, context), data in sorted(groups.items()):
        errors = [
            abs(safe_float(r["O46_signed_error"]))
            for r in data
        ]

        signed = [
            safe_float(r["O46_signed_error"])
            for r in data
        ]

        output.append({
            "mode": mode,
            "context": context,
            "cases": len(data),
            "MAE": mean(errors),
            "RMSE": rmse(signed),
            "max_error": max(errors),
            "mean_signed_error": mean(signed),
            "overestimate_pct": (
                100 * sum(x > 0 for x in signed) / len(signed)
            ),
            "underestimate_pct": (
                100 * sum(x < 0 for x in signed) / len(signed)
            ),
        })

    return output


# ------------------------------------------------------------
# 4. Error by PVS
# ------------------------------------------------------------

def error_by_pvs(rows):
    groups = defaultdict(list)

    for row in rows:
        groups[(row["mode"], row["pvs_id"])].append(row)

    output = []

    for (mode, pvs_id), data in groups.items():
        errors = [
            abs(safe_float(r["O46_signed_error"]))
            for r in data
        ]

        signed = [
            safe_float(r["O46_signed_error"])
            for r in data
        ]

        generated = [
            safe_float(r["O46_generated"])
            for r in data
        ]

        reference = [
            safe_float(r["O46_reference"])
            for r in data
        ]

        output.append({
            "mode": mode,
            "pvs_id": pvs_id,
            "cases": len(data),
            "MAE": mean(errors),
            "RMSE": rmse(signed),
            "max_error": max(errors),
            "mean_generated": mean(generated),
            "mean_reference": mean(reference),
            "mean_signed_error": mean(signed),
            "overestimate_pct": (
                100 * sum(x > 0 for x in signed) / len(signed)
            ),
            "underestimate_pct": (
                100 * sum(x < 0 for x in signed) / len(signed)
            ),
        })

    return sorted(
        output,
        key=lambda x: x["MAE"],
        reverse=True
    )


# ------------------------------------------------------------
# 5. Worst individual cases
# ------------------------------------------------------------

def worst_cases(rows, n=100):
    output = sorted(
        rows,
        key=lambda x: abs(
            safe_float(x["O46_signed_error"]) or 0
        ),
        reverse=True
    )

    result = []

    for rank, row in enumerate(output[:n], 1):
        result.append({
            "rank": rank,
            **row,
        })

    return result


# ------------------------------------------------------------
# 6. Error distribution buckets
# ------------------------------------------------------------

def error_distribution(rows):
    buckets = [
        ("0.000-0.010", 0.000, 0.010),
        ("0.010-0.025", 0.010, 0.025),
        ("0.025-0.050", 0.025, 0.050),
        ("0.050-0.100", 0.050, 0.100),
        ("0.100-0.150", 0.100, 0.150),
        ("0.150-0.200", 0.150, 0.200),
        ("0.200+", 0.200, float("inf")),
    ]

    output = []

    grouped = defaultdict(list)

    for row in rows:
        grouped[row["mode"]].append(row)

    grouped["ALL"] = rows

    for mode, data in grouped.items():

        errors = [
            abs(safe_float(r["O46_signed_error"]))
            for r in data
        ]

        for label, low, high in buckets:
            count = sum(
                low <= e < high
                for e in errors
            )

            output.append({
                "mode": mode,
                "error_range": label,
                "cases": count,
                "percentage": (
                    100 * count / len(errors)
                    if errors else 0
                ),
            })

    return output


# ------------------------------------------------------------
# 7. Cross-mode consistency
# ------------------------------------------------------------

def cross_mode_analysis(rows):
    by_pvs = defaultdict(dict)

    for row in rows:
        key = (row["pvs_id"], row["context"])
        by_pvs[key][row["mode"]] = row

    output = []

    for (pvs_id, context), modes in by_pvs.items():

        if not all(m in modes for m in MODES):
            continue

        generated = [
            safe_float(modes[m]["O46_generated"])
            for m in MODES
        ]

        reference = [
            safe_float(modes[m]["O46_reference"])
            for m in MODES
        ]

        errors = [
            safe_float(modes[m]["O46_signed_error"])
            for m in MODES
        ]

        output.append({
            "pvs_id": pvs_id,
            "context": context,

            "mode0_O46": generated[0],
            "mode1_O46": generated[1],
            "mode2_O46": generated[2],
            "mode3_O46": generated[3],

            "mode0_error": errors[0],
            "mode1_error": errors[1],
            "mode2_error": errors[2],
            "mode3_error": errors[3],

            "generated_min": min(generated),
            "generated_max": max(generated),
            "generated_range": max(generated) - min(generated),

            "reference_min": min(reference),
            "reference_max": max(reference),
            "reference_range": max(reference) - min(reference),
        })

    return output


# ------------------------------------------------------------
# 8. MOS relationship
# ------------------------------------------------------------

def load_mos_comparisons():
    rows = []

    for mode in MODES:
        path = RESULTS / f"{mode}_mos_comparison.csv"

        if not path.exists():
            continue

        for row in read_csv(path):
            row["mode"] = mode

            row["O46"] = safe_float(row.get("O46"))
            row["MOS"] = safe_float(row.get("MOS"))

            if row["O46"] is not None and row["MOS"] is not None:
                rows.append(row)

    return rows


def mos_analysis(rows):
    output = []

    grouped = defaultdict(list)

    for row in rows:
        grouped[row["mode"]].append(row)

    grouped["ALL"] = rows

    for mode, data in grouped.items():

        xs = [r["O46"] for r in data]
        ys = [r["MOS"] for r in data]

        errors = [
            abs(x - y)
            for x, y in zip(xs, ys)
        ]

        signed = [
            x - y
            for x, y in zip(xs, ys)
        ]

        output.append({
            "mode": mode,
            "cases": len(data),
            "MAE": mean(errors),
            "RMSE": rmse(signed),
            "Pearson": pearson(xs, ys),
            "mean_O46": mean(xs),
            "mean_MOS": mean(ys),
            "mean_signed_error": mean(signed),
            "overestimate_pct": (
                100 * sum(x > 0 for x in signed) / len(signed)
                if signed else None
            ),
            "underestimate_pct": (
                100 * sum(x < 0 for x in signed) / len(signed)
                if signed else None
            ),
        })

    return output


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    print("=" * 70)
    print("O46 ERROR ANALYSIS")
    print("=" * 70)

    ANALYSIS.mkdir(parents=True, exist_ok=True)

    detailed = load_all_detailed()

    print(f"Loaded validation rows: {len(detailed)}")

    o46_rows = build_o46_error_dataset(detailed)

    print(f"Valid O46 rows: {len(o46_rows)}")

    # 1
    write_csv(
        ANALYSIS / "o46_error_dataset.csv",
        o46_rows
    )

    # 2
    write_csv(
        ANALYSIS / "o46_over_under_summary.csv",
        over_under_summary(o46_rows)
    )

    # 3
    write_csv(
        ANALYSIS / "o46_error_by_context.csv",
        error_by_context(o46_rows)
    )

    # 4
    write_csv(
        ANALYSIS / "o46_error_by_pvs.csv",
        error_by_pvs(o46_rows)
    )

    # 5
    write_csv(
        ANALYSIS / "o46_worst_cases.csv",
        worst_cases(o46_rows, 100)
    )

    # 6
    write_csv(
        ANALYSIS / "o46_error_distribution.csv",
        error_distribution(o46_rows)
    )

    # 7
    write_csv(
        ANALYSIS / "o46_cross_mode.csv",
        cross_mode_analysis(o46_rows)
    )

    # 8
    mos_rows = load_mos_comparisons()

    write_csv(
        ANALYSIS / "o46_mos_analysis.csv",
        mos_analysis(mos_rows)
    )

    print()
    print("=" * 70)
    print("O46 ANALYSIS COMPLETE")
    print("=" * 70)
    print()
    print(f"Reports: {ANALYSIS}")
    print()
    print("Generated:")
    print("  o46_error_dataset.csv")
    print("  o46_over_under_summary.csv")
    print("  o46_error_by_context.csv")
    print("  o46_error_by_pvs.csv")
    print("  o46_worst_cases.csv")
    print("  o46_error_distribution.csv")
    print("  o46_cross_mode.csv")
    print("  o46_mos_analysis.csv")


if __name__ == "__main__":
    main()