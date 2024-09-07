from .serializers import UserSerializer,LogoutSerializer,SignInSerializer,UpdateProfileSerializer, BalaiSerializer
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from .token import create_jwt_pair_for_user
from .models import User,BalaiModel
from django.core import serializers
import json
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import get_authorization_header
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import AccessToken
from drf_spectacular.utils import extend_schema
from django.contrib.auth.models import update_last_login
from .pagination import ItemPagination
from django.db.models import Q
from django.shortcuts import get_object_or_404

# views.py
@extend_schema(request=UserSerializer, responses={201: UserSerializer, 400: 'Error'})
class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role == User.GUEST:
            return Response({"messaga":"You dont have permission to perform this action"}, status=status.HTTP_403_FORBIDDEN)
        
        
        # is_staff user
        if request.user.is_staff:
            users_instance = User.objects.all()

        else:
            users_instance = User.objects.filter(balai=request.user.balai)
        # serializers = UserSerializer(instance=users_instance, many=True)

        # search param 
        search = request.GET.get("search")
        if search:
            if request.user.is_staff:
                users_instance = User.objects.filter(
                    Q(username__icontains=search) | 
                    Q(first_name__icontains=search)|
                    Q(last_name__icontains=search) 
                    # Q(email__icontains=search)
                )
            else:
                users_instance = User.objects.filter(oranzation=request.user.balai).filter(
                    Q(username__icontains=search) | 
                    Q(first_name__icontains=search)|
                    Q(last_name__icontains=search) 
                    # Q(email__icontains=search)
                )
        paginator = ItemPagination()
        result_page = paginator.paginate_queryset(users_instance, request, self)
        if result_page is not None:
            serializer = UserSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)
        # return Response({"message":"success", "data":serializers.data}, status=status.HTTP_200_OK)

 
    def post(self, request: Request):
        data = request.data
        user = request.user
        print(user.role, User.SUPERADMIN, User.ADMIN)
        # Check if the request user is superadmin, admin or guest
        if user.role == User.SUPERADMIN:
            allowed_roles = [User.SUPERADMIN, User.ADMIN, User.GUEST]
        elif user.role == User.ADMIN:
            allowed_roles = [User.ADMIN, User.GUEST]
        else:
            return Response({"message": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)
        print(request.data)
        if request.user.is_staff ==False:
            balai = get_object_or_404(BalaiModel,id=data.get('balai'))
            if request.user.balai != balai:
                return Response({"message": "You do not have permission to create user different balai."}, status=status.HTTP_403_FORBIDDEN)


        # Validate the role in the request
        requested_role = data.get('role')
        if requested_role in allowed_roles==False:
            return Response({"message": "You do not have permission to assign this role."}, status=status.HTTP_403_FORBIDDEN)

        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save(created_by=user)
            serializer.save(balai=BalaiModel.objects.get(id=data.get('balai')))
            response = {"message": "User Created Successfully", "data": serializer.data}
            return Response(response, status=status.HTTP_201_CREATED)
        
        return Response({"message":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request: Request, pk: int):
        try:
            user_instance = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        user = request.user

        if request.user.is_staff !=True:
            balai = user.balai
            if request.user.balai != balai:
                return Response({"message": "You do not have permission to edit user different balai."}, status=status.HTTP_403_FORBIDDEN)

            data_balai = get_object_or_404(BalaiModel, id=data.get('balai'))
            if request.user.balai != data_balai:
                return Response({"message": "You do not have permission to edit user to different balai."}, status=status.HTTP_403_FORBIDDEN)

        # Determine the target role either from the request or the current user instance
        requested_role = data.get('role', user_instance.role)
        
        # check does user change them role or not, its not allowed
        if user_instance.id == user.id:
            if user.role !=requested_role:
                return Response({"message":"You cannot change your role"}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if the request user is superadmin, admin or guest
        if user.role == User.SUPERADMIN:
            pass  # Superadmin can change to any role
        elif user.role == User.ADMIN:
            if requested_role == User.SUPERADMIN:
                return Response({"message": "Admins cannot change user role to Superadmin."}, status=status.HTTP_403_FORBIDDEN)
            
            # admin try to change superadmin to other
            if user_instance.role==User.SUPERADMIN:
                return Response({"message": "Admins cannot change Superadmin."}, status=status.HTTP_403_FORBIDDEN)
        
        else:
            return Response({"message": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

        serializer = UserSerializer(user_instance, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response = {"message": "User Updated Successfully", "data": serializer.data}
            return Response(response, status=status.HTTP_200_OK)
        
        return Response({"message":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request,pk):
        try:
            user_instance = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        user = request.user
        
        if user.is_staff !=True:
            if user.balai != user_instance.balai:
                return Response({"message": "You do not have permission to delete user different balai."}, status=status.HTTP_403_FORBIDDEN)

        if user.id == user_instance.id:
            return Response({"message":"You cant delete your account, please contact other Superadmin or Admin"})

        requested_role = user_instance.role
        if user.role == User.SUPERADMIN:
            pass  # Superadmin can change to any role
        elif user.role == User.ADMIN:
            if requested_role == User.SUPERADMIN:
                return Response({"message": "Admins cannot delete Suoeradmin role."}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({"message": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)
        
        user_instance.delete()
        return Response({"message":"success deleted"},status=status.HTTP_204_NO_CONTENT)

class SignInView(APIView):
    @extend_schema(request=SignInSerializer, responses={200: SignInSerializer, 400: 'Error'})
    def post(self, request: Request):
        serializer = SignInSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data["username"]
            password = serializer.validated_data["password"]
        else:
            return Response({"message":serializer.errors},status=status.HTTP_400_BAD_REQUEST)

        user_exist = User.objects.filter(username=username).exists()
        if user_exist is not True:     
            return Response({"message": "username is not exist"}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = authenticate(username=username, password=password)
    
        if user is not None:
            tokens = create_jwt_pair_for_user(user)
            update_last_login(None, user)
            print(dict(user.ROLE_CHOICES).get(user.role))
            # print(dict(user.ROLE_CHOICES))
            # print(User.objects.filter(username=username))
            return Response(data={"message": "Login Successfull",
                                  "username":user.username, 
                                  "balai":{
                                      "id":user.balai.id,
                                      "balai_name":user.balai.balai_name
                                    },
                                    "tokens": tokens,
                                    "role":{"id":user.role,"role_name":dict(user.ROLE_CHOICES).get(user.role)},
                                    "is_staff":user.is_staff}, 
                                    status=status.HTTP_200_OK)

        else:
            return Response(data={"message": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED)
        
        
class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)
    serializers = LogoutSerializer
    
    @extend_schema(request=LogoutSerializer, responses={200: LogoutSerializer, 400: 'Error'})
    def post(self, request):
        serializer = self.serializers(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message":"logout"},status=status.HTTP_205_RESET_CONTENT)
        else:
            return Response({"message":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]    

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except AuthenticationFailed:
            return self.handle_authentication_failed()

    def handle_authentication_failed(self):
        return Response(
            {"message": "Authentication credentials were not provided."},status=status.HTTP_401_UNAUTHORIZED)
    
    def get(self,request,*args, **kwargs):
        try:
            user = request.user        
            user_json = serializers.serialize('json', [user,])
            # Convert JSON string to dictionary
            user_dict = json.loads(user_json)[0]['fields']
            # Return user dictionary as JSON response
            return Response({
                "message":"success",
                # "data":user_dict
                "data":{
                    "profile":{
                        "username":user.username,
                        "instancy":user.instancy,
                        "last_login":user.last_login,
                        "super_user":user.is_superuser,
                        "date_joined":user.date_joined,
                        "modified_date":user.modified_date
                    }
                }
            })
        except Exception as e:
            return Response({"message":"unauthorize"})
    
    def put(self, request):
        user = request.user
        user = User.objects.get(pk=user.id)
       
        serializers = UpdateProfileSerializer(instance=user, data=request.data, context={'request': request}, partial=True)
        if serializers.is_valid():
            user.set_password(request.data.get('password'))
            user.save()
            return Response({
                "message":"sucess",
                "user_id":user.id,
                "user":str(user),
                }
            )
        return Response({"message":serializers.error},status=status.HTTP_400_BAD_REQUEST) 
    

class UserRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_role = request.user.role
        dict_role = dict(User.ROLE_CHOICES)
        if request.user.role ==User.GUEST:
            return Response({"message":dict_role.get(user_role,"unknown")+" role dont have permission to perform this action"}, status=status.HTTP_403_FORBIDDEN)
        roles = [{"id": role[0], "role": role[1]} for role in User.ROLE_CHOICES]
        return Response({"message": "success", "data": roles}, status=status.HTTP_200_OK)
    


@extend_schema(request=BalaiSerializer, responses={201: BalaiSerializer, 400: 'Error'})
class BalaiView(APIView):
    permission_classes = [IsAuthenticated]
    serializer = BalaiSerializer

    def get(self, request, *args, **kwargs):
        if request.user.is_staff:
            instance = BalaiModel.objects.all()
        else:
            instance = BalaiModel.objects.filter(type_name=request.user.balai)
        serializer = self.serializer(instance=instance, many=True)
        return Response({"message":"success", "data": serializer.data},status=status.HTTP_200_OK)
    
    def post(self, request, *args, **kwargs):
        if request.user.is_staff!=True:
            return Response({"message":"You Dont have permission to perform this action"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message":"sucess", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response({"message":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request,pk, *args, **kwargs):
        if request.user.is_staff!=True:
            return Response({"message":"You Dont have permission to perform this action"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            site = BalaiModel.objects.get(pk=pk)
        except BalaiModel.DoesNotExist:
            return Response({"message":"Balai is not exist"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.serializer(instance=site, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save() 
            return Response({"message":"success","data":serializer.data}, status=status.HTTP_201_CREATED)
        
        return Response({"message":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request,pk, *args, **kwargs):
        if request.user.is_staff!=True:
            return Response({"message":"You Dont have permission to perform this action"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            site = BalaiModel.objects.get(pk=pk)
        except BalaiModel.DoesNotExist:
            return Response({"message":"Balai is not exist"}, status=status.HTTP_404_NOT_FOUND)
        
        site.delete()
        return Response({"message":"success deleted"}, status=status.HTTP_204_NO_CONTENT)
        
    
