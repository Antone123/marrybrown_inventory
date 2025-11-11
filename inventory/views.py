from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .models import Supplier, Item, RequestList, RequestItem


def _get_or_create_request_list(request, *, create=True):
    """Return the shared active request list, creating one if allowed."""
    existing_list = (
        RequestList.objects.filter(is_completed=False)
        .order_by('created_at')
        .first()
    )

    if existing_list or not create or not request.user.is_authenticated:
        return existing_list

    staff_name = request.user.get_full_name() or request.user.get_username()
    return RequestList.objects.create(user=request.user, staff_name=staff_name)

@login_required
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(
        request,
        'inventory/supplier_list.html',
        {
            'suppliers': suppliers,
            'staff_display': request.user.get_full_name() or request.user.get_username(),
        },
    )

# 2️⃣ Items of a specific supplier
@login_required
def item_list(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    items = Item.objects.filter(supplier=supplier)
    error = None

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'create_item':
            if not request.user.is_staff:
                messages.error(request, 'Only staff users can add inventory items.')
                return redirect('item_list', supplier_id=supplier.id)

            name = request.POST.get('new_item_name', '').strip()
            stock_value = request.POST.get('new_item_stock', '0')
            category = request.POST.get('new_item_category', '').strip()
            try:
                stock = int(stock_value)
            except (TypeError, ValueError):
                stock = -1

            if not name:
                messages.error(request, 'Item name is required.')
            elif stock < 0:
                messages.error(request, 'Stock must be zero or greater.')
            elif category not in dict(Item.CATEGORY_CHOICES) and supplier.name.lower() == 'mb warehouse':
                messages.error(request, 'Please pick a valid category.')
            else:
                Item.objects.create(
                    supplier=supplier,
                    name=name,
                    current_stock=stock,
                    category=category if category in dict(Item.CATEGORY_CHOICES) else '',
                )
                messages.success(request, f"Added new item '{name}' with stock {stock}.")
            return redirect('item_list', supplier_id=supplier.id)

        request_list = _get_or_create_request_list(request)
        if request_list is None:
            return redirect('supplier_list')
        try:
            item_id = int(request.POST.get('item_id', 0))
            qty = int(request.POST.get('quantity', 0))
        except (TypeError, ValueError):
            item_id = 0
            qty = 0

        item = Item.objects.filter(id=item_id, supplier=supplier).first()

        if not item:
            error = "Invalid item selected."
        elif qty < 1:
            error = "Quantity must be at least 1."
        elif qty > item.current_stock:
            error = "Requested quantity exceeds current stock."
        else:
            request_item, _ = RequestItem.objects.get_or_create(
                request_list=request_list,
                item=item,
                defaults={'quantity': 0},
            )
            request_item.quantity += qty
            request_item.save()
            messages.success(request, f"Added {qty} x {item.name} to the shared list.")
            return redirect('item_list', supplier_id=supplier.id)

    if supplier.name.lower() == 'mb warehouse':
        item_groups = {
            'Ingredients': items.filter(category='ingredient'),
            'Packaging': items.filter(category='packaging'),
        }
    else:
        item_groups = None

    context = {'supplier': supplier, 'items': items, 'error': error, 'item_groups': item_groups}
    return render(request, 'inventory/item_list.html', context)

# 3️⃣ View the cart / request list
@login_required
def cart_view(request):
    request_list = _get_or_create_request_list(request, create=False)
    error = request.session.pop('cart_error', None)

    if request_list:
        cart_items = request_list.items.select_related('item')
        total_items = sum(item.quantity for item in cart_items)
    else:
        cart_items = []
        total_items = 0

    return render(
        request,
        'inventory/cart.html',
        {
            'cart_items': cart_items,
            'total_items': total_items,
            'request_list': request_list,
            'error': error,
        },
    )

# 4️⃣ Complete request and deduct stock
@login_required
def complete_request(request):
    if request.method != 'POST':
        return redirect('cart_view')

    request_list = _get_or_create_request_list(request, create=False)

    if not request_list or request_list.items.count() == 0:
        request.session['cart_error'] = 'Your cart is empty.'
        return redirect('cart_view')

    with transaction.atomic():
        request_items = list(request_list.items.select_related('item'))

        for request_item in request_items:
            item = request_item.item
            if request_item.quantity > item.current_stock:
                request.session['cart_error'] = f"Not enough stock for {item.name}."
                return redirect('cart_view')

        for request_item in request_items:
            item = request_item.item
            item.current_stock -= request_item.quantity
            item.save()

        request_list.is_completed = True
        request_list.save()

    return redirect('supplier_list')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def update_cart_item(request, item_id):
    if request.method != 'POST':
        return redirect('cart_view')

    request_list = _get_or_create_request_list(request, create=False)
    if not request_list:
        request.session['cart_error'] = 'No active cart to update.'
        return redirect('cart_view')

    request_item = get_object_or_404(RequestItem, id=item_id, request_list=request_list)

    try:
        new_quantity = int(request.POST.get('quantity', request_item.quantity))
    except (TypeError, ValueError):
        new_quantity = request_item.quantity

    if new_quantity < 1:
        item_name = request_item.item.name
        request_item.delete()
        messages.info(request, f"Removed {item_name} from the list.")
    else:
        request_item.quantity = new_quantity
        request_item.save()
        messages.success(request, f"Updated {request_item.item.name} to {new_quantity}.")

    return redirect('cart_view')
