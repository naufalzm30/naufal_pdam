
from django.core.management.base import BaseCommand
from pdam_app.models import (StationModel, SensorDataModel, ThresholdSensorModel)
import pytz
from django.utils import timezone
import pickle
import pandas as pd
import time
from datetime import timedelta

class Command(BaseCommand):
    help = 'Taksasi'

    # Function to predict missing data using array format lagged data
    def predict_missing_data(self,model_type, station_topic, lagged_data):
        """
        Predict missing data using the specified model type.
        
        Parameters:
        - model_type: Type of model ('lr' for Linear Regression, 'rf' for Random Forest, 'arima' for ARIMA).
        - station_topic: Topic of the station to load the correct model.
        - lagged_data: A list containing 36 Flow values for the previous 3 hours (for 'lr' and 'rf').
        
        Returns:
        - prediction: Predicted value for the missing time.
        """
        # Determine model filename
        if model_type == 'lr':
            model_filename = f'linear_regression_model_{station_topic.replace("/", "_")}.pkl'
        elif model_type == 'rf':
            model_filename = f'random_forest_model_{station_topic.replace("/", "_")}.pkl'
        elif model_type == 'arima':
            model_filename = f'arima_model_{station_topic.replace("/", "_")}.pkl'
        else:
            raise ValueError("Invalid model type. Choose 'lr', 'rf', or 'arima'.")

        # Load the model
        path = "pdam_app/management/commands/pickle-model-v2/"
        with open(path+model_filename, 'rb') as model_file:
            model_file = model_file
            model = pickle.load(model_file)

        if model_type in ['lr', 'rf']:
            # Convert lagged data to a DataFrame with the correct column names
            input_data = pd.DataFrame([lagged_data], columns=[f'Flow_lag_{i}' for i in range(1, 37)])
            input_data.fillna(0, inplace=True)  # Replace NaNs in input data

            # Predict missing value
            prediction = model.predict(input_data)
        elif model_type == 'arima':
            # ARIMA requires the entire time series to predict the next value
            prediction = model.forecast(steps=1)

        return prediction


    def handle(self, *args, **kwargs):
        stations = StationModel.objects.all()

        for station in stations:
            # Get the current time
            current_time = timezone.localtime()

            # Subtract one hour from the current time
            one_hour_before = current_time - timedelta(hours=1)

            # Filter SensorDataModel for the station, status 0, and time being one hour before
            datas = SensorDataModel.objects.filter(
                station=station,
                status=0,
                time__hour=one_hour_before.hour,
                time__date=one_hour_before.date()
            )
            minutes_data=[]
            for data in datas:
                minutes_data = [data.time.minute for data in datas] 
            
            # taksasi data kosong
            if len(minutes_data)<12:
                # simpan ke database telegram notif karena data kosong, lakukan taksasi
                minutes =[0,5,10,15,20,25,30,35,40,45,50,55]
                # Cari menit yang ada di `minutes` tapi tidak ada di `minutes_data`
                missing_minutes = [minute for minute in minutes if minute not in minutes_data]
                
                # create table telegram type missing is_Sent false

                for miss in missing_minutes:
                    # 10
                    # get 36 data before
                    lagged_data = SensorDataModel.objects.filter(
                        station=station,
                        status=0
                    ).order_by('-time')[:36]  # Ambil 36 data terbaru

                    # Ekstrak data modCH5 dan modCH6 ke dalam array terpisah
                    modch5_data = list(lagged_data.values_list('modCH5', flat=True))
                    modch6_data = list(lagged_data.values_list('modCH6', flat=True))

                    predicted_value = self.predict_missing_data('lr', station.topic, modch5_data)
                    missing_time = one_hour_before.replace(minute=miss, second=0, microsecond=0)
                    SensorDataModel.objects.create(
                        station=station,
                        created_at=timezone.localtime(),
                        time = missing_time,    
                        CH1=data.CH1,
                        CH2=data.CH2,
                        CH3=data.CH3,
                        CH4=data.CH4,
                        CH5=data.CH5,
                        CH6=data.CH6,
                        battery= data.battery,
                        temperature= data.temperature,
                        itter_flow = data.itter_flow,
                        saved_data=data.saved_data,
                        modCH5=predicted_value,
                        modCH6=data.modCH6,
                        status=3,
                        station=station  
                    )

            # taksasi kalau data threshold
            for data in datas:
                day_choice = {
                    "Monday": 1,
                    "Tuesday": 2,
                    "Wednesday": 3,
                    "Thursday": 4,
                    "Friday": 5,
                    "Saturday": 6,
                    "Sunday": 7
                }
                day = day_choice.get(one_hour_before.day)         
                thresholds = ThresholdSensorModel.objects.get(station=station, day=day,hour=one_hour_before.hour, minute=one_hour_before.minute)
                
                if data.modCH5<thresholds.min or data.modCH5>thresholds.max:
                    lagged_data = SensorDataModel.objects.filter(
                        station=station,
                        status=0
                    ).order_by('-time')[:36]  # Ambil 36 data terbaru

                    # Ekstrak data modCH5 dan modCH6 ke dalam array terpisah
                    modch5_data = list(lagged_data.values_list('modCH5', flat=True))
                    predicted_value = self.predict_missing_data('lr', station.topic, modch5_data)
                    SensorDataModel.objects.create(
                        station=station,
                        created_at=timezone.localtime(),
                        time = data.time,    
                        CH1=data.CH1,
                        CH2=data.CH2,
                        CH3=data.CH3,
                        CH4=data.CH4,
                        CH5=data.CH5,
                        CH6=data.CH6,
                        battery= data.battery,
                        temperature= data.temperature,
                        itter_flow = data.itter_flow,
                        saved_data=data.saved_data,
                        modCH5=predicted_value,
                        modCH6=data.modCH6,
                        status=3, #3 untuk takasasi threshold linear regression
                        station=station  
                    )
               
            '''
            status 3 lr
            status 4 rf
            status 5 arima
            '''

   


