from typing import List, Dict, Any, Optional
from app.models.recipe_schemas import InstructionStepCreate
from pydantic import HttpUrl
import logging
from bs4 import BeautifulSoup # Add this import

logger = logging.getLogger(__name__)

def map_spoonacular_data_to_dict(
    spoonacular_data: Dict[str, Any],
    spoonacular_id_val: int
) -> Dict[str, Any]:
    """
    Maps recipe data from Spoonacular API (get_recipe_details response) to
    a dictionary structured for creating a local recipe.
    """

    title = spoonacular_data.get("title")
    if not title:
        raise ValueError("Spoonacular data missing 'title'.")

    description = spoonacular_data.get("summary")
    if description:
        soup = BeautifulSoup(description, "html.parser")
        description = soup.get_text()

    image_url_str = spoonacular_data.get("image")
    image_url = str(HttpUrl(image_url_str)) if image_url_str else None

    source_url_str = spoonacular_data.get("sourceUrl")
    source_url = str(HttpUrl(source_url_str)) if source_url_str else None

    prep_time_minutes = spoonacular_data.get("preparationMinutes")
    cook_time_minutes = spoonacular_data.get("cookingMinutes")

    if prep_time_minutes is None and cook_time_minutes is None:
        ready_in_minutes = spoonacular_data.get("readyInMinutes")
        if ready_in_minutes is not None:
            cook_time_minutes = ready_in_minutes

    servings = spoonacular_data.get("servings")
    difficulty_level = spoonacular_data.get("difficulty", "medium")

    cuisines_list = spoonacular_data.get("cuisines", [])
    cuisine_type = cuisines_list[0] if cuisines_list else None

    dietary_tags = spoonacular_data.get("diets", [])

    instructions_dict_list: List[Dict[str, Any]] = []
    analyzed_instructions = spoonacular_data.get("analyzedInstructions", [])
    if analyzed_instructions:
        for instruction_set in analyzed_instructions:
            for step_data in instruction_set.get("steps", []):
                if "step" in step_data and "number" in step_data:
                    try:
                        instruction_model = InstructionStepCreate(
                            step_number=step_data["number"],
                            instruction=step_data["step"]
                        )
                        instructions_dict_list.append(instruction_model.model_dump())
                    except Exception as e:
                        logger.warning(f"Skipping invalid instruction step for recipe {spoonacular_id_val}: {step_data}. Error: {e}")
    elif spoonacular_data.get("instructions"):
        plain_instructions_text = spoonacular_data.get("instructions")
        if isinstance(plain_instructions_text, str) and plain_instructions_text.strip():
            logger.info(f"Using plain text instructions for recipe {spoonacular_id_val} ('{title}').")
            try:
                instruction_model = InstructionStepCreate(step_number=1, instruction=plain_instructions_text)
                instructions_dict_list.append(instruction_model.model_dump())
            except Exception as e:
                 logger.warning(f"Could not use plain text instruction for recipe {spoonacular_id_val}. Error: {e}")

    mapped_recipe_data = {
        "title": title,
        "description": description,
        "prep_time_minutes": prep_time_minutes,
        "cook_time_minutes": cook_time_minutes,
        "servings": servings,
        "difficulty_level": difficulty_level,
        "cuisine_type": cuisine_type,
        "dietary_tags": dietary_tags,
        "image_url": image_url,
        "source_url": source_url,
        "spoonacular_id": spoonacular_id_val,
        "instructions_data": instructions_dict_list
    }

    spoonacular_ingredients = spoonacular_data.get("extendedIngredients", [])
    mapped_ingredients_temp: List[Dict[str, Any]] = []
    for sp_ing in spoonacular_ingredients:
        name = sp_ing.get("nameClean") or sp_ing.get("name")
        if not name:
            logger.warning(f"Skipping ingredient with no name for recipe {spoonacular_id_val} ('{title}').")
            continue

        quantity = sp_ing.get("amount")
        unit = sp_ing.get("unit")

        preparation_note = sp_ing.get("original") or sp_ing.get("originalString") or "; ".join(sp_ing.get("meta", []))

        if quantity is None or unit is None:
             logger.warning(f"Skipping ingredient '{name}' due to missing quantity/unit for recipe {spoonacular_id_val} ('{title}').")
             continue

        category = None
        if sp_ing.get("aisle"):
            category = sp_ing.get("aisle").split(";")[0]

        calories_per_unit = None
        # Hypothetical: Spoonacular might provide nutrition per ingredient
        # This part is speculative and needs checking against actual Spoonacular data
        if "nutrition" in sp_ing and "nutrients" in sp_ing["nutrition"]:
            for nutrient in sp_ing["nutrition"]["nutrients"]:
                if nutrient.get("name", "").lower() == "calories" and "amount" in nutrient and "unit" in nutrient:
                    # This is tricky: amount might be for the sp_ing.get("amount")
                    # We need calories PER sp_ing.get("unit")
                    # If sp_ing.get("amount") is 1, then nutrient.get("amount") is calories_per_unit
                    # If sp_ing.get("amount") is > 1, needs division.
                    # This is a simplification; real calculation might be more involved.
                    # For now, let's assume if 'amount' (quantity) is 1.0, it's direct, else log/skip.
                    if float(quantity) == 1.0:
                        calories_per_unit = float(nutrient["amount"])
                    else:
                        # Log that calculation is needed or it's not directly per unit
                        logger.info(f"Ingredient '{name}': Calorie data present for quantity {quantity} {unit} but not directly per single unit. Requires calculation.")
                    break

        mapped_ingredients_temp.append({
            "name": name.lower(),
            "quantity": float(quantity),
            "unit": unit,
            "preparation_note": preparation_note,
            "category": category,
            "calories_per_unit": calories_per_unit
        })

    mapped_recipe_data["ingredients_data_temp"] = mapped_ingredients_temp

    if not instructions_dict_list:
        logger.warning(f"No instructions mapped for Spoonacular recipe {spoonacular_id_val} ('{title}').")

    if not mapped_ingredients_temp:
        logger.warning(f"No ingredients mapped for Spoonacular recipe {spoonacular_id_val} ('{title}').")

    # Extract nutritional information
    nutrition_data = spoonacular_data.get("nutrition", {})
    nutrients = nutrition_data.get("nutrients", [])

    calories = None
    protein = None
    fat = None
    carbohydrates = None

    for nutrient in nutrients:
        name = nutrient.get("name", "").lower()
        amount = nutrient.get("amount")
        # unit = nutrient.get("unit") # Unit might be useful for validation later

        if amount is None:
            continue

        if name == "calories":
            calories = amount
        elif name == "protein":
            protein = amount
        elif name == "fat":
            fat = amount
        elif name == "carbohydrates": # Spoonacular often uses "Net Carbohydrates" or just "Carbohydrates"
            carbohydrates = amount
        elif name == "net carbohydrates" and carbohydrates is None: # Prioritize "Carbohydrates" if available
            carbohydrates = amount

    mapped_recipe_data["calories"] = calories
    mapped_recipe_data["protein"] = protein
    mapped_recipe_data["fat"] = fat
    mapped_recipe_data["carbohydrates"] = carbohydrates

    return mapped_recipe_data
