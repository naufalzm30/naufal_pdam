from django.db import models
import uuid
from django.utils import timezone
import os
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from phonenumber_field.modelfields import PhoneNumberField
from account_app.models import BalaiModel
# Create your models here.

User = get_user_model()

def validate_positive(value):
    if value < 0:
        raise ValidationError(
            '%(value)s is not a positive number',
            params={'value': value},
        )

class LoggerTypeModel(models.Model):
    logger_ver = models.CharField(max_length=100, unique=True)
    max_channel = models.PositiveIntegerField()
    max_analog = models.PositiveIntegerField()
    max_digital = models.PositiveIntegerField()
    
    def __str__(self):
        return self.logger_ver
     
    class Meta:
        db_table = "pdam_logger"

class StationModel(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station_serial_id = models.UUIDField(unique=True, editable=False, default=uuid.uuid4, verbose_name='uid')
    station_name = models.CharField(max_length=100)
    location = models.CharField(max_length=100, null=True)
    topic = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    percent_cal = models.FloatField(default=0, validators=[validate_positive])
    factor_cal = models.BooleanField(default=False)
    maintenance_status = models.BooleanField(default=False)
    logger_type = models.ForeignKey(LoggerTypeModel, on_delete=models.CASCADE)
    elevation = models.FloatField()
    sn_modem = models.CharField(max_length=100, blank=True, null=True)
    sn_logger = models.CharField(max_length=100, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,related_name="station_model",blank=True,null=True)
    observator_name = models.CharField(null=True,max_length=100, blank=True)
    observator_phone = PhoneNumberField(null=True,max_length=15, blank=True)
    image = models.ImageField(null=True, blank=True, upload_to='station')
    latitude = models.DecimalField(max_digits=9, decimal_places=6,null=True)  
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True) 

    balai = models.ForeignKey(BalaiModel, on_delete=models.CASCADE, default=1) 

    def __str__(self):
        return self.topic
    

    def save(self, *args, **kwargs):
        try:
            old_image = StationModel.objects.get(pk=self.pk).image
        except StationModel.DoesNotExist:
            old_image = None
        super().save(*args, **kwargs)
        if old_image and old_image != self.image:
            if os.path.isfile(old_image.path):
                os.remove(old_image.path)

        # If Station is being created for the first time, create a ModifiedRecord
        if not ModifiedRecordModel.objects.filter(station=self).exists():
            ModifiedRecordModel.objects.create(
                station=self,
                percent_cal=self.percent_cal,
                factor_cal = self.factor_cal,
                created_at=timezone.now(),
                expired_at=None
            )
        else:
            # Get the latest ModifiedRecord for this Station
            latest_record = ModifiedRecordModel.objects.filter(station=self, expired_at=None).first()
            if latest_record and (latest_record.percent_cal != self.percent_cal or latest_record.factor_cal!=self.factor_cal):
                # Expire the current record
                latest_record.expired_at = timezone.now()
                latest_record.save()
                # Create a new ModifiedRecord with the updated cal value
                ModifiedRecordModel.objects.create(
                    station=self,
                    factor_cal=self.factor_cal,
                    percent_cal = self.percent_cal,
                    created_at=timezone.now(),
                    expired_at=None
                )

        if self.maintenance_status:
            MaintenanceRecordModel.objects.create(
                station=self,
                start_date = timezone.now(),
                end_date = None

            )
        else:
            latest_record = MaintenanceRecordModel.objects.filter(station=self, end_date=None).first()
            if latest_record:
                latest_record.end_date= timezone.now()
                latest_record.save()

    def delete(self, *args, **kwargs):
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)  # Corrected super() call

    class Meta:
        db_table = 'pdam_station'


class ModifiedRecordModel(models.Model):
    station = models.ForeignKey(StationModel, on_delete=models.CASCADE)
    percent_cal = models.FloatField()
    factor_cal = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pdam_modified_record'

class MaintenanceRecordModel(models.Model):
    station = models.ForeignKey(StationModel, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pdam_maintenance_record"

class RawMessagemodel(models.Model):
    # station = models.ForeignKey(StationModel, on_delete=models.CASCADE)
    message = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    time = models.DateTimeField()
    topic = models.CharField(max_length=100, null=True, blank=True)
    status = models.IntegerField()

    class Meta:
        db_table = 'pdam_raw_message'
        unique_together = ( 'time','status', "topic")


class CheckerDataModel(models.Model):
    station = models.ForeignKey(StationModel,null=True,on_delete=models.SET_NULL)
    secs_col = models.IntegerField()
    time = models.DateTimeField()
    created_at = models.DateTimeField()
    CH1 = models.FloatField(null=True)
    CH2 = models.FloatField(null=True)
    CH3 = models.FloatField(null=True)
    CH4 = models.FloatField(null=True)
    CH5 = models.FloatField(null=True)
    CH6 = models.FloatField(null=True)
    modCH5 =  models.FloatField(null=True)
    modCH6 = models.FloatField(null=True)  
    temperature = models.FloatField(null=True)
    battery = models.FloatField(null=True)
    saved_data = models.IntegerField(null=True)
    itter_flow = models.IntegerField(null=True)
    status = models.IntegerField(null=True)


    
    class Meta:
        unique_together = ('station', 'time')
        db_table = 'pdam_checker_data'

    
class SensorDataModel(models.Model):
    station = models.ForeignKey(StationModel, null=True, on_delete=models.SET_NULL, related_name="sensor_data")
    time = models.DateTimeField()
    created_at = models.DateTimeField()
    CH1 = models.FloatField(null=True)
    CH2 = models.FloatField(null=True)
    CH3 = models.FloatField(null=True)
    CH4 = models.FloatField(null=True)
    CH5 = models.FloatField(null=True)
    CH6 = models.FloatField(null=True)
    modCH5 =  models.FloatField(null=True)
    modCH6 = models.FloatField(null=True)   
    temperature = models.FloatField(null=True)
    battery = models.FloatField(null=True)
    saved_data = models.IntegerField(null=True)
    itter_flow = models.IntegerField(null=True)
    status = models.IntegerField(null=True)

    class Meta:
        unique_together = ('station', 'time')
        db_table = 'pdam_sensor_data'


class SensorTypeModel(models.Model):
    sensor_name = models.CharField(max_length=30)
    sensor_icon = models.ImageField(upload_to='sensor_icon', null=True, blank=True)
    # image = models.FileField(upload_to="sensor_icon",null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notation = models.CharField(max_length=10, blank=True, null=True)
    
    class Meta:
        db_table = "pdam_sensor_type"


    def save(self, *args, **kwargs):
        try:
            old_sensor_icon = SensorTypeModel.objects.get(pk=self.pk).sensor_icon
        except SensorTypeModel.DoesNotExist:
            old_sensor_icon = None

        super().save(*args, **kwargs)  # Corrected super() call
        if old_sensor_icon and old_sensor_icon != self.sensor_icon:
            if os.path.isfile(old_sensor_icon.path):
                os.remove(old_sensor_icon.path)

    def delete(self, *args, **kwargs):
        if self.sensor_icon and os.path.isfile(self.sensor_icon.path):
            os.remove(self.sensor_icon.path)
        super().delete(*args, **kwargs)  # Corrected super() call


class ChannelModel(models.Model):
    channel_label = models.CharField(max_length=20,unique=True)
    created_at = models.DateTimeField(auto_now_add= True)
    
    class Meta:
        db_table = "pdam_channel"

class StationConfigurationModel(models.Model):
    station = models.ForeignKey(StationModel, on_delete=models.CASCADE, related_name="station_configurations")
    sensor_type = models.ForeignKey(SensorTypeModel, on_delete=models.CASCADE)
    channel = models.ForeignKey(ChannelModel, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    note = models.CharField(max_length=300, null=True, blank=True)
    hide = models.BooleanField(default=False)
    image = models.ImageField(null=True, blank=True, upload_to='station')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Handle existing records with different sensor_type but same station and channel
        latest_record = StationConfigurationRecordModel.objects.filter(
            station=self.station, channel=self.channel, end_date=None
        ).exclude(sensor_type=self.sensor_type).first()

        if latest_record:
            latest_record.end_date = timezone.now()
            latest_record.save()
        
        # Handle existing records with different channel but same station and sensor_type
        latest_record = StationConfigurationRecordModel.objects.filter(
            station=self.station, sensor_type=self.sensor_type, end_date=None
        ).exclude(channel=self.channel).first()

        if latest_record:
            latest_record.end_date = timezone.now()
            latest_record.save()
        
          # Create new configuration record if none exist with the same station, channel, and sensor_type
        if not StationConfigurationRecordModel.objects.filter(
            station=self.station, sensor_type=self.sensor_type, channel=self.channel, end_date=None
        ).exists() or StationConfigurationRecordModel.objects.filter(
            station=self.station, sensor_type=self.sensor_type, channel=self.channel
        ).exclude(end_date=None).exists():
            StationConfigurationRecordModel.objects.create(
                station=self.station,
                channel=self.channel,
                sensor_type=self.sensor_type,
                created_at=timezone.now(),
                end_date=None
            )


    def delete(self, *args, **kwargs):
        # Custom delete logic
        record = StationConfigurationRecordModel.objects.filter(
            station=self.station, sensor_type=self.sensor_type, channel=self.channel, end_date=None
        ).first()
        
        if record:
            record.end_date = timezone.now()
            record.save()
        
        # Perform the actual deletion
        super().delete(*args, **kwargs)

    class Meta:
        unique_together = (
            ('station', 'channel'),
            ('station', 'sensor_type'),
        )
        db_table = "pdam_station_configuration"

class StationConfigurationRecordModel(models.Model):
    station = models.ForeignKey(StationModel, on_delete=models.CASCADE)
    sensor_type = models.ForeignKey(SensorTypeModel, on_delete=models.CASCADE)
    channel = models.ForeignKey(ChannelModel, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)  

    class Meta:
        db_table = "pdam_station_configuration_record"  

    
@receiver(pre_save, sender=StationConfigurationModel)
def update_modified_time(sender, instance, **kwargs):
    instance.modified_at = timezone.now()


@receiver(pre_delete, sender=StationConfigurationModel)
def handle_delete(sender, instance, **kwargs):
    # Custom delete logic
    record = StationConfigurationRecordModel.objects.filter(
        station=instance.station, sensor_type=instance.sensor_type, channel=instance.channel, end_date=None
    ).first()
    
    if record:
        record.end_date = timezone.now()
        record.save()


# this table is for DS requirements
class SensorDataReqModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    time = models.DateTimeField()
    data = models.FloatField()
    sensor_type = models.ForeignKey(SensorTypeModel, on_delete=models.SET_NULL, blank=True, null=True)
    station = models.ForeignKey(StationModel, on_delete=models.SET_NULL,blank=True, null=True)
    iteration = models.IntegerField()
    channel = models.ForeignKey(ChannelModel, on_delete=models.SET_NULL,blank=True, null=True)
    status = models.PositiveIntegerField()

    class Meta:
        unique_together = ("station","time","sensor_type","channel","data")
        db_table = "pdam_sensor_data_req"


DAYS_OF_WEEK = (
    (1, "Monday"),
    (2, "Tuesday"),
    (3, "Wednesday"),
    (4, "Thursday"),
    (5, "Friday"),
    (6, "Saturday"),
    (7, "Sunday"),
)
class ThresholdSensorModel(models.Model):
    station = models.ForeignKey(StationModel, on_delete=models.CASCADE)
    hour = models.PositiveIntegerField()
    minute = models.PositiveIntegerField()
    day = models.PositiveIntegerField(choices=DAYS_OF_WEEK)
    min = models.FloatField()
    max = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "pdam_threshold_sensor"

@receiver(pre_save, sender=ThresholdSensorModel)
def update_modified_time(sender, instance, **kwargs):
    instance.modified_at = timezone.now()



NOTIF_TYPE = (
    (1, "Threshold"),
    (2, "Missing")
)
class TelegramNotificationModel(models.Model):
    station = models.ForeignKey(StationModel, on_delete=models.SET_NULL, blank=True, null=True)
    # maintenance_start_date = models.DateTimeField()
    # maintenance_end_date = models.DateTimeField()
    is_sent= models.BooleanField(default=False)
    notif_type = models.PositiveBigIntegerField(choices=NOTIF_TYPE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pdam_telegram_notification"

class PublishThresholdModel(models.Model):
    station = models.ForeignKey(StationModel, on_delete=models.CASCADE)
    day = models.PositiveIntegerField(choices=DAYS_OF_WEEK)
    hour = models.PositiveIntegerField()
    message = models.CharField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)
    receive_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "pdam_publish_threshold"


class PublishResendModel(models.Model):
    station = models.ForeignKey(StationModel, on_delete=models.CASCADE)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)
    
    class Meta:
        db_table = "pdam_publish_resend"