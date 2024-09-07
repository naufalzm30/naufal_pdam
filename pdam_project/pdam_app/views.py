from django.shortcuts import render
from .models import (SensorDataModel, StationModel, StationConfigurationModel,
                      ChannelModel, SensorTypeModel, MaintenanceRecordModel,
                      LoggerTypeModel, SensorTypeModel,ThresholdSensorModel,
                      PublishResendModel)
from .serializer import (StationSerializer, MaintenanceRecordSerializer, SensorDataSerializer,
                         LoggerTypeSerializer, SensorTypeSerializer, ChannelSerializer,
                         PublishResendSerializer
                         )
from .pagination import ItemPagination
from .form import SensorTypeForm

# rest_framework
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from django.db.models import Max,Prefetch
from django.db.models.functions import TruncHour
from django.conf import settings
from urllib.parse import quote
import csv
from io import StringIO
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db import transaction
from datetime import datetime, timedelta




def get_channel_by_id(data, id):
  for item in data:
    if item['id'] == id:
      return item["channel_label"]
  return None

def get_sensor_name_by_id(data, id):
  for item in data:
    if item['id'] == id:
      return item["sensor_name"], item["notation"], item["sensor_icon"]
  return None

def is_within_any_maintenance_interval(time_value, maintenance_records):
    """
    Function to check if the time_value is within any of the maintenance intervals.
    :param time_value: The time to check (datetime object).
    :param maintenance_records: Queryset of maintenance records for the station.
    :return: True if time_value is within any interval, else False.
    """
    for record in maintenance_records:
        if record.start_date <= time_value and (record.end_date is None or time_value <= record.end_date):
            return True
    return False

def auto_create_config(station):
    flow_meter = ["flowmeter","FLOWMETER","Flow Meter","flow meter","flow Meter","Flow meter"]
    totalizer = ["totalizer","Totalizer","TOTALIZER"]

    flow_meter = SensorTypeModel.objects.filter(sensor_name__in=flow_meter).first()
    totalizer = SensorTypeModel.objects.filter(sensor_name__in=totalizer).first()
    channel_5 = ChannelModel.objects.get(channel_label="CH5")
    channel_6 = ChannelModel.objects.get(channel_label="CH6")

    StationConfigurationModel.objects.get_or_create(station=station,
                                                    sensor_type =flow_meter,
                                                    channel=channel_5,
    )
    StationConfigurationModel.objects.get_or_create(station=station,
                                                    sensor_type =totalizer,
                                                    channel=channel_6,
    )


def create_confugurations():
    stations = StationModel.objects.all()
    for station in stations:
        auto_create_config(station=station)




# create_confugurations()
class PDAMDashboardView(APIView):
    serializer = StationSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            stations = StationModel.objects.all()
        else:
            stations = StationModel.objects.filter(balai=request.user.balai)

        sensors = SensorTypeModel.objects.filter(sensor_name__in=["Flow Meter", "Totalizer", "battery", "temperature"]).values("sensor_name", "notation", "sensor_icon")

        sensor_mapping = {sensor["sensor_name"]: sensor for sensor in sensors}
        
        responses = []
        for station in stations:
            last_sensor_data = SensorDataModel.objects.filter(station=station).order_by("-time").values().first()

            if last_sensor_data is None:
                responses.append({
                    "id": station.id,
                    "station_name": station.station_name,
                    "last_battery": None,
                    "last_temperature": None,
                    "station_serial_id": station.station_serial_id,
                    "topic": station.topic,
                    "location":station.location,
                    "observator_name": station.observator_name,
                    "phone": str(station.observator_phone),
                    "last_time": None,
                    "image": request.build_absolute_uri(station.image.url) if station.image else None,
                    "station_status": "station doesn't have any data",
                    "balai": station.balai.balai_name,
                    "longitude": station.longitude,
                    "latitude": station.latitude,
                    "max_flow":None,
                    "chart": {},
                    "last_data": []
                })
                continue

            latest_battery = last_sensor_data["battery"]
            latest_temperature = last_sensor_data["temperature"]

            since = timezone.localtime(last_sensor_data["time"])
            last_24_hours = since - timezone.timedelta(hours=24)

            # Check status
            station_status = "OK"
            if (timezone.now() - timezone.localtime(last_sensor_data["time"])).total_seconds() / 3600 > 1.3:
                station_status = "offline"
            
            if station.maintenance_status:
                station_status = "maintenance"

            # Check thresholds for Flow Meter (modCH5)
            try:
                threshold = ThresholdSensorModel.objects.get(station=station, day=since.weekday() + 1, hour=since.hour, minute=since.minute)
                if last_sensor_data["modCH5"] > threshold.max:
                    station_status = "Max Threshold"
                elif last_sensor_data["modCH5"] < threshold.min:
                    station_status = "Min Threshold"
            except ThresholdSensorModel.DoesNotExist:
                pass

            # Fetch hourly data for the last 24 hours
            hourly_data = SensorDataModel.objects.filter(
                station=station,
                time__gte=last_24_hours
            ).annotate(hour=TruncHour('time')).values("hour").annotate(latest_time=Max('time')).order_by('hour')
            
            sensor_data_dict = {"battery": [], "temperature": [], "Flow Meter": [], "Totalizer": []}
            
            for entry in hourly_data:
                latest_time = entry["latest_time"]
                sensor_data = SensorDataModel.objects.filter(station=station, time=latest_time).values().first()

                if sensor_data:
                    sensor_data_dict["battery"].append(sensor_data.get("battery"))
                    sensor_data_dict["temperature"].append(sensor_data.get("temperature"))
                    sensor_data_dict["Flow Meter"].append(sensor_data.get("modCH5"))
                    sensor_data_dict["Totalizer"].append(sensor_data.get("modCH6"))

            time_values = [timezone.localtime(entry["latest_time"]) for entry in hourly_data]
            # Calculate max flow from Flow Meter data
            flow_meter_data = sensor_data_dict.get("Flow Meter", [])
            max_flow = max(flow_meter_data) if flow_meter_data else None


            responses.append({
                "id": station.id,
                "station_name": station.station_name,
                "last_battery": latest_battery,
                "last_temperature": latest_temperature,
                "station_serial_id": station.station_serial_id,
                "topic": station.topic,
                "location":station.location,
                "observator_name": station.observator_name,
                "phone": str(station.observator_phone),
                "last_time": timezone.localtime(last_sensor_data["time"]),
                "image": request.build_absolute_uri(station.image.url) if station.image else None,
                "station_status": station_status,
                "maintenance": station.maintenance_status,
                "balai": station.balai.balai_name,
                "longitude": station.longitude,
                "latitude": station.latitude,
                "max_flow":max_flow,
                "chart": {
                    "time": time_values,
                    "sensor_data": [
                        {
                            "sensor_name": name,
                            "notation": sensor_mapping[name]["notation"],
                            "value": sensor_data_dict[name]
                        } for name in ["battery", "temperature", "Flow Meter", "Totalizer"]
                    ]
                },
                "last_data": [
                    {
                        "sensor_name": name,
                        "value": last_sensor_data.get(field),
                        "notation": sensor_mapping[name]["notation"],
                        "icon": request.build_absolute_uri(settings.MEDIA_URL + sensor_mapping[name]["sensor_icon"])
                    }
                    for name, field in zip(["battery", "temperature", "Flow Meter", "Totalizer"], ["battery", "temperature", "modCH5", "modCH6"])
                ]
            })

        return Response({"message": "success", "data": responses})

'''

# Create your views here.
@extend_schema(request=StationSerializer, responses={201: StationSerializer, 400: 'Error'})
class PDAMDashboardView(APIView):
    serializer = StationSerializer
    permission_classes = [IsAuthenticated]
    def get(self, request):
        # data = StationModel.objects.all().values()
        if request.user.is_staff:
            stations = StationModel.objects.all().prefetch_related(
                Prefetch(
                    'station_configurations',
                    queryset=StationConfigurationModel.objects.select_related('sensor_type', 'channel')
                )
            )
        else:
            stations = StationModel.objects.filter(balai=request.user.balai).prefetch_related(
                Prefetch(
                    'station_configurations',
                    queryset=StationConfigurationModel.objects.select_related('sensor_type', 'channel')
                )
            )
        
        channels = ChannelModel.objects.all().values()
        sensors = SensorTypeModel.objects.all().values()
            
        responses = []
        for station in stations:
            configurations = station.station_configurations.all()
            channel_labels = [get_channel_by_id(channels, entry.channel_id) for entry in configurations]
            sensor_type_names = [get_sensor_name_by_id(sensors, entry.sensor_type_id)[0] for entry in configurations]
            sensor_type_notations = [get_sensor_name_by_id(sensors, entry.sensor_type_id)[1] for entry in configurations]
            
            # Build the full URL using MEDIA_URL
            sensor_type_icons = [
                request.build_absolute_uri(settings.MEDIA_URL + f"{quote(get_sensor_name_by_id(sensors, entry.sensor_type_id)[2])}")
                for entry in configurations
            ]
            last_sensor_data = SensorDataModel.objects.filter(station=station).order_by("-time").values().first()

            # print(last_sensor_data, station.topic)
            # if theres no data in that station
            if last_sensor_data is None:
                responses.append({
                    "id": station.id,
                    "station_name": station.station_name,
                    "last_battery": None,
                    "last_temperature": None,
                    "station_serial_id":station.station_serial_id,
                    "topic": station.topic,
                    "observator_name": station.observator_name,
                    "phone": str(station.observator_phone),
                    "last_time": None,
                    "image":request.build_absolute_uri(station.image.url) if station.image else None,
                    "station_status":"station doesnt has any data",
                    "chart": {
            
                    },
                    "last_data": [

                    ]
                })
                continue

            latest_battery = last_sensor_data["battery"]
            latest_temperature = last_sensor_data["temperature"]

            since = timezone.localtime(last_sensor_data["time"])
            last_24_hours = since - timezone.timedelta(hours=24)

            # check status
            station_status = "OK"
            if (timezone.now()-timezone.localtime(last_sensor_data["time"])).total_seconds()/3600>1.3:
               station_status = "offline"
            
            if station.maintenance_status:
                  station_status = "maintenance"
            
            hour = since.hour
            minute = since.minute
            day_name = since.strftime('%A')
            name_choice = {
                "Monday": 1,
                "Tuesday": 2,
                "Wednesday": 3,
                "Thursday": 4,
                "Friday": 5,
                "Saturday": 6,
                "Sunday": 7
            }

            # Get the integer value corresponding to the day name
            day = name_choice.get(day_name)
            if station_status=="OK":
                try:
                    threshold = ThresholdSensorModel.objects.get(station=station, day=day, hour=hour, minute=minute)
                    min = threshold.min
                    max = threshold.max
                    if last_sensor_data["CH5"]>max:
                        station_status="Max Threshold"
                    elif last_sensor_data["CH5"]<min:
                        station_status="Min Threshold"
                except Exception as e:
                    print(e)
            
            # Fetch maintenance records for the station
            maintenance_records = MaintenanceRecordModel.objects.filter(station=station)

            hourly_data = SensorDataModel.objects.filter(
                station=station,
                time__gte=last_24_hours
            ).annotate(hour=TruncHour('time')).values("hour").annotate(latest_time=Max('time')).order_by('hour')
            
            sensor_data_dict = {}

            for entry in hourly_data:
                #hour = entry['hour']
                latest_time = entry['latest_time']
                
                # Fetch the sensor data for the latest time of the current hour
                sensor_data = SensorDataModel.objects.filter(
                    station=station,
                    time=latest_time
                ).values()  # Adjust fields as needed

                for item in sensor_data:
                    for i, (channel, sensor,notation) in enumerate(zip(channel_labels, sensor_type_names,sensor_type_notations)):
                        key = (sensor, channel)
                        if key not in sensor_data_dict:
                            sensor_data_dict[key] = {"sensor_name": sensor,"notation":notation,"channel": channel, "value": []}
                        
                        sensor_data_dict[key]["value"].append(item[channel])

            # Convert dictionary to list
            sensor_entry = list(sensor_data_dict.values())

            # Generate the 'time' array
            if configurations is not None:
                time_values = [timezone.localtime(entry['latest_time']) for entry in hourly_data]
            else :
                time_values = None
            # Generate the 'is_maintenance' array by checking each time value against maintenance records
            # is_maintenance = [
            #     is_within_any_maintenance_interval(time_value, maintenance_records)
            #     for time_value in time_values
            # ]

            responses.append({
                "id": station.id,
                "station_name": station.station_name,
                "last_battery": latest_battery,
                "last_temperature": latest_temperature,
                "station_serial_id":station.station_serial_id,
                "topic": station.topic,
                "observator_name": station.observator_name,
                "phone": str(station.observator_phone),
                "last_time": timezone.localtime(last_sensor_data["time"]),
                "image":request.build_absolute_uri(station.image.url) if station.image else None,
                "station_status":station_status,
                "maintenance":station.maintenance_status,
                "balai":station.balai.balai_name,
                "longitude":station.longitude,
                "latitude":station.latitude,
                "chart": {
                    "time": time_values,
                    # "is_maintenance":is_maintenance,
                    "sensor_data": sensor_entry
                },
                "last_data": [
                    {
                        "sensor_name": sensor_type_names[i],
                        "channel": channel_labels[i],
                        "value": last_sensor_data.get(channel_labels[i], None),
                        "notation": sensor_type_notations[i],
                        "icon":sensor_type_icons[i]  # Replace with actual icon if available
                    }
                    for i, (channel, sensor,icon) in enumerate(zip(channel_labels, sensor_type_names,sensor_type_icons))
                ]
            })
       
        return Response({"message": "success", "data": responses})
'''

@extend_schema(request=StationSerializer, responses={201: StationSerializer, 400: 'Error'})
class StationView(APIView):
    serializer = StationSerializer
    permission_classes =[IsAuthenticated]

    def get(self, request,station_serial_id=None):
       
        station = StationModel.objects.filter(balai=request.user.balai)

        if request.user.is_staff:
            station = StationModel.objects.all()

        serializer = self.serializer(instance=station, many=True,context={'request': request})
        # for item in serializer.data:
        #     #     item.pop("id")
        #     item.pop("created_by")

        if station_serial_id is not None:
            try:
                station = StationModel.objects.get(station_serial_id=station_serial_id)
                serializer = self.serializer(instance= station,context={'request': request})
                
            except Exception as e:
                return Response({"message":str(e)}, status=status.HTTP_404_NOT_FOUND)
       
        return Response({"message":"success", "data":serializer.data},status=status.HTTP_200_OK)
    
    def post(self, request):
        created_by = request.user
        request.data["created_by"] = created_by.id
        serializer = self.serializer(data=request.data,context={'request': request})
       
        if serializer.is_valid():
            station = serializer.save()
            auto_create_config(station=station)
            return Response({"message":"success","data":serializer.data},status=status.HTTP_201_CREATED)
        return Response({"message":serializer.errors},status=status.HTTP_400_BAD_REQUEST)
    
    def put (self,request,station_serial_id):
        data = request.data.copy()
        data['created_by'] = request.user.id
        try:
            station = StationModel.objects.get(station_serial_id=station_serial_id)
        except Exception as e:
            return Response({"message":str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.serializer(station,data=data,partial=True,context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message":"success","data":serializer.data},status=status.HTTP_201_CREATED)
        return Response({"message":serializer.errors},status=status.HTTP_400_BAD_REQUEST)
    

    def delete(self, request, station_serial_id):
        try:
            station = StationModel.objects.get(station_serial_id=station_serial_id)
        except Exception as e:
            return Response({"message":str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        station.delete()
        return Response ({"message":"station deleted"}, status=status.HTTP_204_NO_CONTENT)

'''
class DataStationView(APIView):
    def get(self, request, station_serial_id):
        try:
            stations = StationModel.objects.filter(station_serial_id=station_serial_id).prefetch_related(
                Prefetch(
                    'station_configurations',
                    queryset=StationConfigurationModel.objects.select_related('sensor_type', 'channel')
                )
            )
        except Exception as e:
            return Response({"message":str(e)},status=status.HTTP_400_BAD_REQUEST)
        
        channels = ChannelModel.objects.all().values()
        sensors = SensorTypeModel.objects.all().values()

        responses = []
        for station in stations:
            configurations = station.station_configurations.all()
            channel_labels = [get_channel_by_id(channels, entry.channel_id) for entry in configurations]
            sensor_type_names = [get_sensor_name_by_id(sensors, entry.sensor_type_id)[0] for entry in configurations]
            sensor_type_notations = [get_sensor_name_by_id(sensors, entry.sensor_type_id)[1] for entry in configurations]
            sensor_type_icons = [
                request.build_absolute_uri(settings.MEDIA_URL + f"{quote(get_sensor_name_by_id(sensors, entry.sensor_type_id)[2])}")
                for entry in configurations
            ]

            since = timezone.localtime(SensorDataModel.objects.filter(station=station).order_by("-time").first().time)
            delta_time = since - timezone.timedelta(hours=24)

            # Fetch hourly data for the chart
            hourly_data = SensorDataModel.objects.filter(
                station=station,
                time__gte=delta_time
            ).annotate(hour=TruncHour('time')).values('hour').annotate(
                latest_time=Max('time')
            ).order_by('hour')
            
            # if time filter from fe is active
            since_datetime=None
            until_datetime = None
            try:
                since_str = (request.GET.get("from"))
                since_datetime = datetime.strptime(since_str, '%Y-%m-%d %H:%M')
                until_str = (request.GET.get("until"))
                until_datetime = datetime.strptime(until_str, '%Y-%m-%d %H:%M')
                until_datetime +=timedelta(minutes=1)

                if since_datetime and until_datetime:
                    # Fetch hourly data for the chart
                    hourly_data = SensorDataModel.objects.filter(
                        station=station,
                        time__gte=since_datetime,
                        time__lte=until_datetime  
                    ).annotate(hour=TruncHour('time')).values('hour').annotate(
                        latest_time=Max('time')
                    ).order_by('hour')
            except :
                pass
          

            # Prepare sensor data dictionary for hourly chart data
            sensor_data_dict = {sensor: [] for sensor in channel_labels + ["battery", "temperature"]}
            time_values = []

            for entry in hourly_data:
                hour = entry['hour']
                latest_time = entry['latest_time']

                time_values.append(timezone.localtime(hour).isoformat())

                # Fetch the sensor data for the latest time of the current hour
                sensor_data = SensorDataModel.objects.filter(
                    station=station, time=latest_time
                ).values().first()

                if sensor_data:
                    for channel in channel_labels:
                        sensor_data_dict[channel].append(sensor_data.get(channel, None))

                    sensor_data_dict["battery"].append(sensor_data.get("battery", None))
                    sensor_data_dict["temperature"].append(sensor_data.get("temperature", None))

            # Prepare 'last_data' to include all historical data points for each sensor
            last_data_entries = []
            for i, channel in enumerate(channel_labels):
                sensor_data_model = SensorDataModel.objects.filter(station=station)
                if since_datetime and until_datetime:
                    sensor_data_model = SensorDataModel.objects.filter(station=station,
                                                                       time__gte=since_datetime,
                                                                       time__lte=until_datetime)
                sensor_entry = {
                    "sensor_name": sensor_type_names[i],
                    "channel": channel,
                    "value": list(sensor_data_model.values_list(channel, flat=True)),
                    # "time": list(SensorDataModel.objects.filter(station=station).values_list('time', flat=True).order_by('time')),
                    "notation": sensor_type_notations[i],
                    "icon": sensor_type_icons[i]
                }
                last_data_entries.append(sensor_entry)

            # Add battery and temperature data to 'last_data'
            last_data_entries.extend([
                {
                    "sensor_name": "Battery",
                    "channel": "battery",
                    "value": list(sensor_data_model.values_list('battery', flat=True)),
                    # "time": list(sensor_data_model.values_list('time', flat=True).order_by('time')),
                    "notation": "V",
                    "icon": None
                },
                {
                    "sensor_name": "Temperature",
                    "channel": "temperature",
                    "value": list(sensor_data_model.values_list('temperature', flat=True)),
                    # "time": list(sensor_data_model.values_list('time', flat=True).order_by('time')),
                    "notation": "°C",
                    "icon": None
                }
            ])

            # Get the latest battery and temperature values
            latest_sensor_data = sensor_data_model.order_by("-time").values().first()
            latest_battery = latest_sensor_data["battery"] if latest_sensor_data else None
            latest_temperature = latest_sensor_data["temperature"] if latest_sensor_data else None

            # Check station status
            station_status = "OK"
            if latest_sensor_data and (timezone.now() - timezone.localtime(latest_sensor_data["time"])).total_seconds() / 3600 > 1.5:
                station_status = "offline"
            if station.maintenance_status:
                station_status = "maintenance"
            
            hour = since.hour
            minute = since.minute
            day_name = since.strftime('%A')
            name_choice = {
                "Monday": 1,
                "Tuesday": 2,
                "Wednesday": 3,
                "Thursday": 4,
                "Friday": 5,
                "Saturday": 6,
                "Sunday": 7
            }

            # Get the integer value corresponding to the day name
            day = name_choice.get(day_name)
            if station_status=="OK":
                try:
                    threshold = ThresholdSensorModel.objects.get(station=station, day=day, hour=hour, minute=minute)
                    min = threshold.min
                    max = threshold.max
                    if latest_sensor_data["CH5"]>max:
                        station_status="Max Threshold"
                    elif latest_sensor_data["CH5"]<min:
                        station_status="Min Threshold"
                except Exception as e:
                    print(e)

            # Build the response
            responses.append({
                "id": station.id,
                "station_name": station.station_name,
                "last_battery": latest_battery,
                "last_temperature": latest_temperature,
                "station_serial_id": station.station_serial_id,
                "topic": station.topic,
                "observator_name": station.observator_name,
                "phone": str(station.observator_phone),
                "last_time": timezone.localtime(latest_sensor_data["time"]).isoformat() if latest_sensor_data else None,
                "image": request.build_absolute_uri(station.image.url) if station.image else None,
                "station_status": station_status,
                "maintenance": station.maintenance_status,
                "longitude":station.longitude,
                "latitude":station.latitude,
                "chart": {
                    "time": time_values,  # Hourly times for the chart
                    "sensor_data": [
                        {
                            "sensor_name": sensor_type_names[i],
                            "channel": channel,
                            "value": sensor_data_dict[channel],
                            # "time": time_values,
                            "notation": sensor_type_notations[i],
                            "icon": sensor_type_icons[i]
                        } for i, channel in enumerate(channel_labels)
                    ] + [
                        {
                            "sensor_name": "Battery",
                            "channel": "battery",
                            "value": sensor_data_dict["battery"],
                            # "time": time_values,
                            "notation": "V",
                            "icon": None
                        },
                        {
                            "sensor_name": "Temperature",
                            "channel": "temperature",
                            "value": sensor_data_dict["temperature"],
                            # "time": time_values,
                            "notation": "°C",
                            "icon": None
                        }
                    ]
                },
                "table": {
                    "time":[timezone.localtime(time) for time in sensor_data_model.values_list('time', flat=True).order_by('time')],
                    "data":last_data_entries}  # All historical data points for each sensor
            })

        return Response({"message": "success", "data": responses})
'''

'''
class DataStationView(APIView):
    def get(self, request, station_serial_id):
        try:
            stations = StationModel.objects.filter(station_serial_id=station_serial_id).prefetch_related(
                Prefetch(
                    'station_configurations',
                    queryset=StationConfigurationModel.objects.select_related('sensor_type', 'channel')
                )
            )
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        channels = ChannelModel.objects.all().values()
        sensors = SensorTypeModel.objects.all().values()

        responses = []
        for station in stations:
            configurations = station.station_configurations.all()
            channel_labels = [get_channel_by_id(channels, entry.channel_id) for entry in configurations]
            sensor_type_names = [get_sensor_name_by_id(sensors, entry.sensor_type_id)[0] for entry in configurations]
            sensor_type_notations = [get_sensor_name_by_id(sensors, entry.sensor_type_id)[1] for entry in configurations]
            sensor_type_icons = [
                request.build_absolute_uri(settings.MEDIA_URL + f"{quote(get_sensor_name_by_id(sensors, entry.sensor_type_id)[2])}")
                for entry in configurations
            ]

            since = timezone.localtime(SensorDataModel.objects.filter(station=station).order_by("-time").first().time)
            delta_time = since - timezone.timedelta(hours=24)

            # Fetch all data for the last 24 hours or the specified time range
            sensor_data_model = SensorDataModel.objects.filter(station=station, time__gte=delta_time)

            # if time filter from frontend is active
            since_datetime = None
            until_datetime = None
            try:
                since_str = request.GET.get("from")
                since_datetime = datetime.strptime(since_str, '%Y-%m-%d %H:%M')
                until_str = request.GET.get("until")
                until_datetime = datetime.strptime(until_str, '%Y-%m-%d %H:%M')
                until_datetime += timedelta(minutes=1)

                if since_datetime and until_datetime:
                    # Fetch data within the time range
                    sensor_data_model = SensorDataModel.objects.filter(
                        station=station,
                        time__gte=since_datetime,
                        time__lte=until_datetime
                    )
            except:
                pass

            # Prepare sensor data dictionary for all data points
            sensor_data_dict = {sensor: [] for sensor in channel_labels + ["battery", "temperature"]}
            time_values = [timezone.localtime(time).isoformat() for time in sensor_data_model.values_list('time', flat=True).order_by('time')]

            # Fill sensor data dictionary with all sensor data points
            for sensor_data in sensor_data_model:
                for channel in channel_labels:
                    sensor_data_dict[channel].append(getattr(sensor_data, channel, None))

                sensor_data_dict["battery"].append(sensor_data.battery)
                sensor_data_dict["temperature"].append(sensor_data.temperature)

            # Prepare 'last_data' to include all historical data points for each sensor
            last_data_entries = []
            for i, channel in enumerate(channel_labels):
                sensor_entry = {
                    "sensor_name": sensor_type_names[i],
                    "channel": channel,
                    "value": list(sensor_data_model.values_list(channel, flat=True)),
                    "notation": sensor_type_notations[i],
                    "icon": sensor_type_icons[i]
                }
                last_data_entries.append(sensor_entry)

            # Add battery and temperature data to 'last_data'
            last_data_entries.extend([
                {
                    "sensor_name": "Battery",
                    "channel": "battery",
                    "value": list(sensor_data_model.values_list('battery', flat=True)),
                    "notation": "V",
                    "icon": None
                },
                {
                    "sensor_name": "Temperature",
                    "channel": "temperature",
                    "value": list(sensor_data_model.values_list('temperature', flat=True)),
                    "notation": "°C",
                    "icon": None
                }
            ])

            # Get the latest battery and temperature values
            latest_sensor_data = sensor_data_model.order_by("-time").values().first()
            latest_battery = latest_sensor_data["battery"] if latest_sensor_data else None
            latest_temperature = latest_sensor_data["temperature"] if latest_sensor_data else None

            # Check station status
            station_status = "OK"
            if latest_sensor_data and (timezone.now() - timezone.localtime(SensorDataModel.objects.filter(station=station).last().time)).total_seconds() / 3600 > 1.5:
                station_status = "offline"
            if station.maintenance_status:
                station_status = "maintenance"

            hour = since.hour
            minute = since.minute
            day_name = since.strftime('%A')
            name_choice = {
                "Monday": 1,
                "Tuesday": 2,
                "Wednesday": 3,
                "Thursday": 4,
                "Friday": 5,
                "Saturday": 6,
                "Sunday": 7
            }

            # Get the integer value corresponding to the day name
            day = name_choice.get(day_name)
            if station_status == "OK":
                try:
                    threshold = ThresholdSensorModel.objects.get(station=station, day=day, hour=hour, minute=minute)
                    min = threshold.min
                    max = threshold.max
                    if latest_sensor_data["CH5"] > max:
                        station_status = "Max Threshold"
                    elif latest_sensor_data["CH5"] < min:
                        station_status = "Min Threshold"
                except Exception as e:
                    print(e)

            # Build the response
            responses.append({
                "id": station.id,
                "station_name": station.station_name,
                "last_battery": latest_battery,
                "last_temperature": latest_temperature,
                "station_serial_id": station.station_serial_id,
                "topic": station.topic,
                "observator_name": station.observator_name,
                "phone": str(station.observator_phone),
                "last_time": timezone.localtime(latest_sensor_data["time"]).isoformat() if latest_sensor_data else None,
                "image": request.build_absolute_uri(station.image.url) if station.image else None,
                "station_status": station_status,
                "maintenance": station.maintenance_status,
                "longitude": station.longitude,
                "latitude": station.latitude,
                "chart": {
                    "time": time_values,
                    "sensor_data": [
                        {
                            "sensor_name": sensor_type_names[i],
                            "channel": channel,
                            "value": sensor_data_dict[channel],
                            "notation": sensor_type_notations[i],
                            "icon": sensor_type_icons[i]
                        } for i, channel in enumerate(channel_labels)
                    ] + [
                        {
                            "sensor_name": "Battery",
                            "channel": "battery",
                            "value": sensor_data_dict["battery"],
                            "notation": "V",
                            "icon": None
                        },
                        {
                            "sensor_name": "Temperature",
                            "channel": "temperature",
                            "value": sensor_data_dict["temperature"],
                            "notation": "°C",
                            "icon": None
                        }
                    ]
                },
                # "table": {
                #     "time": [timezone.localtime(time) for time in sensor_data_model.values_list('time', flat=True).order_by('time')],
                #     "data": last_data_entries
                # }
            })

        return Response({"message": "success", "data": responses})
'''


class DataStationView(APIView):
    def get(self, request, station_serial_id):
        try:
            station = StationModel.objects.get(station_serial_id=station_serial_id)
        except StationModel.DoesNotExist as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            since = timezone.localtime(SensorDataModel.objects.filter(station=station).order_by("-time").first().time)
        except AttributeError:
            return Response({"message": "No sensor data found."}, status=status.HTTP_400_BAD_REQUEST)

        delta_time = since - timezone.timedelta(hours=24)
        sensor_data_model = SensorDataModel.objects.filter(station=station, time__gte=delta_time).order_by('-time')

        since_datetime = request.GET.get("from")
        until_datetime = request.GET.get("until")

        if since_datetime and until_datetime:
            try:
                since_datetime = datetime.strptime(since_datetime, '%Y-%m-%d %H:%M')
                until_datetime = datetime.strptime(until_datetime, '%Y-%m-%d %H:%M') + timedelta(minutes=1)
                sensor_data_model = SensorDataModel.objects.filter(
                    station=station, time__gte=since_datetime, time__lte=until_datetime
                ).order_by('-time')
            except ValueError:
                return Response({"message": "Invalid date format."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch sensor types and their corresponding notations
        sensor_types = SensorTypeModel.objects.all()
        sensor_type_dict = {sensor_type.sensor_name: sensor_type.notation for sensor_type in sensor_types}

        sensor_data_dict = {"Flow Meter": [], "Totalizer": [], "battery": [], "temperature": []}
        time_values = [timezone.localtime(time).isoformat() for time in sensor_data_model.values_list('time', flat=True)]

        for sensor_data in sensor_data_model:
            sensor_data_dict["Flow Meter"].append(sensor_data.modCH5)
            sensor_data_dict["Totalizer"].append(sensor_data.modCH6)
            sensor_data_dict["battery"].append(sensor_data.battery)
            sensor_data_dict["temperature"].append(sensor_data.temperature)

        last_data_entries = [
            {
                "sensor_name": "Flow Meter",
                "channel": "modCH5",
                "value": list(sensor_data_model.values_list('modCH5', flat=True)),
                "notation": sensor_type_dict.get("Flow Meter", "m³"),
                "icon": None  # Add icons if needed
            },
            {
                "sensor_name": "Totalizer",
                "channel": "modCH6",
                "value": list(sensor_data_model.values_list('modCH6', flat=True)),
                "notation": sensor_type_dict.get("Totalizer", "m³"),
                "icon": None
            },
            {
                "sensor_name": "Battery",
                "channel": "battery",
                "value": list(sensor_data_model.values_list('battery', flat=True)),
                "notation": sensor_type_dict.get("Battery", "V"),
                "icon": None
            },
            {
                "sensor_name": "Temperature",
                "channel": "temperature",
                "value": list(sensor_data_model.values_list('temperature', flat=True)),
                "notation": sensor_type_dict.get("Temperature", "°C"),
                "icon": None
            }
        ]

        latest_sensor_data = sensor_data_model.first()
        latest_battery = latest_sensor_data.battery if latest_sensor_data else None
        latest_temperature = latest_sensor_data.temperature if latest_sensor_data else None

        station_status = "OK"
        if latest_sensor_data and (timezone.now() - timezone.localtime(latest_sensor_data.time)).total_seconds() / 3600 > 1.5:
            station_status = "offline"
        if station.maintenance_status:
            station_status = "maintenance"

        chart_data = []
        for time, sensor_data in zip(time_values, sensor_data_model):
            status_ok = "OK"
            hour = timezone.localtime(sensor_data.time).hour
            minute = timezone.localtime(sensor_data.time).minute
            day_name = timezone.localtime(sensor_data.time).strftime('%A')

            day_choice = {
                "Monday": 1,
                "Tuesday": 2,
                "Wednesday": 3,
                "Thursday": 4,
                "Friday": 5,
                "Saturday": 6,
                "Sunday": 7
            }
            day = day_choice.get(day_name)

            try:
                threshold = ThresholdSensorModel.objects.get(station=station, day=day, hour=hour, minute=minute)
                min_threshold = threshold.min
                max_threshold = threshold.max
                flow_meter_value = sensor_data.modCH5
                if flow_meter_value is not None:
                    if flow_meter_value > max_threshold:
                        status_ok = "Max Threshold"
                    elif flow_meter_value < min_threshold:
                        status_ok = "Min Threshold"
            except ThresholdSensorModel.DoesNotExist:
                pass

            chart_data.append({
                "time": time,
                "status": status_ok,
                "sensor_data": [
                    {
                        "sensor_name": "Flow Meter",
                        "channel": "modCH5",
                        "value": sensor_data.modCH5,
                        "notation": sensor_type_dict.get("Flow Meter", "m³"),
                        "icon": None
                    },
                    {
                        "sensor_name": "Totalizer",
                        "channel": "modCH6",
                        "value": sensor_data.modCH6,
                        "notation": sensor_type_dict.get("Totalizer", "m³"),
                        "icon": None
                    },
                    {
                        "sensor_name": "Battery",
                        "channel": "battery",
                        "value": sensor_data.battery,
                        "notation": sensor_type_dict.get("Battery", "V"),
                        "icon": None
                    },
                    {
                        "sensor_name": "Temperature",
                        "channel": "temperature",
                        "value": sensor_data.temperature,
                        "notation": sensor_type_dict.get("Temperature", "°C"),
                        "icon": None
                    }
                ]
            })
        
        # Initialize variables
        flow_meter_values = []

        # Process chart data and collect Flow Meter values
        for sensor_data in chart_data:
            for sensor in sensor_data["sensor_data"]:
                if sensor["sensor_name"] == "Flow Meter" and sensor["value"] is not None:
                    flow_meter_values.append(sensor["value"])

        # Calculate average flow if there are flow meter values
        average_flow = sum(flow_meter_values) / len(flow_meter_values) if flow_meter_values else None

        # Count total Flow Meter data points
        total_data = len(flow_meter_values)

        response_data = {
            "id": station.id,
            "station_name": station.station_name,
            "last_battery": latest_battery,
            "last_temperature": latest_temperature,
            "station_serial_id": station.station_serial_id,
            "topic": station.topic,
            "observator_name": station.observator_name,
            "phone": str(station.observator_phone),
            "last_time": timezone.localtime(latest_sensor_data.time).isoformat() if latest_sensor_data else None,
            "image": request.build_absolute_uri(station.image.url) if station.image else None,
            "station_status": station_status,
            "maintenance": station.maintenance_status,
            "longitude": station.longitude,
            "latitude": station.latitude,
            "average_flow":average_flow,
            "total_data":total_data,
            "chart": chart_data
        }

        return Response({"message": "success", "data": [response_data]})

@extend_schema(request=MaintenanceRecordSerializer, responses={201: MaintenanceRecordSerializer, 400: 'Error'})
class MaintenanceRecordTableView(APIView):
    serializer = MaintenanceRecordSerializer
    permission_classes = [IsAuthenticated]
    
    def get(self, request, station_serial_id=None):
      if station_serial_id is not None:
        try:
            record = MaintenanceRecordModel.objects.filter(station__station_serial_id = station_serial_id).order_by("-start_date")
        
        except Exception as e:
           return Response({"message":e}, status=status.HTTP_400_BAD_REQUEST)

        paginator = ItemPagination()
        result_page = paginator.paginate_queryset(record, request, self)
        if result_page is not None:
            serializer = self.serializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)


@extend_schema(request=MaintenanceRecordSerializer, responses={201: MaintenanceRecordSerializer, 400: 'Error'})    
class MaintenanceRecordDView(APIView):
   serializer = MaintenanceRecordSerializer
   permission_classes = [IsAuthenticated]

   def get(self, request, station_serial_id=None):
      if station_serial_id is not None:
        since = SensorDataModel.objects.filter(station__station_serial_id=station_serial_id).order_by("-time").first()
        if since is None:
           return  Response({"message":"station doesn has any data from the sensor"})
        
        since = since.time
        since = timezone.localtime(since)
        last_24_hours = since - timezone.timedelta(hours=24)
        try:
            record = MaintenanceRecordModel.objects.filter(station__station_serial_id = station_serial_id,start_date__gte=last_24_hours)
        
        except Exception as e:
           return Response({"message":str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.serializer(instance=record, many=True)

        return Response({"message":"success","data":serializer.data})
    
@extend_schema(request=SensorDataSerializer, responses={201: SensorDataSerializer, 400: 'Error'})
class SensorDataTableView(APIView):
    serializer = SensorDataSerializer

    def get(self, request, station_serial_id=None):
       if station_serial_id is not None:
            record = SensorDataModel.objects.filter(station__station_serial_id=station_serial_id).order_by("-time")
            paginator = ItemPagination()
            result_page = paginator.paginate_queryset(record,request,self)
            if result_page is not None:
                serializer = self.serializer(result_page, many=True)
                return paginator.get_paginated_response(serializer.data)

@extend_schema(request=SensorTypeSerializer, responses={201: SensorTypeSerializer, 400: 'Error'})
class SensorTypeView(APIView):
    serializer = SensorTypeSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request,pk=None, *args, **kwargs):
        if pk:
            try:
                sensor_type = SensorTypeModel.objects.get(pk=pk)
                serializer = self.serializer(instance=sensor_type,context={'request': request})
            except SensorTypeModel.DoesNotExist:
                return Response({"message":"sensortype not exist"}, status=status.HTTP_404_NOT_FOUND)
        else:  
            sensor_type = SensorTypeModel.objects.all()
            serializer = self.serializer(instance=sensor_type, many=True,context={'request': request})
        
        data = serializer.data.copy()
        if type(data)==list:
            data = [item for item in data if item['sensor_name'] not in ['temperature', "battery"]]
        return Response({"message":"success","data":data}, status=status.HTTP_200_OK)
    

    def post(self, request, *arg, **kwarg):
        form = SensorTypeForm(request.POST, request.FILES)
        if form.is_valid():
            sensor_type = form.save()
            serializer = SensorTypeSerializer(sensor_type, context={'request': request}) 
            return Response({"message":"success",'data':serializer.data}, status=status.HTTP_201_CREATED)
        
        return Response ({"message":form.errors}, status=status.HTTP_400_BAD_REQUEST)
        
    
    def put(self, request, pk):
        try:
            sensor_type = SensorTypeModel.objects.get(pk=pk)
        except SensorTypeModel.DoesNotExist:
            return Response({"message":"sensortype is not exist"}, status=status.HTTP_404_NOT_FOUND)
        
        form = SensorTypeForm(request.POST, request.FILES, instance=sensor_type)
        if form.is_valid():
            sensor_type = form.save()
            serializer = SensorTypeSerializer(sensor_type, context={'request': request})   
            return Response({"message":"success","data":serializer.data}, status=status.HTTP_201_CREATED)
        
        return Response({"message":form.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        try:
            sensor_type = SensorTypeModel.objects.get(pk=pk)
        except SensorTypeModel.DoesNotExist:
            return Response({"message":"sensortype is not exist"}, status=status.HTTP_404_NOT_FOUND)
        sensor_type.delete()
        return Response({
            "message":"success delete",
        }, status=status.HTTP_204_NO_CONTENT)


@extend_schema(request=LoggerTypeSerializer, responses={201: LoggerTypeSerializer, 400: 'Error'})
class LoggerView(APIView):
    permission_classes = [IsAuthenticated]
    serializer = LoggerTypeSerializer

    def get(self, request):
        instance = LoggerTypeModel.objects.all()
        serializer = self.serializer(instance=instance, many=True)
        return Response({"message":"success", "data":serializer.data}, status=status.HTTP_200_OK)
    
    def post(self, request):
        data = request.data
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message":"success", "data":serializer.data}, status=status.HTTP_201_CREATED)

        return Response({"message":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)    

    def put(self, request, pk):
        try:
            logger = LoggerTypeModel.objects.get(pk=pk)
        
        except Exception as e:
            return Response({"message":"logger ID is not exist"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.serializer(logger, data= request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response ({"message":"success", "data":serializer.data}, status=status.HTTP_201_CREATED)
        
        return Response ({"message":serializer.error_messages}, status=status.HTTP_400_BAD_REQUEST)

    def delete (self, request,pk):
        try:
            logger = LoggerTypeModel.objects.get(pk=pk)
        except Exception as e:
            return Response({"message":"logger ID is not exist"}, status=status.HTTP_404_NOT_FOUND)
        
        logger.delete()
        return Response({"message":"logger with this ID deleted"},status=status.HTTP_204_NO_CONTENT)


@extend_schema(request=ChannelSerializer, responses={201: ChannelSerializer, 400: 'Error'}) 
class ChannelView(APIView):
    serializer = ChannelSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        channel = ChannelModel.objects.all()
        serializer = self.serializer(instance=channel, many=True)
        data = serializer.data.copy()
        # data.pop('TEMP')
        # data.pop('BATT')
        data = [item for item in data if item["channel_label"] not in ["TEMP", "BATT"]]
        return Response({"message":"success","data":data}, status=status.HTTP_200_OK)

'''
class UploadCSVAPIView(APIView):
    def post(self, request, station_serial_id,*args, **kwargs):
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({"message": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            csv_data = StringIO(csv_file.read().decode())
            reader = csv.DictReader(csv_data)

            for row in reader:
                try:
                    # Extract data from the CSV row
                    hour = int(row.get('hour'))
                    minute = int(row.get('minute'))
                    day = int(row.get('day'))
                    min_value = float(row.get('min'))
                    max_value = float(row.get('max'))

                    # Find the station
                    station = get_object_or_404(StationModel,station_serial_id=station_serial_id)

                    # Update or create the ThresholdSensorModel entry
                    obj, created = ThresholdSensorModel.objects.update_or_create(
                        station=station,
                        hour=hour,
                        minute=minute,
                        day=day,
                        defaults={
                            'min': min_value,
                            'max': max_value,
                            'modified_at': timezone.now(),
                        }
                    )
                except Exception as e:
                    return Response({"error":str(e) }, status=status.HTTP_400_BAD_REQUEST)

            return Response({"success": "CSV data processed successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
'''

class UploadCSVAPIView(APIView):
    def post(self, request, station_serial_id, *args, **kwargs):
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({"message": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            csv_data = StringIO(csv_file.read().decode())
            reader = csv.DictReader(csv_data)

            station = get_object_or_404(StationModel, station_serial_id=station_serial_id)
            
            records_to_update = []
            records_to_create = []
            existing_records = {}

            # Pre-fetch all existing ThresholdSensorModel entries for the given station
            existing_entries = ThresholdSensorModel.objects.filter(station=station)
            for entry in existing_entries:
                key = (entry.hour, entry.minute, entry.day)
                existing_records[key] = entry

            with transaction.atomic():
                for row in reader:
                    try:
                        # Extract data from the CSV row
                        hour = int(row.get('hour'))
                        minute = int(row.get('minute'))
                        day = int(row.get('day'))
                        min_value = float(row.get('min'))
                        max_value = float(row.get('max'))

                        key = (hour, minute, day)

                        if key in existing_records:
                            # Update the existing record
                            record = existing_records[key]
                            record.min = min_value
                            record.max = max_value
                            record.modified_at = timezone.now()
                            records_to_update.append(record)
                        else:
                            # Create a new record
                            new_record = ThresholdSensorModel(
                                station=station,
                                hour=hour,
                                minute=minute,
                                day=day,
                                min=min_value,
                                max=max_value,
                                modified_at=timezone.now()
                            )
                            records_to_create.append(new_record)

                    except Exception as e:
                        return Response({"message": "csv format columns is uncompatible"}, status=status.HTTP_400_BAD_REQUEST)

                # Bulk update existing records
                if records_to_update:
                    ThresholdSensorModel.objects.bulk_update(records_to_update, ['min', 'max', 'modified_at'])
                
                # Bulk create new records
                if records_to_create:
                    ThresholdSensorModel.objects.bulk_create(records_to_create)

            return Response({"message": "CSV data processed successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class PublishResendView(APIView):
    serializer = PublishResendSerializer
    def post(self, request):
        try:
            station = StationModel.objects.get(station_serial_id=request.data['station'])
        except Exception as e:
            return Response({"message":str(e)},status=status.HTTP_400_BAD_REQUEST)
        
        data = request.data.copy()
        print("station",station)
        data['station'] = station.pk
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message":"sucess"},status=status.HTTP_201_CREATED)
        
        return Response({"message":serializer.errors},status=status.HTTP_400_BAD_REQUEST)