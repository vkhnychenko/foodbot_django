from django.contrib import admin

from .models import Users, Items, Cart


@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'name', 'username')
    readonly_fields = ('user_id', 'name', 'username')


admin.site.register(Items)
admin.site.register(Cart)
