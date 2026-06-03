"""
ProductDynamicFieldsMixin — adds is_favorite, is_most_booked, is_top_rated,
is_trip, and is_rent to any Trip or Rent read serializer without N+1 queries.

Usage
-----
Inherit as the *first* base class — no Meta.fields changes, no view changes:

    class TripSerializer(ProductDynamicFieldsMixin, StrictModelSerializer):
        ...
        class Meta:
            model = Trip
            fields = [...]   # leave as-is; the five fields are injected automatically

Performance guarantees
----------------------
All five fields use a request-scoped cache stored on ``request._dynamic_fields_cache``.
The cache is populated lazily — each key is computed at most once per request,
regardless of how many items are serialized in the same response:

* is_favorite      One SELECT of the user's favorited IDs per product type
                   (trip / rent).  Each item's check is an O(1) frozenset lookup.
                   Anonymous users short-circuit immediately (no DB hit).

* is_most_booked / is_top_rated
                   One COUNT(bookings) query + one AVG(reviews__rating) query
                   per model type per request.  Each item's check is O(1).

* is_trip / is_rent
                   Pure isinstance checks — no DB access ever.
"""
from __future__ import annotations

from django.db.models import Avg, Count
from rest_framework import serializers

