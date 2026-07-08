"""Manual calibration harness — prints the CO-PO matrix for a set of sample COs so
we can eyeball whether the thresholds and weights produce sensible levels.

Run:  python -m tests.calibrate     (from the backend/ directory)
"""
from __future__ import annotations

from app.engine.csas import score_co

SAMPLE_COS = [
    "Apply data structures and algorithms to solve computational problems efficiently.",
    "Analyze the time complexity and space complexity of algorithms.",
    "Design and develop a software system using modern engineering tools.",
    "Understand the ethical and professional responsibilities of an engineer.",
    "Evaluate the environmental impact and sustainability of engineering solutions.",
    "Communicate technical results effectively through reports and presentations.",
    "Work effectively as a member of a multidisciplinary team on a project.",
    "Define the basic concepts and terminology of database management systems.",
]

POS = [f"PO{i}" for i in range(1, 13)]


def main() -> None:
    header = "CO".ljust(6) + "Bloom  " + "".join(p.rjust(5) for p in POS)
    print(header)
    print("-" * len(header))
    for i, co in enumerate(SAMPLE_COS, 1):
        row = score_co(co)
        levels = {c.po: c.level for c in row.cells}
        line = f"CO{i}".ljust(6) + str(row.bloom_level).ljust(7) + \
            "".join(str(levels[p]).rjust(5) for p in POS)
        print(line)

    print("\n--- Detail for CO3 (design/develop) ---")
    for c in score_co(SAMPLE_COS[2]).cells:
        if c.level > 0:
            print(f"  {c.po} L{c.level}  raw={c.raw:.3f} sig={c.semantic:.3f} "
                  f"lam={c.lexical:.3f} gate={c.gate:.3f}  {[m['term'] for m in c.matched_terms]}")


if __name__ == "__main__":
    main()
