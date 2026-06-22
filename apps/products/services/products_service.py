from __future__ import annotations

import logging
import  asyncio 
from asgiref.sync import sync_to_async
from apps.core.utils.translation_utils import TRANSLATION_LANGUAGES, TranslationService
from apps.products.interfaces.products_repository_interface import IProductRepository
from apps.products.models import Category, Colour, Product, Size, Tag
from apps.products.repositories.products_repository import (
    CategoryRepository,
    ColourRepository,
    SizeRepository,
    TagRepository,
)

logger = logging.getLogger(__name__)


class CategoryService:

    def __init__(self, repository: CategoryRepository, translation_service: TranslationService) -> None:
        self._repo = repository
        self._translation = translation_service

    def get_all_categories(self):
        return self._repo.get_all()

    def get_active_categories(self):
        return self._repo.get_all_active()

    def get_category(self, id: int):
        return self._repo.get_by_id(id)

    def create_category(self, data: dict):
        instance = self._repo.create(data)
        self._auto_translate_all(instance)
        return instance

    def update_category(self, id: int, data: dict):
        instance = self._repo.update(id, data)
        self._auto_translate_all(instance)
        return instance

    def delete_category(self, id: int):
        return self._repo.delete(id)

    def toggle_active_category(self, id: int):
        return self._repo.toggle_active(id)

    def _auto_translate_all(self, instance: Category) -> None:
        source = {"name": instance.name}
        for lang_code, lang_name in TRANSLATION_LANGUAGES.items():
            try:
                translated = self._translation.translate_batch(source, lang_name)
                self._repo.upsert_translation(
                    instance, lang_code,
                    translated.get("name", instance.name),
                )
            except Exception:
                logger.exception("Failed to translate Category %s to %s", instance.pk, lang_code)


class TagService:

    def __init__(self, repository: TagRepository, translation_service: TranslationService) -> None:
        self._repo = repository
        self._translation = translation_service

    def get_all_tags(self):
        return self._repo.get_all()

    def get_active_tags(self):
        return self._repo.get_all_active()

    def get_tag(self, id: int):
        return self._repo.get_by_id(id)

    def create_tag(self, data: dict):
        instance = self._repo.create(data)
        self._auto_translate_all(instance)
        return instance

    def update_tag(self, id: int, data: dict):
        instance = self._repo.update(id, data)
        self._auto_translate_all(instance)
        return instance

    def delete_tag(self, id: int):
        return self._repo.delete(id)

    def toggle_active_tag(self, id: int):
        return self._repo.toggle_active(id)

    def _auto_translate_all(self, instance: Tag) -> None:
        source = {"name": instance.name}
        for lang_code, lang_name in TRANSLATION_LANGUAGES.items():
            try:
                translated = self._translation.translate_batch(source, lang_name)
                self._repo.upsert_translation(
                    instance, lang_code,
                    translated.get("name", instance.name),
                )
            except Exception:
                logger.exception("Failed to translate Tag %s to %s", instance.pk, lang_code)


class ColourService:

    def __init__(self, repository: ColourRepository, translation_service: TranslationService) -> None:
        self._repo = repository
        self._translation = translation_service

    def get_all_colours(self):
        return self._repo.get_all()

    def get_colour(self, id: int):
        return self._repo.get_by_id(id)

    def create_colour(self, data: dict):
        instance = self._repo.create(data)
        self._auto_translate_all(instance)
        return instance

    def update_colour(self, id: int, data: dict):
        instance = self._repo.update(id, data)
        self._auto_translate_all(instance)
        return instance

    def delete_colour(self, id: int):
        return self._repo.delete(id)

    def _auto_translate_all(self, instance: Colour) -> None:
        source = {"name": instance.name}
        for lang_code, lang_name in TRANSLATION_LANGUAGES.items():
            try:
                translated = self._translation.translate_batch(source, lang_name)
                self._repo.upsert_translation(
                    instance, lang_code,
                    translated.get("name", instance.name),
                )
            except Exception:
                logger.exception("Failed to translate Colour %s to %s", instance.pk, lang_code)


class SizeService:

    def __init__(self, repository: SizeRepository) -> None:
        self._repo = repository

    def get_all_sizes(self):
        return self._repo.get_all()

    def get_size(self, id: int):
        return self._repo.get_by_id(id)

    def create_size(self, data: dict):
        return self._repo.create(data)

    def update_size(self, id: int, data: dict):
        return self._repo.update(id, data)

    def delete_size(self, id: int):
        return self._repo.delete(id)


class ProductService:

    def __init__(self, repository: IProductRepository, translation_service: TranslationService) -> None:
        self._repo = repository
        self._translation = translation_service

    def get_all_products(self):
        return self._repo.get_all()

    def get_product(self, id: int):
        return self._repo.get_by_id(id)

    def list_available_products(self):
        return self._repo.get_all_active()

    def get_products_by_category(self, category_id: int):
        return self._repo.get_by_category(category_id)

    def get_products_by_tag(self, tag_id: int):
        return self._repo.get_by_tag(tag_id)

    def create_product(self, data: dict):
        instance = self._repo.create(data)
        asyncio.run(self._auto_translate_all(instance))
        return instance

    def update_product(self, id: int, data: dict):
        instance = self._repo.update(id, data)
        asyncio.run(self._auto_translate_all(instance))
        return instance

    def delete_product(self, id: int):
        return self._repo.delete(id)

    def toggle_active_product(self, id: int):
        return self._repo.toggle_active(id)

    def filter_products(self, **kwargs):
        return self._repo.filter(**kwargs)
    async def _translate_language(self, instance: Product, source: dict, lang_name: str,lang_code: str) -> dict:
        try: 
            translated = await asyncio.to_thread(self._translation.translate_batch, source, lang_name)
            await sync_to_async(self._repo.upsert_translation)(
                instance, lang_code,
                translated.get("name", instance.name),
                translated.get("description", instance.description),
            )
            return translated
        except Exception:
            logger.exception("Failed to translate Product %s to %s", instance.pk, lang_code)
            translated = {}
        return translated

    async def _auto_translate_all(self, instance: Product) -> None:
        source = {"name": instance.name, "description": instance.description}
        await asyncio.gather(*[
            self._translate_language(instance, source, lang_name, lang_code)
            for lang_code, lang_name in TRANSLATION_LANGUAGES.items()
        ])