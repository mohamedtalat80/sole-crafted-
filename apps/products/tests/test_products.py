from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.exceptions import NotFoundError

_PRODUCT_SERVICE_PATCH = "apps.products.views._get_product_service"
_CATEGORY_SERVICE_PATCH = "apps.products.views._get_category_service"
_TAG_SERVICE_PATCH = "apps.products.views._get_tag_service"
_COLOUR_SERVICE_PATCH = "apps.products.views._get_colour_service"
_SIZE_SERVICE_PATCH = "apps.products.views._get_size_service"


def _make_product(**kwargs):
    p = MagicMock()
    p.pk = kwargs.get("pk", 1)
    p.id = p.pk
    p.name = kwargs.get("name", "Air Max")
    p.brand = kwargs.get("brand", "Nike")
    p.description = kwargs.get("description", "A shoe.")
    p.price = kwargs.get("price", "199.99")
    p.discount_percentage = kwargs.get("discount_percentage", 0)
    p.is_active = kwargs.get("is_active", True)
    p.main_image = None
    p.category = MagicMock(id=1, name="Running", translations=MagicMock(all=lambda: []))
    p.sizes = MagicMock(all=lambda: [])
    p.colors = MagicMock(all=lambda: [])
    p.tags = MagicMock(all=lambda: [])
    p.images = MagicMock(all=lambda: [])
    p.translations = MagicMock(all=lambda: [])
    p.created_at = "2026-01-01T00:00:00Z"
    p.updated_at = "2026-01-01T00:00:00Z"
    return p


def _make_category(**kwargs):
    c = MagicMock()
    c.pk = kwargs.get("pk", 1)
    c.id = c.pk
    c.name = kwargs.get("name", "Running")
    c.is_active = kwargs.get("is_active", True)
    c.translations = MagicMock(all=lambda: [])
    c.created_at = "2026-01-01T00:00:00Z"
    c.updated_at = "2026-01-01T00:00:00Z"
    return c


def _make_tag(**kwargs):
    t = MagicMock()
    t.pk = kwargs.get("pk", 1)
    t.id = t.pk
    t.name = kwargs.get("name", "Sport")
    t.is_active = kwargs.get("is_active", True)
    t.translations = MagicMock(all=lambda: [])
    t.created_at = "2026-01-01T00:00:00Z"
    t.updated_at = "2026-01-01T00:00:00Z"
    return t


def _make_colour(**kwargs):
    c = MagicMock()
    c.pk = kwargs.get("pk", 1)
    c.id = c.pk
    c.name = kwargs.get("name", "Black")
    c.translations = MagicMock(all=lambda: [])
    return c


def _make_size(**kwargs):
    s = MagicMock()
    s.pk = kwargs.get("pk", 1)
    s.id = s.pk
    s.name = kwargs.get("name", "42")
    return s


def _assert_success(test, response, status_code=200):
    test.assertEqual(response.status_code, status_code)
    test.assertTrue(response.data["status"])


def _assert_error(test, response, status_code):
    test.assertEqual(response.status_code, status_code)
    test.assertFalse(response.data["status"])


# ---------------------------------------------------------------------------
# Product tests
# ---------------------------------------------------------------------------

class ProductPublicListViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_public_list_returns_200(self):
        with patch(_PRODUCT_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.list_available_products.return_value = [_make_product()]
            response = self.client.get("/api/products/")
        _assert_success(self, response, 200)

    def test_public_list_empty(self):
        with patch(_PRODUCT_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.list_available_products.return_value = []
            response = self.client.get("/api/products/")
        _assert_success(self, response, 200)


class AdminProductViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = MagicMock()
        self.admin.is_authenticated = True
        self.admin.account_type = "admin"
        self.client.force_authenticate(user=self.admin)

    # --- list ---

    def test_list_returns_200(self):
        with patch(_PRODUCT_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_all_products.return_value = [_make_product()]
            response = self.client.get("/api/admin/products/")
        _assert_success(self, response, 200)

    def test_list_requires_admin(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/admin/products/")
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_list_rejects_non_admin(self):
        user = MagicMock()
        user.is_authenticated = True
        user.account_type = "customer"
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/admin/products/")
        _assert_error(self, response, status.HTTP_403_FORBIDDEN)

    # --- create ---

    def test_create_returns_201(self):
        product = _make_product()
        with patch(_PRODUCT_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.create_product.return_value = product
            response = self.client.post("/api/admin/products/", {
                "name": "Air Max", "brand": "Nike", "description": "A shoe.",
                "price": "199.99", "category": 1,
            }, format="json")
        _assert_success(self, response, 201)

    def test_create_missing_required_field_returns_400(self):
        response = self.client.post("/api/admin/products/", {"brand": "Nike"}, format="json")
        _assert_error(self, response, 400)

    def test_create_unknown_field_returns_400(self):
        response = self.client.post("/api/admin/products/", {
            "name": "Air Max", "brand": "Nike", "description": "A shoe.",
            "price": "199.99", "category": 1, "unknown_field": "x",
        }, format="json")
        _assert_error(self, response, 400)

    # --- retrieve ---

    def test_retrieve_returns_200(self):
        product = _make_product()
        with patch(_PRODUCT_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_product.return_value = product
            response = self.client.get("/api/admin/products/1/")
        _assert_success(self, response, 200)

    def test_retrieve_not_found_returns_error(self):
        with patch(_PRODUCT_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_product.side_effect = NotFoundError(message="Product not found")
            response = self.client.get("/api/admin/products/99/")
        self.assertFalse(response.data["status"])

    # --- partial_update ---

    def test_update_returns_200(self):
        product = _make_product(name="Air Max Pro")
        with patch(_PRODUCT_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.update_product.return_value = product
            response = self.client.patch("/api/admin/products/1/", {"name": "Air Max Pro"}, format="json")
        _assert_success(self, response, 200)

    def test_update_invalid_data_returns_400(self):
        response = self.client.patch("/api/admin/products/1/", {"price": "not-a-number"}, format="json")
        _assert_error(self, response, 400)

    # --- destroy ---

    def test_delete_returns_200(self):
        with patch(_PRODUCT_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.delete_product.return_value = None
            response = self.client.delete("/api/admin/products/1/")
        _assert_success(self, response, 200)

    def test_delete_not_found_returns_error(self):
        with patch(_PRODUCT_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.delete_product.side_effect = NotFoundError(message="Product not found")
            response = self.client.delete("/api/admin/products/99/")
        self.assertFalse(response.data["status"])

    # --- toggle_active ---

    def test_toggle_active_returns_200(self):
        with patch(_PRODUCT_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.toggle_active_product.return_value = False
            response = self.client.post("/api/admin/products/1/toggle-active/")
        _assert_success(self, response, 200)
        self.assertEqual(response.data["data"]["is_active"], False)


# ---------------------------------------------------------------------------
# Category tests
# ---------------------------------------------------------------------------

class AdminCategoryViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        admin = MagicMock()
        admin.is_authenticated = True
        admin.account_type = "admin"
        self.client.force_authenticate(user=admin)

    def test_list_returns_200(self):
        with patch(_CATEGORY_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_all_categories.return_value = [_make_category()]
            response = self.client.get("/api/admin/categories/")
        _assert_success(self, response, 200)

    def test_create_returns_201(self):
        with patch(_CATEGORY_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.create_category.return_value = _make_category()
            response = self.client.post("/api/admin/categories/", {"name": "Running"}, format="json")
        _assert_success(self, response, 201)

    def test_create_missing_name_returns_400(self):
        response = self.client.post("/api/admin/categories/", {}, format="json")
        _assert_error(self, response, 400)

    def test_retrieve_returns_200(self):
        with patch(_CATEGORY_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_category.return_value = _make_category()
            response = self.client.get("/api/admin/categories/1/")
        _assert_success(self, response, 200)

    def test_retrieve_not_found(self):
        with patch(_CATEGORY_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_category.side_effect = NotFoundError(message="Category not found")
            response = self.client.get("/api/admin/categories/99/")
        self.assertFalse(response.data["status"])

    def test_update_returns_200(self):
        with patch(_CATEGORY_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.update_category.return_value = _make_category(name="Trail")
            response = self.client.patch("/api/admin/categories/1/", {"name": "Trail"}, format="json")
        _assert_success(self, response, 200)

    def test_delete_returns_200(self):
        with patch(_CATEGORY_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.delete_category.return_value = None
            response = self.client.delete("/api/admin/categories/1/")
        _assert_success(self, response, 200)

    def test_toggle_active_returns_200(self):
        with patch(_CATEGORY_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.toggle_active_category.return_value = False
            response = self.client.post("/api/admin/categories/1/toggle-active/")
        _assert_success(self, response, 200)
        self.assertEqual(response.data["data"]["is_active"], False)

    def test_list_requires_admin(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/admin/categories/")
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


# ---------------------------------------------------------------------------
# Tag tests
# ---------------------------------------------------------------------------

class AdminTagViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        admin = MagicMock()
        admin.is_authenticated = True
        admin.account_type = "admin"
        self.client.force_authenticate(user=admin)

    def test_list_returns_200(self):
        with patch(_TAG_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_all_tags.return_value = [_make_tag()]
            response = self.client.get("/api/admin/tags/")
        _assert_success(self, response, 200)

    def test_create_returns_201(self):
        with patch(_TAG_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.create_tag.return_value = _make_tag()
            response = self.client.post("/api/admin/tags/", {"name": "Sport"}, format="json")
        _assert_success(self, response, 201)

    def test_create_missing_name_returns_400(self):
        response = self.client.post("/api/admin/tags/", {}, format="json")
        _assert_error(self, response, 400)

    def test_retrieve_returns_200(self):
        with patch(_TAG_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_tag.return_value = _make_tag()
            response = self.client.get("/api/admin/tags/1/")
        _assert_success(self, response, 200)

    def test_retrieve_not_found(self):
        with patch(_TAG_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_tag.side_effect = NotFoundError(message="Tag not found")
            response = self.client.get("/api/admin/tags/99/")
        self.assertFalse(response.data["status"])

    def test_update_returns_200(self):
        with patch(_TAG_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.update_tag.return_value = _make_tag(name="Casual")
            response = self.client.patch("/api/admin/tags/1/", {"name": "Casual"}, format="json")
        _assert_success(self, response, 200)

    def test_delete_returns_200(self):
        with patch(_TAG_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.delete_tag.return_value = None
            response = self.client.delete("/api/admin/tags/1/")
        _assert_success(self, response, 200)

    def test_toggle_active_returns_200(self):
        with patch(_TAG_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.toggle_active_tag.return_value = True
            response = self.client.post("/api/admin/tags/1/toggle-active/")
        _assert_success(self, response, 200)
        self.assertEqual(response.data["data"]["is_active"], True)


# ---------------------------------------------------------------------------
# Colour tests
# ---------------------------------------------------------------------------

class AdminColourViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        admin = MagicMock()
        admin.is_authenticated = True
        admin.account_type = "admin"
        self.client.force_authenticate(user=admin)

    def test_list_returns_200(self):
        with patch(_COLOUR_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_all_colours.return_value = [_make_colour()]
            response = self.client.get("/api/admin/colours/")
        _assert_success(self, response, 200)

    def test_create_returns_201(self):
        with patch(_COLOUR_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.create_colour.return_value = _make_colour()
            response = self.client.post("/api/admin/colours/", {"name": "Black"}, format="json")
        _assert_success(self, response, 201)

    def test_create_missing_name_returns_400(self):
        response = self.client.post("/api/admin/colours/", {}, format="json")
        _assert_error(self, response, 400)

    def test_retrieve_returns_200(self):
        with patch(_COLOUR_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_colour.return_value = _make_colour()
            response = self.client.get("/api/admin/colours/1/")
        _assert_success(self, response, 200)

    def test_update_returns_200(self):
        with patch(_COLOUR_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.update_colour.return_value = _make_colour(name="Navy Blue")
            response = self.client.patch("/api/admin/colours/1/", {"name": "Navy Blue"}, format="json")
        _assert_success(self, response, 200)

    def test_delete_returns_200(self):
        with patch(_COLOUR_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.delete_colour.return_value = None
            response = self.client.delete("/api/admin/colours/1/")
        _assert_success(self, response, 200)


# ---------------------------------------------------------------------------
# Size tests
# ---------------------------------------------------------------------------

class AdminSizeViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        admin = MagicMock()
        admin.is_authenticated = True
        admin.account_type = "admin"
        self.client.force_authenticate(user=admin)

    def test_list_returns_200(self):
        with patch(_SIZE_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_all_sizes.return_value = [_make_size()]
            response = self.client.get("/api/admin/sizes/")
        _assert_success(self, response, 200)

    def test_create_returns_201(self):
        with patch(_SIZE_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.create_size.return_value = _make_size()
            response = self.client.post("/api/admin/sizes/", {"name": "42"}, format="json")
        _assert_success(self, response, 201)

    def test_create_missing_name_returns_400(self):
        response = self.client.post("/api/admin/sizes/", {}, format="json")
        _assert_error(self, response, 400)

    def test_retrieve_returns_200(self):
        with patch(_SIZE_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_size.return_value = _make_size()
            response = self.client.get("/api/admin/sizes/1/")
        _assert_success(self, response, 200)

    def test_retrieve_not_found(self):
        with patch(_SIZE_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.get_size.side_effect = NotFoundError(message="Size not found")
            response = self.client.get("/api/admin/sizes/99/")
        self.assertFalse(response.data["status"])

    def test_update_returns_200(self):
        with patch(_SIZE_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.update_size.return_value = _make_size(name="43")
            response = self.client.patch("/api/admin/sizes/1/", {"name": "43"}, format="json")
        _assert_success(self, response, 200)

    def test_delete_returns_200(self):
        with patch(_SIZE_SERVICE_PATCH) as mock_factory:
            mock_factory.return_value.delete_size.return_value = None
            response = self.client.delete("/api/admin/sizes/1/")
        _assert_success(self, response, 200)

    def test_list_requires_admin(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/admin/sizes/")
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
