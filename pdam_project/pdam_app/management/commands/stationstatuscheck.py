import csv
from django.core.management.base import BaseCommand
from pdam_app.models import RawMessagemodel
from django.db.models import Max
from django.db import connection
from datetime import datetime, timedelta
import time
import pytz
from django.utils import timezone

class Command(BaseCommand):
    help = 'Cek last time from each station'

    
    def handle(self, *args, **kwargs):
        start = time.time()
        datas = RawMessagemodel.objects.values("station__topic").annotate(last_time=Max('time'))
        
        for data in datas:
            # check latest time
            # Get the current time in the Asia/Jakarta timezone
            now = datetime.now(pytz.timezone('Asia/Jakarta'))

            # Assume data['last_time'] is a timezone-aware datetime object
            last_time = data['last_time']

            # Convert last_time to local timezone if it isn't already
            last_time_local = timezone.localtime(last_time)

            # Calculate the time difference
            time_difference = (now - last_time_local).total_seconds()
            if (time_difference/3600)>1.5:
                print("hei it is offline", data, last_time_local)