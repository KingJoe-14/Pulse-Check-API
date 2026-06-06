import json
from datetime import datetime, timezone
from redis_client.client import get_redis_client

def register_monitor(device_id, timeout, alert_email):
    """
    Registers a new monitor in Redis.
    - monitor:{id} → hash storing device info and status
    - ttl:{id}     → expiring key that triggers the alert
    """
    r = get_redis_client()

    # Check if monitor already exists
    if r.exists(f'monitor:{device_id}'):
        return None, 'Monitor with this ID already exists'

    now = datetime.now(timezone.utc).isoformat()

    # Store monitor data as a Redis hash
    r.hset(f'monitor:{device_id}', mapping={
        'id':          device_id,
        'timeout':     timeout,
        'alert_email': alert_email,
        'status':      'active',
        'created_at':  now,
        'updated_at':  now,
    })

    # Set the expiring TTL key — this is what Redis watches
    r.set(f'ttl:{device_id}', '1', ex=timeout)

    return {
        'id':          device_id,
        'timeout':     timeout,
        'alert_email': alert_email,
        'status':      'active',
        'created_at':  now,
    }, None


def get_monitor(device_id):
    """Fetch a single monitor by ID."""
    r = get_redis_client()
    data = r.hgetall(f'monitor:{device_id}')
    if not data:
        return None
    return data


def get_all_monitors():
    """Fetch all registered monitors."""
    r = get_redis_client()
    keys = r.keys('monitor:*')
    monitors = []
    for key in keys:
        data = r.hgetall(key)
        if data:
            monitors.append(data)
    return monitors
