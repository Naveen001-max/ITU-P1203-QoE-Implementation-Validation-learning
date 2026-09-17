import json
from itu_p1203 import P1203Pa

with open("examples/p1203_2_20sec.json", "r", encoding="utf-8") as f:
    data = json.load(f)

segments = data["I11"]["segments"]

model = P1203Pa(segments)

result = model.calculate()

print("ITU-T P.1203.2 - Audio Quality Module")
print("=" * 50)

print("Number of audio segments:", len(segments))
print("Total duration:",
      sum(s["duration"] for s in segments),
      "seconds")

print("\nO.21 per-second scores:")
print("-" * 50)

for second, score in enumerate(result["audio"]["O21"], start=1):
    print(f"t={second:02d}s    O.21={score:.6f}")