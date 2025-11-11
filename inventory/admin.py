
# Register your models here.
from django.contrib import admin
from .models import Supplier, Item, RequestList, RequestItem

admin.site.register(Supplier)
admin.site.register(Item)
admin.site.register(RequestList)
admin.site.register(RequestItem)
