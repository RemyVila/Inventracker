import json
from pathlib import Path

from django.core.management.base import BaseCommand
from core.models import (
    Ingredient,
    Recipe,
    RecipeItem,
    Vendor,
    VendorProduct,
)


class Command(BaseCommand):
    help = "Loads dummy seed data from core/fixtures/seed_data.json"

    def handle(self, *args, **options):
        # Resolve JSON path relative to project root
        json_path = Path("core") / "fixtures" / "seed_data.json"
        if not json_path.exists():
            self.stderr.write(self.style.ERROR(f"Seed file not found: {json_path}"))
            return

        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        recipes_data = data.get("recipes", [])
        vendors_data = data.get("vendors", [])
        vendor_products_data = data.get("vendor_products", [])

        # ------------------------------------------------------------------
        # 1) Build Ingredient objects inferred from recipes
        # ------------------------------------------------------------------
        ingredient_units = {}  # name -> default_unit (from first occurrence)

        for recipe in recipes_data:
            for item in recipe.get("items", []):
                name = item["ingredient"]
                unit = item["unit"]
                # Only set the default unit the first time we see it
                ingredient_units.setdefault(name, unit)

        ingredients_by_name = {}
        for name, unit in ingredient_units.items():
            obj, created = Ingredient.objects.get_or_create(
                name=name,
                defaults={"default_unit": unit},
            )
            ingredients_by_name[name] = obj
            if created:
                self.stdout.write(f"Created Ingredient: {name} ({unit})")

        # ------------------------------------------------------------------
        # 2) Load Vendors
        # ------------------------------------------------------------------
        vendors_by_name = {}
        for v in vendors_data:
            name = v["name"]
            contact_email = v.get("contact_email", "")
            vendor_obj, created = Vendor.objects.get_or_create(
                name=name,
                defaults={
                    "contact_email": contact_email or None,
                },
            )
            vendors_by_name[name] = vendor_obj
            if created:
                self.stdout.write(f"Created Vendor: {name}")

        # ------------------------------------------------------------------
        # 3) Load VendorProducts
        # ------------------------------------------------------------------
        for vp in vendor_products_data:
            vendor_name = vp["vendor"]
            ingredient_name = vp["ingredient"]

            vendor = vendors_by_name.get(vendor_name)
            if not vendor:
                self.stderr.write(
                    self.style.WARNING(
                        f"Vendor '{vendor_name}' referenced in vendor_products "
                        f"but not found; skipping."
                    )
                )
                continue

            ingredient = ingredients_by_name.get(ingredient_name)
            if not ingredient:
                # If an ingredient is referenced here but not in recipes,
                # create it on the fly with the unit from vendor product.
                ingredient_unit = vp["unit"]
                ingredient, _ = Ingredient.objects.get_or_create(
                    name=ingredient_name,
                    defaults={"default_unit": ingredient_unit},
                )
                ingredients_by_name[ingredient_name] = ingredient
                self.stdout.write(
                    f"Created Ingredient (from vendor_products): "
                    f"{ingredient_name} ({ingredient_unit})"
                )

            quantity = vp["quantity"]
            unit = vp["unit"]
            price = vp["price"]
            product_name = vp.get("product_name", "") or ""
            sku = vp.get("sku", "") or ""

            vp_obj, created = VendorProduct.objects.get_or_create(
                vendor=vendor,
                ingredient=ingredient,
                quantity=quantity,
                unit=unit,
                defaults={
                    "product_name": product_name,
                    "price": price,
                    "sku": sku,
                    "active": True,
                },
            )

            if created:
                self.stdout.write(
                    f"Created VendorProduct: {vendor.name} - {ingredient.name} "
                    f"({quantity} {unit}) @ {price}"
                )

        # ------------------------------------------------------------------
        # 4) Load Recipes and RecipeItems
        # ------------------------------------------------------------------
        # Optional: clear existing recipes if you want a clean slate
        # Recipe.objects.all().delete()
        # RecipeItem.objects.all().delete()

        for recipe_data in recipes_data:
            recipe_name = recipe_data["name"]
            recipe_obj, created = Recipe.objects.get_or_create(name=recipe_name)
            if created:
                self.stdout.write(f"Created Recipe: {recipe_name}")
            else:
                # If it already exists, clear its items so we can re-seed
                recipe_obj.recipeitem_set.all().delete()
                self.stdout.write(f"Reset Recipe items for: {recipe_name}")

            for item in recipe_data.get("items", []):
                ingredient_name = item["ingredient"]
                ingredient = ingredients_by_name[ingredient_name]
                quantity = item["quantity"]
                unit = item["unit"]

                RecipeItem.objects.create(
                    recipe=recipe_obj,
                    ingredient=ingredient,
                    quantity=quantity,
                    unit=unit,
                )

        self.stdout.write(self.style.SUCCESS("Seed data loaded successfully!"))
