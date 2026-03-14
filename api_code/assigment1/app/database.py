import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# load the .env file so MONGO_URI is available
load_dotenv()


# creates a mongo client using the connection string from the env
def get_mongo_client() -> MongoClient:
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("MONGO_URI environment variable is not set.")

    return MongoClient(mongo_uri)


# quick test to see if we can actually reach the mongo server
# returns true if the ping works, false if it doesnt
def test_connection() -> bool:
    client = get_mongo_client()
    try:
        client.admin.command("ping")
        return True
    except ConnectionFailure:
        return False
    finally:
        client.close()


# you can run this file directly to test the connection
# just do python -m app.database
if __name__ == "__main__":
    if test_connection():
        print("MongoDB connection successful.")
    else:
        print("MongoDB connection FAILED.")
