from django.contrib import admin
from django.urls import path, include
from .views import (UserView,SignInView, ProfileView,LogoutView,
                    UserRoleView, BalaiView) 

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path('user/', UserView.as_view()),
    path('user/<int:pk>/', UserView.as_view()),
    path('signin/', SignInView.as_view()),
    path('signout/', LogoutView.as_view()),
    # path('profile/',ProfileView.as_view()),
    path("refresh_token/",TokenRefreshView.as_view()),  
    # path('profile/<int:pk>/',ProfileView.as_view())

    path("role/",UserRoleView.as_view()),
    path("balai/",BalaiView.as_view()),
    # path("organization/", OrganizationView.as_view()),
    # path("organization/<int:pk>/", OrganizationView.as_view())


]
