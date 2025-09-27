from django.contrib import admin
from .models import User, Guardian, Dependent, GuardianMessageDefault, AppSettings

# Register your models here.
admin.site.register(User)
admin.site.register(Guardian)
admin.site.register(Dependent)
admin.site.register(AppSettings)
admin.site.register(GuardianMessageDefault)