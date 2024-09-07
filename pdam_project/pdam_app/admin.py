from django.contrib import admin
from pdam_project.admin import admin_site
from .models import (StationModel, RawMessagemodel, CheckerDataModel, 
                    SensorDataModel, ModifiedRecordModel, MaintenanceRecordModel,
                    SensorTypeModel, ChannelModel, 
                    StationConfigurationModel,StationConfigurationRecordModel,
                    SensorDataReqModel,LoggerTypeModel, ThresholdSensorModel,
                    PublishThresholdModel,PublishResendModel, TelegramNotificationModel
                    )

from .form import RawMessageForm, SensorTypeForm,StationConfigurationForm, ThreshodSensorForm, StationForm


# Register your models here.
# @admin.register(StationModel)
class StationAdmin(admin.ModelAdmin):
    model =StationModel
    form = StationForm
    list_display = [field.name for field in StationModel._meta.fields ]
    list_filter = ["balai"]
    search_fields = ('station_name', 'topic')

class LoggerTypeAdmin(admin.ModelAdmin):
    model = LoggerTypeModel
    list_display = [field.name for field in LoggerTypeModel._meta.fields ]
 


# @admin.register(RawMessagemodel)
class RawMessageAdmin(admin.ModelAdmin):
    form = RawMessageForm
    model = RawMessagemodel
    list_display = ("id","created_at","message","time","status")
    search_fields = ['topic']
    list_filter = ["topic","status"]




# @admin.register(CheckerDataModel)
class CheckerDataAdmin(admin.ModelAdmin):
    model =CheckerDataModel
    list_display = [field.name for field in CheckerDataModel._meta.fields ]
    list_filter = ["status", "station__topic"]


# @admin.register(SensorDataModel)
class SensorDataAdmin(admin.ModelAdmin):
    model =SensorDataModel
    list_display = [field.name for field in SensorDataModel._meta.fields ]
    list_filter = ["status", "station__topic"]


# @admin.register(ModifiedRecordModel)
class ModifiedRecordaAdmin(admin.ModelAdmin):
    model =ModifiedRecordModel
    list_display = ["get_station","percent_cal","factor_cal","created_at","expired_at"]
    list_filter = ["station__topic"]

    def get_station(self,obj):
        return obj.station.topic
    
    get_station.short_description = 'Station'


class MaintenanceRecordAdmin(admin.ModelAdmin):
    model =MaintenanceRecordModel
    # list_display = [field.name for field in MaintenanceRecordModel._meta.fields ]
    list_display = ['get_station',"start_date","end_date"]
    search_fields = ['station__topic']
    list_filter = ["station__topic"]
    
    def get_station(self,obj):
        return obj.station.topic
    
    get_station.short_description = 'Station topic'


class SensorTypeAdmin(admin.ModelAdmin):
    model = SensorTypeModel
    list_display = [ field.name for field in SensorTypeModel._meta.fields]
    form = SensorTypeForm


class StationConfigurationAdmin(admin.ModelAdmin):
    model = StationConfigurationModel
    form = StationConfigurationForm
    list_display =["id","created_at","get_stationname","get_sensortype","get_channel","modified_at"]
    list_filter = ['station__topic',"channel__channel_label","sensor_type__sensor_name"]

    def get_stationname(self, obj):
        return obj.station.topic if obj.station else None
    
    def get_sensortype(self, obj):
        return obj.sensor_type.sensor_name if obj.sensor_type else None
    
    def get_channel(self, obj):
        return obj.channel.channel_label if obj.channel else None
    

    get_stationname.short_description = 'Station Topic'  # Set the column name in the admin interface
    get_sensortype.short_description = 'Sensor'
    get_channel.short_description = 'Label'


class ChannelAdmin(admin.ModelAdmin):
    model = ChannelModel
    list_display = [ field.name for field in ChannelModel._meta.fields]


class StationConfigurationRecordAdmin(admin.ModelAdmin):
    model = StationConfigurationRecordModel
    list_display =["id","created_at","get_stationname","get_sensortype","get_channel","end_date"]

    def get_stationname(self, obj):
        return obj.station.topic if obj.station else None
    
    def get_sensortype(self, obj):
        return obj.sensor_type.sensor_name if obj.sensor_type else None
    
    def get_channel(self, obj):
        return obj.channel.channel_label if obj.channel else None
    

    get_stationname.short_description = 'Station Topic'  # Set the column name in the admin interface
    get_sensortype.short_description = 'Sensor'
    get_channel.short_description = 'Label'


class SensorDataReqAdmin(admin.ModelAdmin):
    model = SensorDataReqModel
    list_display=["id","get_station", "get_channel", "get_sensor_type","data" ,"created_at", "time","iteration","status"]
    list_filter =["station__topic","sensor_type__sensor_name","channel__channel_label"]

    def get_station(self, obj):
        return obj.station.topic if obj.station else None
    
    
    def get_channel(self, obj):
        return obj.channel.channel_label if obj.channel else None
    
        
    def get_sensor_type(self, obj):
        return obj.sensor_type.sensor_name if obj.sensor_type else None
    
    get_station.short_description = 'Station Topic'  # Set the column name in the admin interface
    get_sensor_type.short_description = 'Sensor'
    get_channel.short_description = 'Label'

class ThresholdSensorAdmin(admin.ModelAdmin):
    model = ThresholdSensorModel
    list_display = ["id", "get_station", "day","hour","minute","min","max","created_at","modified_at"]
    list_filter = ["station__topic","day","hour"]
    form = ThreshodSensorForm
    
    def get_station(self, obj):
        return obj.station.topic if obj.station else None
    
    get_station.short_description = "station"

class PublishThresholdAdmin(admin.ModelAdmin):
    model = PublishThresholdModel
    list_display = [ field.name for field in PublishThresholdModel._meta.fields]
    list_filter = ["day","hour","is_sent"]

class PublishResendAdmin(admin.ModelAdmin):
    model = PublishResendModel
    list_display = [ field.name for field in PublishResendModel._meta.fields]
    list_filter = ["station"]


class TelegramNotificationAdmin(admin.ModelAdmin):
    model = TelegramNotificationModel
    list_display = [ field.name for field in TelegramNotificationModel._meta.fields]
    list_filter = ["station"]

admin_site.register(TelegramNotificationModel, TelegramNotificationAdmin)
admin_site.register(StationModel,StationAdmin)
admin_site.register(StationConfigurationRecordModel, StationConfigurationRecordAdmin)
admin_site.register(StationConfigurationModel, StationConfigurationAdmin)
admin_site.register(ChannelModel,ChannelAdmin)
admin_site.register(SensorTypeModel, SensorTypeAdmin)
admin_site.register(MaintenanceRecordModel,MaintenanceRecordAdmin)
admin_site.register(ModifiedRecordModel, ModifiedRecordaAdmin)
admin_site.register(SensorDataModel,SensorDataAdmin)
admin_site.register(SensorDataReqModel, SensorDataReqAdmin)
admin_site.register(CheckerDataModel,CheckerDataAdmin)
admin_site.register(RawMessagemodel,RawMessageAdmin)
admin_site.register(LoggerTypeModel,LoggerTypeAdmin)
admin_site.register(ThresholdSensorModel, ThresholdSensorAdmin)
admin_site.register(PublishThresholdModel, PublishThresholdAdmin)
admin_site.register(PublishResendModel, PublishResendAdmin)

