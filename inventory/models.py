from django.conf import settings
from django.db import models

# Suppliers
class Supplier(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# Items for each supplier
class Item(models.Model):
    CATEGORY_CHOICES = [
        ('ingredient', 'Ingredient'),
        ('packaging', 'Packaging'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    current_stock = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, blank=True)

    def __str__(self):
        return self.name

# Staff requests (the “cart” list)
class RequestList(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    staff_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.staff_name} - {self.created_at}"

# Individual items in a staff request
class RequestItem(models.Model):
    request_list = models.ForeignKey(RequestList, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.item.name} ({self.quantity})"
