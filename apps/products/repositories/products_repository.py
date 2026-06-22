from __future__ import annotations

from typing import List, Optional

from apps.core.exceptions import NotFoundError
from apps.products.interfaces.products_repository_interface import IProductRepository
from apps.products.models import (
    Category,
    CategoryTranslation,
    Colour,
    ColourTranslation,
    Product,
    ProductTranslation,
    Size,
    Tag,
    TagTranslation,
)


class CategoryRepository:

    def get_all(self) -> List[Category]:
        return Category.objects.prefetch_related("translations").order_by("-created_at")

    def get_all_active(self) -> List[Category]:
        return Category.objects.filter(is_active=True).prefetch_related("translations").order_by("-created_at")

    def get_by_id(self, id: int) -> Category:
        try:
            return Category.objects.prefetch_related("translations").get(pk=id)
        except Category.DoesNotExist:
            raise NotFoundError(message="Category not found")

    def create(self, data: dict) -> Category:
        return Category.objects.create(
            name=data["name"],
            is_active=data.get("is_active", True),
        )

    def update(self, id: int, data: dict) -> Category:
        instance = self.get_by_id(id)
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, id: int) -> None:
        self.get_by_id(id).delete()

    def toggle_active(self, id: int) -> bool:
        instance = self.get_by_id(id)
        instance.is_active = not instance.is_active
        instance.save()
        return instance.is_active

    def get_translation(self, instance: Category, language: str) -> Optional[CategoryTranslation]:
        try:
            return instance.translations.get(language=language)
        except CategoryTranslation.DoesNotExist:
            return None

    def upsert_translation(self, instance: Category, language: str, name: str) -> CategoryTranslation:
        obj, _ = CategoryTranslation.objects.update_or_create(
            category=instance,
            language=language,
            defaults={"name": name},
        )
        return obj


class TagRepository:

    def get_all(self) -> List[Tag]:
        return Tag.objects.prefetch_related("translations").order_by("-created_at")

    def get_all_active(self) -> List[Tag]:
        return Tag.objects.filter(is_active=True).prefetch_related("translations").order_by("-created_at")

    def get_by_id(self, id: int) -> Tag:
        try:
            return Tag.objects.prefetch_related("translations").get(pk=id)
        except Tag.DoesNotExist:
            raise NotFoundError(message="Tag not found")

    def get_by_ids(self, ids: list) -> List[Tag]:
        return list(Tag.objects.filter(pk__in=ids))

    def create(self, data: dict) -> Tag:
        return Tag.objects.create(
            name=data["name"],
            is_active=data.get("is_active", True),
        )

    def update(self, id: int, data: dict) -> Tag:
        instance = self.get_by_id(id)
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, id: int) -> None:
        self.get_by_id(id).delete()

    def toggle_active(self, id: int) -> bool:
        instance = self.get_by_id(id)
        instance.is_active = not instance.is_active
        instance.save()
        return instance.is_active

    def get_translation(self, instance: Tag, language: str) -> Optional[TagTranslation]:
        try:
            return instance.translations.get(language=language)
        except TagTranslation.DoesNotExist:
            return None

    def upsert_translation(self, instance: Tag, language: str, name: str) -> TagTranslation:
        obj, _ = TagTranslation.objects.update_or_create(
            tag=instance,
            language=language,
            defaults={"name": name},
        )
        return obj


class ColourRepository:

    def get_all(self) -> List[Colour]:
        return Colour.objects.prefetch_related("translations").order_by("name")

    def get_by_id(self, id: int) -> Colour:
        try:
            return Colour.objects.prefetch_related("translations").get(pk=id)
        except Colour.DoesNotExist:
            raise NotFoundError(message="Colour not found")

    def get_by_ids(self, ids: list) -> List[Colour]:
        return list(Colour.objects.filter(pk__in=ids))

    def create(self, data: dict) -> Colour:
        return Colour.objects.create(name=data["name"])

    def update(self, id: int, data: dict) -> Colour:
        instance = self.get_by_id(id)
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, id: int) -> None:
        self.get_by_id(id).delete()

    def get_translation(self, instance: Colour, language: str) -> Optional[ColourTranslation]:
        try:
            return instance.translations.get(language=language)
        except ColourTranslation.DoesNotExist:
            return None

    def upsert_translation(self, instance: Colour, language: str, name: str) -> ColourTranslation:
        obj, _ = ColourTranslation.objects.update_or_create(
            colour=instance,
            language=language,
            defaults={"name": name},
        )
        return obj


class SizeRepository:

    def get_all(self) -> List[Size]:
        return Size.objects.order_by("name")

    def get_by_id(self, id: int) -> Size:
        try:
            return Size.objects.get(pk=id)
        except Size.DoesNotExist:
            raise NotFoundError(message="Size not found")

    def get_by_ids(self, ids: list) -> List[Size]:
        return list(Size.objects.filter(pk__in=ids))

    def create(self, data: dict) -> Size:
        return Size.objects.create(name=data["name"])

    def update(self, id: int, data: dict) -> Size:
        instance = self.get_by_id(id)
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, id: int) -> None:
        self.get_by_id(id).delete()


class ProductRepository(IProductRepository):

    def __init__(
        self,
        category: CategoryRepository,
        tag: TagRepository,
        colour: ColourRepository,
        size: SizeRepository,
    ) -> None:
        self._category_repo = category
        self._tag_repo = tag
        self._colour_repo = colour
        self._size_repo = size

    def _base_qs(self):
        return (
            Product.objects.select_related("category")
            .prefetch_related(
                "tags", "tags__translations",
                "sizes",
                "colors",
                "images",
                "translations",
            )
        )

    def get_all(self) -> List[Product]:
        return self._base_qs().order_by("-created_at")

    def get_all_active(self) -> List[Product]:
        return self._base_qs().filter(is_active=True).order_by("-created_at")

    def get_by_id(self, id: int) -> Product:
        try:
            return self._base_qs().get(pk=id)
        except Product.DoesNotExist:
            raise NotFoundError(message="Product not found")

    def get_by_category(self, category_id: int) -> List[Product]:
        self._category_repo.get_by_id(category_id)
        return self._base_qs().filter(category_id=category_id, is_active=True).order_by("-created_at")

    def get_by_tag(self, tag_id: int) -> List[Product]:
        self._tag_repo.get_by_id(tag_id)
        return self._base_qs().filter(tags__id=tag_id, is_active=True).order_by("-created_at")

    def create(self, data: dict) -> Product:
        category = self._category_repo.get_by_id(data["category"])
        tag_ids = data.get("tags", [])
        size_ids = data.get("sizes", [])
        colour_ids = data.get("colors", [])

        instance = Product.objects.create(
            name=data["name"],
            brand=data.get("brand", ""),
            description=data.get("description", ""),
            price=data["price"],
            discount_percentage=data.get("discount_percentage", 0),
            category=category,
            is_active=data.get("is_active", True),
        )
        if tag_ids:
            instance.tags.set(self._tag_repo.get_by_ids(tag_ids))
        if size_ids:
            instance.sizes.set(self._size_repo.get_by_ids(size_ids))
        if colour_ids:
            instance.colors.set(self._colour_repo.get_by_ids(colour_ids))
        return instance

    def update(self, id: int, data: dict) -> Product:
        instance = self.get_by_id(id)
        m2m_fields = {"tags", "sizes", "colors"}
        scalar_data = {k: v for k, v in data.items() if k not in m2m_fields}

        if "category" in scalar_data:
            scalar_data["category"] = self._category_repo.get_by_id(scalar_data["category"])

        for key, value in scalar_data.items():
            setattr(instance, key, value)
        instance.save()

        if "tags" in data:
            instance.tags.set(self._tag_repo.get_by_ids(data["tags"]))
        if "sizes" in data:
            instance.sizes.set(self._size_repo.get_by_ids(data["sizes"]))
        if "colors" in data:
            instance.colors.set(self._colour_repo.get_by_ids(data["colors"]))
        return instance

    def delete(self, id: int) -> None:
        self.get_by_id(id).delete()

    def filter(self, **kwargs) -> List[Product]:
        return self._base_qs().filter(**kwargs)

    def toggle_active(self, id: int) -> bool:
        instance = self.get_by_id(id)
        instance.is_active = not instance.is_active
        instance.save()
        return instance.is_active

    def get_translation(self, instance: Product, language: str) -> Optional[ProductTranslation]:
        try:
            return instance.translations.get(language=language)
        except ProductTranslation.DoesNotExist:
            return None

    def upsert_translation(self, instance: Product, language: str, name: str, description: str) -> ProductTranslation:
        obj, _ = ProductTranslation.objects.update_or_create(
            product=instance,
            language=language,
            defaults={"name": name, "description": description},
        )
        return obj
