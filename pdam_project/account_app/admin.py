from django.contrib import admin
from .models import User, BalaiModel
from pdam_project.admin import admin_site
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import User, BalaiModel
# # Register your models here.
# class UserAdmin(admin.ModelAdmin):
#     list_display = ('id','username', 'email',"balai", 'first_name', 'last_name', 'role', 'is_staff',"is_superuser","created_by","last_login")
#     list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups',"balai")
#     model = User

class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ('id','username', 'email', "get_balai",'first_name', 'last_name', 'role', 'is_staff',"is_superuser","created_by","last_login")
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email',"get_balai","balai")}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Role', {'fields': ('role',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'role','balai', 'password1', 'password2'),
        }),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')

    readonly_fields = ('get_balai',)

    def get_balai(self, obj):
        return obj.balai.balai_name if obj.balai else None

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'Balai':
            kwargs['queryset'] = BalaiModel.objects.all()
            kwargs['label'] = 'Balai'
            kwargs['empty_label'] = 'Select an Organization'
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class BalaiAdmin(admin.ModelAdmin):
    list_display = ("id","balai_name","created_at")
    model = BalaiModel



admin_site.register(User, UserAdmin)
admin_site.register(BalaiModel, BalaiAdmin)