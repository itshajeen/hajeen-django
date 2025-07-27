from django.contrib import admin
from .models import User, Guardian, Dependent 

# Register your models here.
admin.site.register(User)
admin.site.register(Guardian)
admin.site.register(Dependent)
