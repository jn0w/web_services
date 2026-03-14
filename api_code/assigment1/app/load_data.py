# this script reads the csv file, converts it to json, and loads it into mongodb
# run it with python -m app.load_data

import csv
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from app.database import get_mongo_client

# path to the csv file relative to this script
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "products.csv")

# mongo database and collection names
DB_NAME = "inventory"
COLLECTION_NAME = "products"


# reads the csv and turns each row into a dict with our field names
def csv_to_json(csv_path: str) -> list[dict]:
    products = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append(
                {
                    "id": int(row["ProductID"]),
                    "name": row["Name"],
                    "price": float(row["UnitPrice"]),
                    "quantity": int(row["StockQuantity"]),
                    "description": row["Description"],
                }
            )
    return products


# drops the old collection and inserts the fresh product list
def load_into_mongo(products: list[dict]) -> int:
    client = get_mongo_client()
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    collection.drop()
    result = collection.insert_many(products)
    client.close()
    return len(result.inserted_ids)


if __name__ == "__main__":
    # first convert csv to json and save it to a file
    products = csv_to_json(CSV_PATH)

    json_path = os.path.join(os.path.dirname(CSV_PATH), "products.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2)
    print(f"Converted {len(products)} products to JSON -> {json_path}")

    # then load the same data into mongo
    count = load_into_mongo(products)
    print(f"Inserted {count} products into MongoDB ({DB_NAME}.{COLLECTION_NAME})")
