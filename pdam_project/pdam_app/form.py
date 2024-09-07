from .models import RawMessagemodel, SensorTypeModel ,StationConfigurationModel, ThresholdSensorModel, StationModel
from django import forms
from django_svg_image_form_field import SvgAndImageFormField


class RawMessageForm(forms.ModelForm):
    class Meta:
        model = RawMessagemodel
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize the queryset for the dropdown fields to display human-readable names
        # self.fields['station'].widget.choices = [(station.id, station.station_name) for station in self.fields['station'].queryset]
       
class SensorTypeForm(forms.ModelForm):
    class Meta:
        model = SensorTypeModel
        fields = "__all__"  
        field_classes = {
            'sensor_icon': SvgAndImageFormField,
        }

class StationConfigurationForm(forms.ModelForm):
    class Meta:
        model = StationConfigurationModel
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize the queryset for the dropdown fields to display human-readable names
        self.fields['station'].widget.choices = [(station.id, station.topic) for station in self.fields['station'].queryset]
        self.fields['sensor_type'].widget.choices = [(sensor_type.id, sensor_type.sensor_name) for sensor_type in self.fields['sensor_type'].queryset]
        self.fields['channel'].widget.choices = [(channel.id, channel.channel_label) for channel in self.fields['channel'].queryset]


class ThreshodSensorForm(forms.ModelForm):
    class Meta:
        model = ThresholdSensorModel
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize the queryset for the dropdown fields to display human-readable names
        self.fields['station'].widget.choices = [(station.id, station.topic) for station in self.fields['station'].queryset]
        

class StationForm(forms.ModelForm):
    class Meta:
        model = StationModel
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize the queryset for the dropdown fields to display human-readable names
        self.fields['logger_type'].widget.choices = [(logger_type.id, logger_type.logger_ver) for logger_type in self.fields['logger_type'].queryset]
        