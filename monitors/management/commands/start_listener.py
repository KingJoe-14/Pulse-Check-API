from django.core.management.base import BaseCommand
from redis_client.client import get_redis_client
from monitors.services.alert_service import fire_alert, fire_backoff_alert


class Command(BaseCommand):
    help = 'Listens for Redis keyspace expiry events and fires alerts'

    def handle(self, *args, **options):
        r = get_redis_client()
        pubsub = r.pubsub()

        pubsub.psubscribe('__keyevent@0__:expired')

        self.stdout.write(self.style.SUCCESS(
            'Keyspace listener started — waiting for expiry events...'
        ))

        for message in pubsub.listen():
            if message['type'] != 'pmessage':
                continue

            expired_key = message['data']
            self.stdout.write(f'Key expired: {expired_key}')

            # ttl:{device_id} expired → device missed heartbeat
            if expired_key.startswith('ttl:'):
                device_id = expired_key[len('ttl:'):]
                self.stdout.write(self.style.WARNING(
                    f'Monitor {device_id} missed heartbeat — firing alert'
                ))
                fire_alert(device_id)

            # backoff:{device_id}:{level} expired → escalate alert
            elif expired_key.startswith('backoff:'):
                parts = expired_key.split(':')
                if len(parts) == 3:
                    device_id = parts[1]
                    level     = int(parts[2])
                    self.stdout.write(self.style.WARNING(
                        f'Firing backoff level {level} alert for {device_id}'
                    ))
                    fire_backoff_alert(device_id, level)
