from datetime import datetime, timezone


def epoch_timestamp_to_iso_format(timestamp_epoch: int) -> str:
    return datetime.fromtimestamp(timestamp_epoch, tz=timezone.utc).isoformat()
