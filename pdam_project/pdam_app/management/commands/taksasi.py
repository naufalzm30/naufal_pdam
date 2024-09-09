
from django.core.management.base import BaseCommand
from pdam_app.models import (StationModel, SensorDataModel, ThresholdSensorModel)
import pytz
from django.utils import timezone
import pickle
import pandas as pd
import time
from datetime import timedelta

import warnings 

warnings.filterwarnings("ignore")

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
        try:

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

                minutes_data = [data.time.minute for data in datas]

                # If not enough data points (less than 12 minutes in an hour)
                if len(minutes_data) < 12:
                    # Minutes we expect to have data for
                    expected_minutes = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
                    # Find missing minutes
                    missing_minutes = [minute for minute in expected_minutes if minute not in minutes_data]

                    # Handle missing data points
                    for miss in missing_minutes:
                        # Get 36 previous data entries
                        lagged_data = SensorDataModel.objects.filter(
                            station=station,
                            status=0
                        ).order_by('-time')[:36]  # Get the latest 36 records

                        if lagged_data.exists():
                            # Extract data from lagged_data
                            modch5_data = list(lagged_data.values_list('modCH5', flat=True))
                            predicted_value = self.predict_missing_data('lr', station.topic, modch5_data)
                            
                            # Get the first data point to use as a template
                            data = lagged_data.first()
                            
                            # Create the missing data entry
                            missing_time = one_hour_before.replace(minute=miss, second=0, microsecond=0)
                            try:
                                SensorDataModel.objects.create(
                                    station=station,
                                    created_at=timezone.localtime(),
                                    time=missing_time,
                                    CH1=data.CH1,
                                    CH2=data.CH2,
                                    CH3=data.CH3,
                                    CH4=data.CH4,
                                    CH5=data.CH5,
                                    CH6=data.CH6,
                                    battery=data.battery,
                                    temperature=data.temperature,
                                    itter_flow=data.itter_flow,
                                    saved_data=data.saved_data,
                                    modCH5=predicted_value,
                                    modCH6=data.modCH6,
                                    status=3  # Status for missing data prediction
                                )
                            except Exception as e:
                                print(e)

                # Handle threshold violations
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
                    day = day_choice.get(one_hour_before.strftime("%A"))  # Get day as string
                    thresholds = ThresholdSensorModel.objects.filter(
                        station=station, 
                        day=day,
                        hour=one_hour_before.hour,
                        minute=one_hour_before.minute
                    ).first()

                    if thresholds and (data.modCH5 < thresholds.min or data.modCH5 > thresholds.max):
                        # Get 36 previous data entries for prediction
                        lagged_data = SensorDataModel.objects.filter(
                            station=station,
                            status=0
                        ).order_by('-time')[:36]

                        if lagged_data.exists():
                            # Extract data from lagged_data
                            modch5_data = list(lagged_data.values_list('modCH5', flat=True))
                            print(modch5_data)
                            predicted_value = self.predict_missing_data('lr', station.topic, modch5_data)

                            # Create the corrected data 
                            try:
                                SensorDataModel.objects.create(
                                    station=station,
                                    created_at=timezone.localtime(),
                                    time=data.time,
                                    CH1=data.CH1,
                                    CH2=data.CH2,
                                    CH3=data.CH3,
                                    CH4=data.CH4,
                                    CH5=data.CH5,
                                    CH6=data.CH6,
                                    battery=data.battery,
                                    temperature=data.temperature,
                                    itter_flow=data.itter_flow,
                                    saved_data=data.saved_data,
                                    modCH5=predicted_value,
                                    modCH6=data.modCH6,
                                    status=3  # Status for threshold violation correction
                                )
                            except Exception as e:
                                print(e)

                    '''
                    status 3 lr
                    status 4 rf
                    status 5 arima
                    '''


        except Exception as e:
            print(e)


