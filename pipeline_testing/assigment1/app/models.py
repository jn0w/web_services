from pydantic import BaseModel, Field


# this is what we expect when someone sends us a new product to add
# pydantic will reject the request if any field is missing or the wrong type
class ProductIn(BaseModel):
    id: int = Field(..., gt=0, description="Unique product ID (positive integer)")
    name: str = Field(..., min_length=1, description="Product name")
    price: float = Field(..., gt=0, description="Product price in USD")
    quantity: int = Field(..., ge=0, description="Stock quantity")
    description: str = Field(..., min_length=1, description="Product description text")


# this is the shape of the product data we send back in responses
class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    quantity: int
    description: str


# response model for the convert endpoint
# includes the original usd price, the converted eur price, and the rate used
class ConvertedPriceOut(BaseModel):
    id: int
    name: str
    original_price_usd: float
    converted_price_eur: float
    exchange_rate: float


# used to validate the start and end params for the paginate endpoint
class PaginateParams(BaseModel):
    start: int = Field(..., gt=0, description="Product ID to start from")
    end: int = Field(..., gt=0, description="Product ID to end at")
