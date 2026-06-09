from datetime import datetime, timezone
from redis_client.client import get_redis_client


def register_monitor(device_id, timeout, alert_email):
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

    # Update status to active
    r.hset(f'monitor:{device_id}', mapping={
        'status':     'active',
        'updated_at': now,
    })

    # Clear any backoff keys
    r.delete(f'backoff:{device_id}')

    return {
        'id':         device_id,
        'status':     'active',
        'message':    'Heartbeat received — timer reset',
        'updated_at': now,
    }, None


def pause_monitor(device_id):
    """
    Pauses a monitor by removing the TTL key.
    Redis PERSIST removes the expiry — key stays forever until deleted.
    No alerts will fire while paused.
    """
    r = get_redis_client()

    data = r.hgetall(f'monitor:{device_id}')
    if not data:
        return None, 'not_found'

    current_status = data.get('status')

    if current_status == 'down':
        return None, 'down'

    if current_status == 'paused':
        return None, 'already_paused'

    now = datetime.now(timezone.utc).isoformat()

    # Remove the TTL — timer stops completely
    r.persist(f'ttl:{device_id}')

    # Update status to paused
    r.hset(f'monitor:{device_id}', mapping={
        'status':     'paused',
        'updated_at': now,
    })

    return {
        'id':         device_id,
        'status':     'paused',
        'message':    'Monitor paused — no alerts will fire',
        'updated_at': now,
    }, None


def get_monitor(device_id):
    r = get_redis_client()
    data = r.hgetall(f'monitor:{device_id}')
    if not data:
        return None
    return data


def get_all_monitors():
    r = get_redis_client()
    keys = r.keys('monitor:*')
    monitors = []
    for key in keys:
        data = r.hgetall(key)
        if data:
            monitors.append(data)
    return monitors

def recover_monitor(device_id):
    """
    Recovers a down monitor back to active state.
    Resets the timer and clears all backoff keys.
    Only works when monitor status is down.
    """
    r = get_redis_client()

    data = r.hgetall(f'monitor:{device_id}')
    if not data:
        return None, 'not_found'

    current_status = data.get('status')

    if current_status != 'down':
        return None, 'not_down'

    now = datetime.now(timezone.utc).isoformat()
    timeout = int(data.get('timeout', 60))

    # Restart the TTL key
    r.set(f'ttl:{device_id}', '1', ex=timeout)

    # Clear all backoff keys
    r.delete(f'backoff:{device_id}:1')
    r.delete(f'backoff:{device_id}:2')

    # Reset status to active
    r.hset(f'monitor:{device_id}', mapping={
        'status':     'active',
        'updated_at': now,
    })

    return {
        'id':         device_id,
        'status':     'active',
        'message':    f'Monitor {device_id} recovered — timer restarted',
        'updated_at': now,
    }, None


def delete_monitor(device_id):
    """
    Deletes a monitor and all its associated Redis keys.
    """
    r = get_redis_client()

    if not r.exists(f'monitor:{device_id}'):
        return None, 'not_found'

    r.delete(f'monitor:{device_id}')
    r.delete(f'ttl:{device_id}')
    r.delete(f'backoff:{device_id}:1')
    r.delete(f'backoff:{device_id}:2')

    return {'message': f'Monitor {device_id} deleted successfully'}, None