import unittest
import logging
from app.services.recipe_mapper import map_spoonacular_data_to_dict
from app.models.recipe_schemas import InstructionStepCreate # For validating instruction structure

# Configure logger for capturing logs during tests if needed for specific assertions
# For unittest, self.assertLogs can be used. For pytest, caplog fixture.
# Here, we'll primarily check for behavior like skipping items,
# but direct log assertion can be added if critical.

class TestRecipeMapper(unittest.TestCase):

    def test_map_full_recipe_data_successfully(self):
        spoonacular_data = {
            "id": 123,
            "title": "Test Recipe Deluxe",
            "image": "http://example.com/image.jpg",
            "sourceUrl": "http://example.com/source_recipe",
            "preparationMinutes": 15,
            "cookingMinutes": 25,
            "servings": 4,
            "difficulty": "medium", # This is not directly mapped, default used if not spoonacular_data.get("difficulty")
            "cuisines": ["Italian", "Fusion"],
            "diets": ["vegetarian", "low-fodmap"],
            "summary": "<p>This is a <b>fantastic</b> recipe with <a href='#'>links</a> and <html>markup</html>.</p>",
            "extendedIngredients": [
                {
                    "nameClean": "Tomato",
                    "name": "tomatoes", # nameClean should be preferred
                    "amount": 2.0,
                    "unit": "pieces",
                    "original": "2 large tomatoes, diced",
                    "aisle": "Produce;Vegetables",
                    "nutrition": {
                        "nutrients": [{"name": "Calories", "amount": 60.0, "unit": "kcal"}] # For 2 pieces
                    }
                },
                {
                    "nameClean": "Pasta",
                    "amount": 1.0, # Calories per unit test (amount is 1)
                    "unit": "serving (100g)", # Test complex unit
                    "aisle": "Pasta and Rice",
                    "meta": ["organic"], # Should be part of preparation_note if original is missing
                    "nutrition": {
                        "nutrients": [{"name": "Calories", "amount": 350.0, "unit": "kcal"}] # For 1 serving
                    }
                },
                {
                    "nameClean": "Olive Oil",
                    "amount": 2.0,
                    "unit": "tbsp",
                    "aisle": "Oil, Vinegar, Salad Dressing",
                    # Missing nutrition for this ingredient
                },
                { # Ingredient to be skipped (missing quantity)
                    "nameClean": "Salt",
                    "unit": "pinch"
                },
                { # Ingredient to be skipped (missing name)
                    "amount": 1.0,
                    "unit": "clove"
                },
                 { # Ingredient with no aisle
                    "nameClean": "Secret Spice",
                    "amount": 1.0,
                    "unit": "tsp",
                    "original": "1 tsp secret spice"
                    # No aisle, no nutrition
                }
            ],
            "analyzedInstructions": [
                {
                    "name": "Main Steps",
                    "steps": [
                        {"number": 1, "step": "Boil water for pasta."},
                        {"number": 2, "step": "Dice tomatoes."},
                        {"number": 3, "step": "Cook everything."}
                    ]
                },
                { # Invalid step in this section
                    "name": "Invalid Section",
                    "steps": [
                        {"number": 1, "instruction": "This is not a 'step' field"} # Invalid
                    ]
                }
            ],
            "nutrition": {
                "nutrients": [
                    {"name": "Calories", "amount": 800.0, "unit": "kcal"},
                    {"name": "Protein", "amount": 30.0, "unit": "g"},
                    {"name": "Fat", "amount": 25.0, "unit": "g"},
                    {"name": "Net Carbohydrates", "amount": 100.0, "unit": "g"} # Test "Net Carbohydrates"
                ]
            }
        }
        spoonacular_id_val = 123

        with self.assertLogs(logger='app.services.recipe_mapper', level='INFO') as cm:
            mapped_data = map_spoonacular_data_to_dict(spoonacular_data, spoonacular_id_val)

        # Basic assertions
        self.assertEqual(mapped_data["title"], "Test Recipe Deluxe")
        self.assertEqual(mapped_data["image_url"], "http://example.com/image.jpg")
        self.assertEqual(mapped_data["source_url"], "http://example.com/source_recipe")
        self.assertEqual(mapped_data["prep_time_minutes"], 15)
        self.assertEqual(mapped_data["cook_time_minutes"], 25)
        self.assertEqual(mapped_data["servings"], 4)
        self.assertEqual(mapped_data["difficulty_level"], "medium") # Default or from data
        self.assertEqual(mapped_data["cuisine_type"], "Italian")
        self.assertListEqual(mapped_data["dietary_tags"], ["vegetarian", "low-fodmap"])
        self.assertEqual(mapped_data["spoonacular_id"], spoonacular_id_val)

        # Description HTML Stripping
        self.assertEqual(mapped_data["description"], "This is a fantastic recipe with links and markup.")

        # Ingredients Mapping
        self.assertEqual(len(mapped_data["ingredients_data_temp"]), 4) # tomato, pasta, olive oil, secret spice (salt/no-name skipped)

        ing1_tomato = mapped_data["ingredients_data_temp"][0]
        self.assertEqual(ing1_tomato["name"], "tomato")
        self.assertEqual(ing1_tomato["quantity"], 2.0)
        self.assertEqual(ing1_tomato["unit"], "pieces")
        self.assertEqual(ing1_tomato["preparation_note"], "2 large tomatoes, diced")
        self.assertEqual(ing1_tomato["category"], "Produce")
        self.assertIsNone(ing1_tomato["calories_per_unit"]) # Amount was 2.0

        ing2_pasta = mapped_data["ingredients_data_temp"][1]
        self.assertEqual(ing2_pasta["name"], "pasta")
        self.assertEqual(ing2_pasta["quantity"], 1.0)
        self.assertEqual(ing2_pasta["unit"], "serving (100g)")
        self.assertEqual(ing2_pasta["preparation_note"], "organic") # from meta
        self.assertEqual(ing2_pasta["category"], "Pasta and Rice")
        self.assertEqual(ing2_pasta["calories_per_unit"], 350.0) # Amount was 1.0

        ing3_olive_oil = mapped_data["ingredients_data_temp"][2]
        self.assertEqual(ing3_olive_oil["name"], "olive oil")
        self.assertEqual(ing3_olive_oil["category"], "Oil, Vinegar, Salad Dressing")
        self.assertIsNone(ing3_olive_oil["calories_per_unit"]) # Missing nutrition data

        ing4_secret_spice = mapped_data["ingredients_data_temp"][3]
        self.assertEqual(ing4_secret_spice["name"], "secret spice")
        self.assertIsNone(ing4_secret_spice["category"]) # Missing aisle
        self.assertIsNone(ing4_secret_spice["calories_per_unit"])


        # Check logs for skipped ingredients and calorie calculation notes
        # Example: self.assertIn("Skipping ingredient 'Salt' due to missing quantity", cm.output[0])
        self.assertTrue(any("Skipping ingredient 'Salt' due to missing quantity" in log_msg for log_msg in cm.output))
        self.assertTrue(any("Skipping ingredient with no name" in log_msg for log_msg in cm.output))
        self.assertTrue(any("Ingredient 'tomato': Calorie data present for quantity 2.0 pieces but not directly per single unit." in log_msg for log_msg in cm.output))


        # Instructions Mapping
        self.assertEqual(len(mapped_data["instructions_data"]), 3)
        self.assertIsInstance(mapped_data["instructions_data"][0], dict) # Was InstructionStepCreate.model_dump()
        self.assertEqual(mapped_data["instructions_data"][0]["step_number"], 1)
        self.assertEqual(mapped_data["instructions_data"][0]["instruction"], "Boil water for pasta.")
        self.assertEqual(mapped_data["instructions_data"][2]["instruction"], "Cook everything.")
        # Check log for skipped invalid instruction
        self.assertTrue(any("Skipping invalid instruction step" in log_msg for log_msg in cm.output))


        # Nutritional Information Mapping
        self.assertEqual(mapped_data["calories"], 800.0)
        self.assertEqual(mapped_data["protein"], 30.0)
        self.assertEqual(mapped_data["fat"], 25.0)
        self.assertEqual(mapped_data["carbohydrates"], 100.0)


    def test_map_recipe_with_missing_prep_cook_uses_readyinminutes(self):
        spoonacular_data = {
            "title": "Quick Dish",
            "readyInMinutes": 20, # Only this time is provided
            "summary": "A very quick dish."
        }
        mapped_data = map_spoonacular_data_to_dict(spoonacular_data, 234)
        self.assertIsNone(mapped_data["prep_time_minutes"])
        self.assertEqual(mapped_data["cook_time_minutes"], 20) # readyInMinutes should go to cook_time_minutes

    def test_map_instructions_from_plain_text(self):
        spoonacular_data = {
            "title": "Simple Instructions",
            "instructions": "1. Do this. 2. Do that.",
            "summary": "Easy."
        }
        mapped_data = map_spoonacular_data_to_dict(spoonacular_data, 345)
        self.assertEqual(len(mapped_data["instructions_data"]), 1)
        self.assertEqual(mapped_data["instructions_data"][0]["step_number"], 1)
        self.assertEqual(mapped_data["instructions_data"][0]["instruction"], "1. Do this. 2. Do that.")

    def test_map_no_instructions_provided(self):
        spoonacular_data = {
            "title": "No Instructions Recipe",
            "summary": "Figure it out."
            # No analyzedInstructions, no instructions field
        }
        with self.assertLogs(logger='app.services.recipe_mapper', level='WARNING') as cm:
            mapped_data = map_spoonacular_data_to_dict(spoonacular_data, 456)

        self.assertEqual(len(mapped_data["instructions_data"]), 0)
        self.assertTrue(any("No instructions mapped" in log_msg for log_msg in cm.output))

    def test_map_ingredient_name_fallback(self):
        spoonacular_data = {
            "title": "Ingredient Name Fallback",
            "summary": "Test.",
            "extendedIngredients": [{
                "name": "Regular Name Only", # No nameClean
                "amount": 1.0,
                "unit": "item"
            }]
        }
        mapped_data = map_spoonacular_data_to_dict(spoonacular_data, 567)
        self.assertEqual(len(mapped_data["ingredients_data_temp"]), 1)
        self.assertEqual(mapped_data["ingredients_data_temp"][0]["name"], "regular name only")

    def test_map_ingredient_preparation_note_fallback(self):
        spoonacular_data = {
            "title": "Prep Note Fallback",
            "summary": "Test.",
            "extendedIngredients": [{
                "nameClean": "Test Ing",
                "amount": 1.0,
                "unit": "item",
                # No "original" or "originalString"
                "meta": ["finely chopped", "rinsed"]
            }]
        }
        mapped_data = map_spoonacular_data_to_dict(spoonacular_data, 678)
        self.assertEqual(mapped_data["ingredients_data_temp"][0]["preparation_note"], "finely chopped; rinsed")

    def test_missing_title_raises_value_error(self):
        spoonacular_data = {
            "id": 789,
            "summary": "A recipe with no name."
            # Missing "title"
        }
        with self.assertRaisesRegex(ValueError, "Spoonacular data missing 'title'."):
            map_spoonacular_data_to_dict(spoonacular_data, 789)

    def test_empty_spoonacular_data(self):
        # Technically, missing title would be caught first.
        # This tests general resilience, though specific checks for other fields
        # are implicitly covered by their absence in a minimal valid payload.
        spoonacular_data = {}
        with self.assertRaisesRegex(ValueError, "Spoonacular data missing 'title'."):
            map_spoonacular_data_to_dict(spoonacular_data, 901)

    def test_map_nutrition_various_names(self):
        spoonacular_data = {
            "title": "Nutrition Test",
            "summary": "Nutrition.",
            "nutrition": {
                "nutrients": [
                    {"name": "Calories", "amount": 100.0},
                    {"name": "Protein", "amount": 10.0},
                    {"name": "Fat", "amount": 5.0},
                    # No "Carbohydrates", should be None
                ]
            }
        }
        mapped_data = map_spoonacular_data_to_dict(spoonacular_data, 1001)
        self.assertEqual(mapped_data["calories"], 100.0)
        self.assertEqual(mapped_data["protein"], 10.0)
        self.assertEqual(mapped_data["fat"], 5.0)
        self.assertIsNone(mapped_data["carbohydrates"])

        spoonacular_data_net_carbs = {
            "title": "Nutrition Test Net Carbs",
            "summary": "Nutrition.",
            "nutrition": {
                "nutrients": [
                    {"name": "Net Carbohydrates", "amount": 50.0}, # Only net carbs
                ]
            }
        }
        mapped_data_net = map_spoonacular_data_to_dict(spoonacular_data_net_carbs, 1002)
        self.assertEqual(mapped_data_net["carbohydrates"], 50.0)

        spoonacular_data_both_carbs = {
            "title": "Nutrition Test Both Carbs",
            "summary": "Nutrition.",
            "nutrition": {
                "nutrients": [
                    {"name": "Carbohydrates", "amount": 60.0}, # Regular carbs
                    {"name": "Net Carbohydrates", "amount": 55.0}, # Net carbs also present
                ]
            }
        }
        # "Carbohydrates" should be prioritized over "Net Carbohydrates" if both exist
        mapped_data_both = map_spoonacular_data_to_dict(spoonacular_data_both_carbs, 1003)
        self.assertEqual(mapped_data_both["carbohydrates"], 60.0)


    def test_no_ingredients_mapped_warning(self):
        spoonacular_data = {
            "title": "No Ingredients Recipe",
            "summary": "A recipe with no ingredients listed.",
            "extendedIngredients": [] # Empty list
        }
        with self.assertLogs(logger='app.services.recipe_mapper', level='WARNING') as cm:
            mapped_data = map_spoonacular_data_to_dict(spoonacular_data, 1101)

        self.assertEqual(len(mapped_data["ingredients_data_temp"]), 0)
        self.assertTrue(any("No ingredients mapped" in log_msg for log_msg in cm.output))

if __name__ == "__main__":
    # This allows running the tests directly via `python test_recipe_mapper.py`
    # For more complex setups or CI, a test runner like pytest or `python -m unittest discover` is common.
    unittest.main()
