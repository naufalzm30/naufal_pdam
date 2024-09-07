from rest_framework import serializers
from .models import User , BalaiModel
from rest_framework.validators import ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.shortcuts import get_object_or_404

    
# serializers.py
class UserSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    balai = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', "balai",'password', 'role', 'role_name', 'created_by',"is_staff"]
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def get_created_by(self, obj):
        if obj.created_by:
            return obj.created_by.username
        return None
    
    def get_balai(self, obj):
        if obj.balai:
            return {
                'id': obj.balai.id,
                'balai_name': obj.balai.balai_name
            }
            # return obj.balai.balai_name
        return None

    def get_role_name(self, obj):
        return obj.get_role_display()
    
    def to_internal_value(self, data):
        internal_value = super().to_internal_value(data)
        organization_id = data.get('balai')
        try:
            organization = BalaiModel.objects.get(id=organization_id)
        except BalaiModel.DoesNotExist:
            raise serializers.ValidationError({'balai': 'Balai with this ID does not exist.'})
        internal_value['balai'] = organization
        return internal_value

    
    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            # email=validated_data['email'],
            # first_name=validated_data['first_name'],
            # last_name=validated_data['last_name'],
            role=validated_data['role'],
            # organization=validated_data['organization']
        )
        user.set_password(validated_data['password'])
        if 'created_by' in validated_data:
            user.created_by = validated_data['created_by']
        user.save()
        return user
    
    def validate_username(self, value):
        # Check if the username already exists
        if self.instance is None or self.instance.username != value:
            if User.objects.filter(username=value).exists():
                raise serializers.ValidationError("A user with this username already exists.")
            
        # if self.instance is None or self.instance.email != value:
        #     if User.objects.filter(email=value).exists():
        #         raise serializers.ValidationError("A user with this email already exists.")
        return value

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            if attr == 'password':
                instance.set_password(value)
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            self.fail('invalid_token')
    
    # Define custom error messages
    default_error_messages = {
        'invalid_token': 'Token is invalid or expired',
    }

class SignInSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)
    password = serializers.CharField(max_length=20)


class UpdateProfileSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    repassword = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['username', 'password','repassword']
        extra_kwargs = {'password': {'write_only': True}}
    
    def validate_username(self, value):
        user = self.context['request'].user
        if User.objects.filter(username=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("User with this username already exists.")
        return value

    # def validate_email(self, value):
    #     user = self.context['request'].user
    #     if User.objects.filter(email=value).exclude(id=user.id).exists():
    #         raise serializers.ValidationError("User with this email already exists.")
    #     return value

    def validate(self, data):
        if 'password' in data and data['password'] != data.get('repassword'):
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return data


    def update(self, instance, validated_data):
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
            validated_data.pop('password')
            validated_data.pop('repassword', None)
        return super().update(instance, validated_data)
    
class BalaiSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalaiModel
        fields = ("id", "balai_name")