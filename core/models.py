from django.db import models

# Create your models here.
class Vendor(models.Model):
    name = models.CharField(max_length=255)
    contact_email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name
        
class Ingredient(models.Model):
    name = models.CharField(max_length=255, unique=True)
    default_unit = models.CharField(max_length=50)  # e.g. "grams", "ml", "units"

    def __str__(self):
        return self.name

class Recipe(models.Model):
    name = models.CharField(max_length=255)
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeItem',
        related_name='recipes'
    )

    def __str__(self):
        return self.name

class RecipeItem(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)

    # Amount used in this recipe
    quantity = models.FloatField()
    unit = models.CharField(max_length=50)  # "g", "ml", "cups", etc.

    def __str__(self):
        return f"{self.quantity} {self.unit} {self.ingredient.name} in {self.recipe.name}"

class InventoryItem(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="inventory_items")
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_items")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)  # preferably matches default_unit
    unit_cost = models.DecimalField(max_digits=10, decimal_places=4)  # cost per default_unit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ingredient.name} - {self.quantity} {self.unit}"

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost
    
class VendorProduct(models.Model):
    """
    A *catalog* item: a specific ingredient as sold by a vendor,
    in a particular package size and price.
    Example:
      Vendor: 'Bulk Baking Co'
      Ingredient: 'Flour'
      quantity: 5000
      unit: 'g'
      price: 8.99
    """

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="products"
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="vendor_products"
    )

    # Optional marketing/label name for that product
    product_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional name as listed by the vendor (e.g. 'AP Flour 50lb Bag')"
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Package size (e.g. 5000 for 5kg)"
    )
    unit = models.CharField(
        max_length=50,
        help_text="Unit for the package size, e.g. 'g', 'ml', 'units'"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price for the whole package"
    )

    sku = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional vendor SKU / code"
    )
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # This makes exactly what you noticed true:
        # the combination is what gives uniqueness.
        unique_together = ("vendor", "ingredient", "quantity", "unit")

    def __str__(self):
        label = self.product_name or f"{self.ingredient.name}"
        return f"{self.vendor.name} - {label} ({self.quantity} {self.unit})"

    @property
    def cost_per_unit(self):
        if self.quantity and self.quantity > 0:
            return self.price / self.quantity
        return None