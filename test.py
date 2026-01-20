from datetime import datetime, timezone

timestr = "2026-01-08T19:08"

# Parse the string as a UTC datetime
dt = datetime.strptime(timestr, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)

# Convert to seconds since epoch
epoch_seconds = int(dt.timestamp())

print(epoch_seconds)
