from typing import List, Dict, Any, Optional
from app.models.recipe_schemas import InstructionStepCreate
from pydantic import HttpUrl
import logging

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
    # Future: consider stripping HTML from description if present.
    # from bs4 import BeautifulSoup
    # if description:
    #     soup = BeautifulSoup(description, "html.parser")
    #     description = soup.get_text()

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

        mapped_ingredients_temp.append({
            "name": name.lower(),
            "quantity": float(quantity),
            "unit": unit,
            "preparation_note": preparation_note
        })

    mapped_recipe_data["ingredients_data_temp"] = mapped_ingredients_temp

    if not instructions_dict_list:
        logger.warning(f"No instructions mapped for Spoonacular recipe {spoonacular_id_val} ('{title}').")

    if not mapped_ingredients_temp:
        logger.warning(f"No ingredients mapped for Spoonacular recipe {spoonacular_id_val} ('{title}').")

    return mapped_recipe_data
