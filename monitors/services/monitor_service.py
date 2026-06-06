from datetime import datetime, timezone
from redis_client.client import get_redis_client


def register_monitor(device_id, timeout, alert_email):
    """
    Registers a new monitor in Redis.
    - monitor:{id} → hash storing device info and status
    - ttl:{id}     → expiring key that triggers the alert
    """
    r = get_redis_client()

    if r.exists(f'monitor:{device_id}'):
        return None, 'Monitor with this ID already exists'

    now = datetime.now(timezone.utc).isoformat()

    r.hset(f'monitor:{device_id}', mapping={
        'id':          device_id,
        'timeout':     timeout,
        'alert_email': alert_email,
        'status':      'active',
        'created_at':  now,
        'updated_at':  now,
    })

    r.set(f'ttl:{device_id}', '1', ex=int(timeout))

    return {
        'id':          device_id,
        'timeout':     int(timeout),
        'alert_email': alert_email,
        'status':      'active',
        'created_at':  now,
    }, None


def heartbeat_monitor(device_id):
    """
    Resets the countdown timer for a monitor.
    - If monitor does not exist → return error
    - If monitor is down → return error
    - If monitor is paused → unpause and restart timer
    - If monitor is active → reset timer
    """
    r = get_redis_client()

    data = r.hgetall(f'monitor:{device_id}')
    if not data:
        return None, 'not_found'

    current_status = data.get('status')
    timeout = int(data.get('timeout', 60))

    if current_status == 'down':
        return None, 'down'

    now = datetime.now(timezone.utc).isoformat()

    # Reset the TTL key (also unpauses if paused)
    r.set(f'ttl:{device_id}', '1', ex=timeout)

    # Update status to active and refresh updated_at
    r.hset(f'monitor:{device_id}', mapping={
        'status':     'active',
        'updated_at': now,
    })

    # Clear any backoff alert keys if they exist
    r.delete(f'backoff:{device_id}')

    return {
        'id':         device_id,
        'status':     'active',
        'message':    'Heartbeat received — timer reset',
        'updated_at': now,
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
