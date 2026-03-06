from datetime import datetime, timedelta
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services import sla

samples = [
    datetime(2025, 3, 14, 8, 0),   # before business
    datetime(2025, 3, 14, 10, 0),  # during business
    datetime(2025, 3, 14, 16, 30), # near end of business
    datetime(2025, 3, 14, 18, 0),  # after business
    datetime(2025, 3, 15, 12, 0),  # weekend
]

print("Testing _add_business_minutes")
for dt in samples:
    for mins in (60, 240, 480, 1440):
        result = sla._add_business_minutes(dt, mins)
        print(f"start={dt} add={mins} -> {result}")
    print("---")
