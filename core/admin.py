from django.contrib import admin
from .models import User, Client, Craftsman, Ads 

# Register your models here.
admin.site.register(User)
admin.site.register(Client)
admin.site.register(Craftsman)
admin.site.register(Ads)