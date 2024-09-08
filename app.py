from flask import Flask, jsonify, request
import requests
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
from functools import lru_cache

app = Flask(__name__)

# Accepted all origins to access the api
CORS(app, resources={r"/*": {"origins": "*"}})

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/markets"


# Swagger specific
SWAGGER_URL = "/swagger"  # URL for exposing Swagger UI (without trailing '/')
API_URL = "/static/swagger.json"  # URL for exposing the OpenAPI/Swagger JSON schema
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL, API_URL, config={"app_name": "Crypto API"}
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


# Function to fetch and filter coins data
@lru_cache(maxsize=1)  # Cache the API response
def fetch_and_filter_crypto_data(search=None, sort_by=None):
    """
    Get Filtered Cryptocurrency Projects
    ---
    parameters:
      - name: search
        in: query
        type: string
        required: false
        description: Search term for cryptocurrency (e.g. 'eth' for Ethereum)
      - name: sort_by
        in: query
        type: string
        required: false
        description: Sort results by 'market_cap' or 'volume'
    """
    params = {
        "vs_currency": "usd",  # Retrieve data in USD
        "order": "market_cap_desc",  # Order by market cap descending
        "per_page": 100,  # Fetch 100 coins per page
        "page": 5,  # Page number
        "sparkline": "false",
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    response = requests.get(COINGECKO_API_URL, params=params, headers=headers)

    if response.status_code != 200:
        return []

    coins = response.json()

    filtered_coins = []

    for coin in coins:
        try:
            # Apply all filter conditions inside a single if statement
            fdv = coin.get("fully_diluted_valuation")
            max_supply = coin.get("max_supply")
            total_supply = coin.get("total_supply")
            market_cap = coin.get("market_cap")
            total_volume = coin.get("total_volume")
            tvl = coin.get("tvl", None)  # TVL may not exist, so default to None
            coin_name = coin.get("name", "").lower()

            # Apply all filter conditions, including search term
            if (
                market_cap is not None
                and market_cap > 0  # Market Capitalization > 0
                and max_supply is not None  # Max supply should not be None
                and total_supply is not None  # Total supply should not be None
                and max_supply == total_supply  # Max supply equals total supply
                and fdv is not None
                and fdv
                < int(
                    request.args.get("fdv", 100000000)
                )  # FDV < $100M or FDV < user input
                and total_volume is not None
                and total_volume > 50000  # 24-hour trading volume > $50k
                and (tvl is None or tvl > 50000)  # TVL > $50k, if TVL exists
                and (
                    search is None or search.lower() in coin_name
                )  # Search term in the name
            ):
                filtered_coins.append(coin)
        except KeyError as e:
            print(f"Missing expected field in coin data: {e}")
            continue

    # Sort the filtered coins based on the `sort_by` parameter
    if sort_by == "market_cap":
        filtered_coins = sorted(
            filtered_coins, key=lambda x: x["market_cap"], reverse=True
        )
    elif sort_by == "volume":
        filtered_coins = sorted(
            filtered_coins, key=lambda x: x["total_volume"], reverse=True
        )

    return filtered_coins


# API endpoint to return filtered data
@app.route("/projects", methods=["GET"])
def get_filtered_projects():
    # Get the search term and sort option from the request parameters
    pass
    search = request.args.get("search", None)
    sort_by = request.args.get("sort_by", None)

    projects = fetch_and_filter_crypto_data(search=search, sort_by=sort_by)

    return jsonify(projects)


if __name__ == "__main__":
    app.run(debug=True)
