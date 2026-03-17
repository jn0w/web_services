import os
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from prometheus_fastapi_instrumentator import Instrumentator
from pymongo import MongoClient

from app.models import ConvertedPriceOut, PaginateParams, ProductIn, ProductOut

# load env variables from the .env file so we can use them below
load_dotenv()

# grab the mongo connection string and exchange rate api key from env
MONGO_URI = os.environ.get("MONGO_URI", "")
EXCHANGE_RATE_API_KEY = os.environ.get("EXCHANGE_RATE_API_KEY", "")

# name of the database and collection we use in mongo
DB_NAME = "inventory"
COLLECTION_NAME = "products"

# this will hold the mongo client once the app starts up
db_client: MongoClient | None = None


# this runs when the app starts and shuts down
# it opens the mongo connection at the start and closes it when we stop the server
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_client
    db_client = MongoClient(MONGO_URI)
    yield
    if db_client:
        db_client.close()


# create the fastapi app and pass in the lifespan handler from above
app = FastAPI(
    title="Inventory API",
    description="FastAPI inventory management system backed by MongoDB",
    version="1.0.0",
    lifespan=lifespan,
)

# set up prometheus monitoring so we can track how the api is performing
# this adds a /metrics endpoint that shows request counts, response times, etc
Instrumentator().instrument(app).expose(app)


# helper to get the products collection from mongo so we dont repeat this everywhere
def _get_collection():
    return db_client[DB_NAME][COLLECTION_NAME]


# mongo adds its own _id field to every document, we dont want to send that back
# so this just removes it before we return the data
def _serialise(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


# get a single product by its id
@app.get("/getSingleProduct", response_model=ProductOut)
def get_single_product(
    id: int = Query(..., gt=0, description="Product ID to look up"),
):
    product = _get_collection().find_one({"id": id})
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with id {id} not found")
    return _serialise(product)


# get every product in the database
@app.get("/getAll", response_model=list[ProductOut])
def get_all():
    products = _get_collection().find()
    return [_serialise(p) for p in products]


# add a new product to the database
# pydantic checks the data types for us automatically through ProductIn
@app.post("/addNew", response_model=ProductOut, status_code=201)
def add_new(product: ProductIn):
    collection = _get_collection()

    # make sure a product with this id doesnt already exist
    if collection.find_one({"id": product.id}):
        raise HTTPException(
            status_code=409, detail=f"Product with id {product.id} already exists"
        )

    # convert the pydantic model to a dict and insert it into mongo
    doc = product.model_dump()
    collection.insert_one(doc)
    return _serialise(doc)


# delete a product by its id
@app.delete("/deleteOne")
def delete_one(
    id: int = Query(..., gt=0, description="Product ID to delete"),
):
    result = _get_collection().delete_one({"id": id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"Product with id {id} not found")
    return {"detail": f"Product {id} deleted"}


# find all products whose name starts with the given letter
# uses a regex query in mongo, case insensitive
@app.get("/startsWith", response_model=list[ProductOut])
def starts_with(
    letter: str = Query(
        ..., min_length=1, max_length=1, description="Starting letter to filter by"
    ),
):
    regex = f"^{letter}"
    products = _get_collection().find({"name": {"$regex": regex, "$options": "i"}})
    return [_serialise(p) for p in products]


# return products between a start id and end id, limited to 10 results
@app.get("/paginate", response_model=list[ProductOut])
def paginate(
    start: int = Query(..., gt=0, description="Product ID to start from"),
    end: int = Query(..., gt=0, description="Product ID to end at"),
):
    if start > end:
        raise HTTPException(
            status_code=400, detail="'start' must be less than or equal to 'end'"
        )

    # find products in the id range, sort by id, and cap it at 10
    products = (
        _get_collection()
        .find({"id": {"$gte": start, "$lte": end}})
        .sort("id", 1)
        .limit(10)
    )
    return [_serialise(p) for p in products]


# convert a products price from usd to eur using the exchangerate api
@app.get("/convert", response_model=ConvertedPriceOut)
async def convert(
    id: int = Query(..., gt=0, description="Product ID to convert price for"),
):
    # make sure the api key is actually set
    if not EXCHANGE_RATE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Exchange rate API key is not configured on the server.",
        )

    product = _get_collection().find_one({"id": id})
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with id {id} not found")

    # call the exchange rate api to get live usd to eur rate
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/latest/USD",
            timeout=10,
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502, detail="Failed to fetch exchange rate from provider"
            )

        data = resp.json()

        # check that the api returned a successful response
        if data.get("result") != "success":
            raise HTTPException(
                status_code=502,
                detail=f"Exchange rate API error: {data.get('error-type', 'unknown')}",
            )

        # pull the eur rate out of the conversion rates
        conversion_rates = data.get("conversion_rates", {})
        eur_rate = conversion_rates.get("EUR")
        if eur_rate is None:
            raise HTTPException(status_code=502, detail="EUR rate not available")

    # multiply the usd price by the eur rate and return everything
    return ConvertedPriceOut(
        id=product["id"],
        name=product["name"],
        original_price_usd=product["price"],
        converted_price_eur=round(product["price"] * eur_rate, 2),
        exchange_rate=eur_rate,
    )
