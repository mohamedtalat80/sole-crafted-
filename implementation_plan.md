# Inventory Check Strategy — Cart, Order & Order Fulfilment

## Background

The inventory system already has a solid foundation:
- **`StockEntry`** — an immutable log of every movement (IN / OUT / ADJUSTMENT)
- **`InventorySnapshot`** — the live `quantity_on_hand` per `(product, size, colour)` SKU, always kept in sync by the service
- **`InventoryService`** — exposes `record_stock_in`, `record_stock_out`, `record_adjustment` and enforces the "no negative stock" rule before any OUT movement

There is **no `cart` or `orders` app yet**. Both need to be built, and inventory integration must be wired into them at the right points.

---

## Answer: When Do We Check Inventory?

> **Short answer: Check (soft) at Cart, check + reserve (hard) at Order placement, and deduct at Order fulfilment.**

| Stage | Action | Inventory Effect |
|---|---|---|
| **Product detail page** | Show `quantity_on_hand` via existing API | Read-only, no change |
| **Add to Cart** | Soft availability check — show warning if stock ≤ 0 | **No reservation**, no deduction |
| **Checkout / Place Order** | Hard availability check **inside a DB transaction** | Reserve stock → `quantity_on_hand` decremented atomically |
| **Order Cancelled / Rejected** | Reverse the reservation | Stock returned via `record_stock_in` |
| **Order Fulfilled / Shipped** | No extra deduction needed (already done at placement) | Optionally record a `StockEntry(OUT)` with the order number for audit trail |

### Why NOT reserve at Cart?
- Carts can be abandoned for hours/days — reserving at that point would block real buyers
- Soft check (UI warning) at cart add is enough UX feedback
- Hard check at checkout is the safety gate — this is the industry-standard approach (used by Nike, Adidas, etc.)

---

## Proposed Changes

### 1 — `apps/inventory` (extend existing service)

#### [MODIFY] [inventory_service.py](file:///e:/work%20projects/shoe_ecommerce/apps/inventory/services/inventory_service.py)

Add two new public methods the order service will call:

```python
def check_availability(self, product_id, size_id, colour_id, quantity) -> bool:
    """Read-only check: returns True if enough stock exists."""

def reserve_stock(self, product_id, size_id, colour_id, quantity, order_ref, recorded_by):
    """
    Atomically checks AND deducts stock for a confirmed order.
    Raises ApplicationError if insufficient.
    Records a StockEntry(OUT, note=f"Order #{order_ref}").
    """

def release_stock(self, product_id, size_id, colour_id, quantity, order_ref, recorded_by):
    """
    Returns stock when an order is cancelled.
    Records a StockEntry(IN, note=f"Cancelled Order #{order_ref}").
    """
```

#### [MODIFY] [inventory_repository_interface.py](file:///e:/work%20projects/shoe_ecommerce/apps/inventory/interfaces/inventory_repository_interface.py)

Add `check_availability` signature to the interface.

---

### 2 — `apps/cart` **[NEW APP]**

A lightweight cart backed by the database (user-linked, survives sessions).

#### [NEW] `apps/cart/models.py`

```
Cart
  - user (FK → User, unique)
  - created_at, updated_at

CartItem
  - cart (FK → Cart)
  - product (FK → Product)
  - size (FK → Size)
  - colour (FK → Colour)
  - quantity (PositiveIntegerField)
  - unique_together: (cart, product, size, colour)
```

#### [NEW] `apps/cart/services/cart_service.py`

Key methods:
- `add_item(user, product_id, size_id, colour_id, quantity)` — **soft availability check** via `InventoryService.check_availability()`. Raises a non-blocking warning (or a 409 with `in_stock: false`) if stock is 0.
- `update_item_quantity(...)` — same soft check
- `remove_item(...)`
- `get_cart(user)` — returns cart with items enriched with current `quantity_on_hand`
- `clear_cart(user)`

#### [NEW] `apps/cart/views.py` + `urls.py`

Standard CRUD endpoints:

| Method | URL | Description |
|---|---|---|
| GET | `/api/cart/` | Get my cart |
| POST | `/api/cart/items/` | Add item |
| PATCH | `/api/cart/items/{id}/` | Update quantity |
| DELETE | `/api/cart/items/{id}/` | Remove item |

---

### 3 — `apps/orders` **[NEW APP]**

#### [NEW] `apps/orders/models.py`

```
Order
  - user (FK → User)
  - status: PENDING → CONFIRMED → SHIPPED → DELIVERED | CANCELLED
  - total_price (DecimalField)
  - shipping_address (TextField / FK → Address)
  - created_at, updated_at

OrderItem
  - order (FK → Order)
  - product (FK → Product)
  - size (FK → Size)
  - colour (FK → Colour)
  - quantity (PositiveIntegerField)
  - unit_price (DecimalField, snapshot of price at order time)
```

#### [NEW] `apps/orders/services/order_service.py`

**`place_order(user)` — the critical method:**

```python
@transaction.atomic
def place_order(self, user):
    cart = cart_service.get_cart(user)
    if not cart.items.exists():
        raise ApplicationError("Cart is empty")

    order = Order.objects.create(user=user, status=Order.Status.PENDING)

    for item in cart.items.select_related(...):
        # HARD inventory check + deduction — all in one DB transaction
        inventory_service.reserve_stock(
            product_id=item.product_id,
            size_id=item.size_id,
            colour_id=item.colour_id,
            quantity=item.quantity,
            order_ref=order.id,
            recorded_by=user,
        )
        OrderItem.objects.create(
            order=order,
            product=item.product,
            size=item.size,
            colour=item.colour,
            quantity=item.quantity,
            unit_price=item.product.price,
        )

    order.status = Order.Status.CONFIRMED
    order.save()
    cart_service.clear_cart(user)
    return order
```

If **any** `reserve_stock` call raises (insufficient stock), the entire `@transaction.atomic` block rolls back — no partial orders, no negative stock.

**`cancel_order(order_id, user)` — reversal:**

```python
@transaction.atomic
def cancel_order(self, order_id, user):
    order = ...  # fetch & validate ownership
    if order.status not in (PENDING, CONFIRMED):
        raise ApplicationError("Cannot cancel at this stage")

    for item in order.items.all():
        inventory_service.release_stock(
            product_id=item.product_id,
            ...
            order_ref=order.id,
            recorded_by=user,
        )

    order.status = Order.Status.CANCELLED
    order.save()
```

#### [NEW] `apps/orders/views.py` + `urls.py`

| Method | URL | Description |
|---|---|---|
| POST | `/api/orders/` | Place order (from cart) |
| GET | `/api/orders/` | List my orders |
| GET | `/api/orders/{id}/` | Order detail |
| POST | `/api/orders/{id}/cancel/` | Cancel order |
| PATCH | `/api/orders/{id}/status/` | Admin: update status |

---

## Open Questions

> [!IMPORTANT]
> **Q1 — Stock visibility on product page**: Should we expose `quantity_on_hand` to customers on the product detail page (so they can see "Only 3 left!")? Or just a simple `in_stock: true/false` flag?

> [!IMPORTANT]
> **Q2 — Cart behaviour when stock runs out**: If a customer has an item in their cart and another customer buys the last unit before they checkout, should we:
> - **Option A**: Block checkout with a clear error message listing the out-of-stock items *(recommended)*
> - **Option B**: Automatically remove the item from their cart

> [!IMPORTANT]
> **Q3 — Shipping address**: Should the `Order` model have a free-text address field, or link to a separate `Address` model on the `users` app (allowing saved addresses)?

> [!IMPORTANT]
> **Q4 — Payment**: Is payment integration (Stripe, PayPal, etc.) in scope? If yes, the `place_order` flow should only reserve stock *after* payment is confirmed, not before. This changes the flow significantly.

---

## Verification Plan

### Automated Tests
- `pytest apps/cart/tests/` — unit tests for soft availability check
- `pytest apps/orders/tests/` — integration tests for `place_order`:
  - Happy path: stock deducted correctly after order placement
  - Race condition: two concurrent orders for the last unit — only one should succeed
  - Cancellation: stock returned correctly

### Manual Verification
- Admin stocks in 2 units of a SKU
- Customer adds 2 to cart → succeeds
- Customer places order → stock goes to 0, `StockEntry(OUT)` created
- Customer tries to add same item again → soft warning "out of stock"
- Customer cancels order → stock returns to 2, `StockEntry(IN)` created
