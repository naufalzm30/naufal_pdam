
from django.core.management.base import BaseCommand
from pdam_app.models import (StationModel)

import pytz
from tqdm import tqdm
import pandas as pd

class Command(BaseCommand):
    help = 'Create dummy threshold data for 7 days'
    file_path = "pdam_app/management/commands/csv/pdam_app_station.csv"
    def handle(self, *args, **kwargs):
        df = pd.read_csv(self.file_path)
        try:
            for i in range(len(df)):
                topic = df.iloc[i]['topic_MQTT']
                station = StationModel.objects.get(topic=topic)
                station.longitude = df.iloc[i]['longitude']
                station.latitude = df.iloc[i]['latitude']
                station.station_name = df.iloc[i]['station_name']
                station.location = df.iloc[i]['location']

                station.save()
    
        except Exception as e:
            print("error",e)
