from django.core.management.base import BaseCommand
from pdam_app.models import StationModel
import uuid
from collections import Counter

class Command(BaseCommand):
    help = 'Remove duplicate station_serial_id values by generating new UUIDs'

    def handle(self, *args, **kwargs):
        # Fetch all station_serial_id values
        all_uuids = StationModel.objects.values_list('station_serial_id', flat=True)
        
        # Count occurrences of each UUID
        uuid_counts = Counter(all_uuids)

        # Identify duplicates
        duplicate_uuids = [uuid for uuid, count in uuid_counts.items() if count > 1]

        if not duplicate_uuids:
            self.stdout.write(self.style.SUCCESS('No duplicate UUIDs found.'))
            return

        self.stdout.write(self.style.WARNING('Found duplicate UUIDs:'))

        for dupe_uuid in duplicate_uuids:
            self.stdout.write(f'Processing duplicates for UUID: {dupe_uuid}')
            # Fetch records with this duplicate UUID
            records = StationModel.objects.filter(station_serial_id=dupe_uuid)

            # Generate new UUIDs and save
            for record in records:
                new_uuid = uuid.uuid4()
                record.station_serial_id = new_uuid
                record.save()
                self.stdout.write(f'Updated record {record.id} with new UUID: {new_uuid}')

        self.stdout.write(self.style.SUCCESS('Completed updating duplicate UUIDs.'))
