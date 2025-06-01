import httpx
from ..core.config import settings

class SpoonacularException(Exception):
    "Custom exception for Spoonacular API client errors."
    pass

class SpoonacularRateLimitException(SpoonacularException):
    "Custom exception for Spoonacular API rate limit errors (e.g., 402)."
    pass

class SpoonacularClient:
    """
    A client for interacting with the Spoonacular API.
    Documentation: https://spoonacular.com/food-api/docs
    """
    BASE_URL = "https://api.spoonacular.com"

    def __init__(self, api_key: str = None):
        resolved_api_key = api_key if api_key is not None else settings.SPOONACULAR_API_KEY
        if not resolved_api_key or resolved_api_key == "your_spoonacular_api_key" or resolved_api_key == "SPOONACULAR_API_KEY":
            raise ValueError(
                "Spoonacular API key is not configured or is still set to a placeholder. "
                "Please set a valid SPOONACULAR_API_KEY in your environment or .env file."
            )
        self.api_key = resolved_api_key
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=20.0)

    async def _request(self, method: str, endpoint: str, params: dict = None, json_data: dict = None) -> dict:
        current_params = params.copy() if params else {}
        current_params["apiKey"] = self.api_key

        try:
            response = await self._client.request(method, endpoint, params=current_params, json=json_data)

            if response.status_code == 402:
                raise SpoonacularRateLimitException(
                    f"Spoonacular API request failed (Status 402 - Payment Required, "
                    f"often points limit): {response.text} for URL: {response.url}"
                )

            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise SpoonacularException(
                f"API request to {e.request.url} failed with status {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.TimeoutException as e:
            raise SpoonacularException(f"Request to {e.request.url} timed out.") from e
        except httpx.RequestError as e:
            raise SpoonacularException(f"Request error for {e.request.url}: {str(e)}") from e

    async def search_recipes(
        self,
        query: str,
        offset: int = 0,
        number: int = 10,
        add_recipe_information: bool = True,
        fill_ingredients: bool = True,
        **kwargs
    ) -> dict:
        params = {
            "query": query,
            "offset": offset,
            "number": number,
            "addRecipeInformation": add_recipe_information,
            "fillIngredients": fill_ingredients,
            **kwargs
        }
        active_params = {k: v for k, v in params.items() if v is not None}
        return await self._request("GET", "/recipes/complexSearch", params=active_params)

    async def get_recipe_details(self, recipe_id: int, include_nutrition: bool = False) -> dict:
        params = {"includeNutrition": include_nutrition}
        return await self._request("GET", f"/recipes/{recipe_id}/information", params=params)

    async def close(self):
        await self._client.aclose()
