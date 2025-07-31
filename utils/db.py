from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

db=client["finbot-api"]
collection=db["query_responses"]

def save_query_response(query,response,clauses,user=None):
    doc={
        "query": query,
        "response": response,
        "clauses": clauses,
        "user": user
    }
    collection.insert_one(doc)