from django.urls import path
from . import views

urlpatterns = [
    path('', views.supplier_list),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('supplier/<int:supplier_id>/', views.item_list, name='item_list'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/item/<int:item_id>/update/', views.update_cart_item, name='update_cart_item'),
    path('complete/', views.complete_request, name='complete_request'),
]
