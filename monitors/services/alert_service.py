import json
from datetime import datetime, timezone
from redis_client.client import get_redis_client


BACKOFF_LEVELS = {
    '1': {'delay': 30,  'severity': 'URGENT'},
    '2': {'delay': 90,  'severity': 'CRITICAL'},
}


def fire_alert(device_id):
    """
    Fires the first alert when a device goes down.
    Sets monitor status to down and schedules backoff alerts.
    """
    r = get_redis_client()

    data = r.hgetall(f'monitor:{device_id}')
    if not data:
        return

    now = datetime.now(timezone.utc).isoformat()

    # Update monitor status to down
    r.hset(f'monitor:{device_id}', mapping={
        'status':     'down',
        'updated_at': now,
    })

    # Fire Alert 1 — Warning
    alert = {
        'ALERT':    f'Device {device_id} is down!',
        'severity': 'WARNING',
        'email':    data.get('alert_email'),
        'time':     now,
    }
    print(json.dumps(alert))

    # Schedule Alert 2 — set a backoff key with 30s TTL
    r.set(f'backoff:{device_id}:1', '1', ex=30)


def fire_backoff_alert(device_id, level):
    """
    Fires escalating alerts after the initial one.
    level 1 → URGENT  (fires 30s after first alert)
    level 2 → CRITICAL (fires 90s after second alert)
    """
    r = get_redis_client()

    data = r.hgetall(f'monitor:{device_id}')
    if not data:
        return

    # If device recovered, stop escalating
    if data.get('status') != 'down':
        return

    now = datetime.now(timezone.utc).isoformat()
    level_str = str(level)
    config = BACKOFF_LEVELS.get(level_str)

    if not config:
        return

    # Fire the escalated alert
    alert = {
        'ALERT':    f'Device {device_id} is still down!',
        'severity': config['severity'],
        'email':    data.get('alert_email'),
        'time':     now,
    }
    print(json.dumps(alert))

    # Schedule next level if it exists
    next_level = str(level + 1)
    if next_level in BACKOFF_LEVELS:
        next_delay = BACKOFF_LEVELS[next_level]['delay']
        r.set(f'backoff:{device_id}:{next_level}', '1', ex=next_delay)
