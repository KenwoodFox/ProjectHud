from datetime import datetime


def _to_local_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt


def time_ago(dt):
    if dt is None:
        return "Never updated"

    dt = _to_local_naive(dt)
    seconds = max(0, int((datetime.now() - dt).total_seconds()))

    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    return f"{int(seconds // 86400)}d ago"
