from __future__ import annotations
from datetime import datetime
SNAPSHOT_SCHEDULE_MIN=[10,30,60,180,360,720,1440,2880,10080,20160,43200]
def due_snapshots(published_at: datetime, now: datetime, taken: list[int]) -> list[int]:
    age=max(0,(now-published_at).total_seconds()/60)
    return [slot for slot in SNAPSHOT_SCHEDULE_MIN if slot<=age and slot not in taken]
