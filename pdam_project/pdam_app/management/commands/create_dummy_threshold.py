
from django.core.management.base import BaseCommand
from pdam_app.models import (StationModel, ThresholdSensorModel)

import pytz
from tqdm import tqdm

class Command(BaseCommand):
    help = 'Create dummy threshold data for 7 days'

    def handle(self, *args, **kwargs):
        stations = StationModel.objects.all()
        days_of_week = range(1, 8)  # Assuming 1 = Sunday, 2 = Monday, ..., 7 = Saturday

        for day in days_of_week:
            for hour in range(0, 24):
                for minute in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]:
                    for station in stations:
                        ThresholdSensorModel.objects.create(
                            station=station,
                            hour=hour,
                            minute=minute,
                            day=day,  # Set the current day of the week
                            min=200,
                            max=1000
                        )
