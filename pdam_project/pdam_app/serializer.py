from rest_framework import serializers
from .models import (StationModel, StationConfigurationModel, SensorDataModel,
                    LoggerTypeModel, MaintenanceRecordModel, LoggerTypeModel,
                    SensorTypeModel, ChannelModel, PublishResendModel)
from account_app.models import BalaiModel
import os, uuid
from django.conf import settings
from account_app.models import User


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationModel
        fields ="__all__"
        

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'image' in data and data['image'] is not None:
            print(data["image"])
            image_url = data['image']
            if image_url.startswith('/media/'):
                # Get the request object from serializer's context
                request = self.context.get('request')
                if request:
                    # Build the full URL using request.build_absolute_uri()
                    data['image'] = request.build_absolute_uri(image_url)
                else:
                    # Handle the case when request object is not available
                    # You can provide a default URL or raise an exception
                    data['image'] = 'default_image_url'
        
        data["logger_type"] = {
            "id":LoggerTypeModel.objects.get(id=data["logger_type"]).id,
            "logger_ver":LoggerTypeModel.objects.get(id=data["logger_type"]).logger_ver,
        }
        data["balai"] = {
            "id":BalaiModel.objects.get(id=data["balai"]).id,
            "balai_name":BalaiModel.objects.get(id=data["balai"]).balai_name,
        }

        if data["created_by"] is not None:
            data["created_by"] = {
                "id": User.objects.get(pk=data['created_by']).id ,
                "username":User.objects.get(pk=data['created_by']).username
            }
        return data
    
    def create(self, validated_data):
        image_file = validated_data.pop('image', None)  # Make image field optional
        if image_file:
            unique_filename = f"{uuid.uuid4().hex}.{image_file.name.split('.')[-1]}"
            validated_data['image'] = os.path.join('station', unique_filename)
            # Save the uploaded image file with the unique filename
            with open(os.path.join('media', validated_data['image']), 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)
        return StationModel.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        if 'station_name' in validated_data and StationModel.objects.filter(station_name=validated_data['station_name']).exclude(id=instance.id).exists():
            raise serializers.ValidationError({'station_name': 'This station_name is already in use.'})
        if 'topic' in validated_data and StationModel.objects.filter(topic=validated_data['topic']).exclude(id=instance.id).exists():
            raise serializers.ValidationError({'topic': 'This topic is already in use.'})
        
        image_file = validated_data.pop('image', None)
        if image_file:
            unique_filename = f"{uuid.uuid4().hex}.{image_file.name.split('.')[-1]}"
            validated_data['image'] = os.path.join('station', unique_filename)
            if instance.image and os.path.isfile(instance.image.path):
                os.remove(instance.image.path)
            with open(os.path.join(settings.MEDIA_ROOT, validated_data['image']), 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)
        return super().update(instance, validated_data)
    
class MaintenanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRecordModel
        fields = "__all__"


class SensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorDataModel
        fields = "__all__"

class LoggerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoggerTypeModel
        fields = "__all__"

    def update(self, instance, validated_data):
        if 'logger_ver' in validated_data and LoggerTypeModel.objects.filter(logger_ver=validated_data['logger_ver']).exclude(id=instance.id).exists():
            raise serializers.ValidationError({'logger_ver': 'This logger_ver is already in use.'})

        return super().update(instance, validated_data)
    
class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelModel
        fields = ["id","channel_label"]

    def create(self, validated_data):
        return super().create(validated_data)


class SensorTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model =SensorTypeModel
        fields =[field.name for field in SensorTypeModel._meta.fields]

    def create(self, validated_data):
        sensor_icon_file = validated_data.pop('sensor_icon',None)
        if sensor_icon_file:
            unique_filename = f"{uuid.uuid4().hex}.{sensor_icon_file.name.split('.')[-1]}"
            validated_data['sensor_icon'] = os.path.join('sensor_icon', unique_filename)
            # Save the uploaded sensor_icon file with the unique filename
            with open(os.path.join('media', validated_data['sensor_icon']), 'wb') as f:
                for chunk in sensor_icon_file.chunks():
                    f.write(chunk)
        return SensorTypeModel.objects.create(**validated_data)
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'sensor_icon' in data and data['sensor_icon'] is not None:
            sensor_icon_url = data['sensor_icon']
            # print("sensor_icon URL:", sensor_icon_url)  # Add this line for debugging
            if sensor_icon_url.startswith('/media/'):
                # Get the request object from serializer's context
                request = self.context.get('request')
                if request:
                    # Build the full URL using request.build_absolute_uri()
                    data['sensor_icon'] = request.build_absolute_uri(sensor_icon_url)
                else:
                    # Handle the case when request object is not available
                    # You can provide a default URL or raise an exception
                    data['sensor_icon'] = 'default_sensor_icon_url'
        return data
    
    def update(self, instance, validated_data):
        sensor_icon_file = validated_data.pop('sensor_icon', None)
        if sensor_icon_file:
     
            unique_filename = f"{uuid.uuid4().hex}.{sensor_icon_file.name.split('.')[-1]}"
            validated_data['sensor_icon'] = os.path.join('sensor_icon', unique_filename)
            if instance.sensor_icon and os.path.isfile(instance.sensor_icon.path):
                os.remove(instance.sensor_icon.path)
            with open(os.path.join(settings.MEDIA_ROOT, validated_data['sensor_icon']), 'wb') as f:
                for chunk in sensor_icon_file.chunks():
                    f.write(chunk)
        else:
            if instance.sensor_icon and os.path.isfile(instance.sensor_icon.path):

                os.remove(instance.sensor_icon.path)
        return super().update(instance, validated_data)
    

    def validate_sensor_name(self, value):
        # Check if the username already exists
        if self.instance is None or self.instance.sensor_name!= value:
            if SensorTypeModel.objects.filter(sensor_name=value).exclude(sensor_name=self.instance.sensor_name).exists():
                raise serializers.ValidationError("This sensor name already exist")
            


class PublishResendSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishResendModel
        fields = "__all__"

    def create(self, validated_data):
        return super().create(validated_data)
