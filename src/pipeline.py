import os
import json
import time
from datetime import datetime
from pymongo import MongoClient
import redis

# Configuration
MONGO_URI = "mongodb://localhost:27017/?replicaSet=rs0&directConnection=true"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
DB_NAME = "radar_combustivel"

# Clients
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Cache for postos data (bairro, etc)
postos_cache = {}

def get_posto_data(posto_id):
    if posto_id in postos_cache:
        return postos_cache[posto_id]
    
    posto = db.postos.find_one({"posto_id": posto_id})
    if posto:
        postos_cache[posto_id] = {
            "bairro": posto["bairro"],
            "nome": posto["nome"],
            "bandeira": posto["bandeira"]
        }
        return postos_cache[posto_id]
    return None

def calculate_variation(posto_id, combustivel, new_price):
    # Get last price from Redis Time Series (ZSET)
    # Member format: "price:event_id"
    last_entries = r.zrevrange(f"ts:preco:{posto_id}:{combustivel}", 0, 0)
    if not last_entries:
        return 0.0
    
    try:
        last_price = float(last_entries[0].split(":")[0])
        variation = ((new_price - last_price) / last_price) * 100
        return round(variation, 2)
    except:
        return 0.0

def process_price_event(doc):
    posto_id = doc.get("posto_id")
    combustivel = doc.get("tipo_combustivel")
    preco = doc.get("preco")
    evento_id = doc.get("evento_id")
    timestamp = doc.get("timestamp").timestamp()

    posto_data = get_posto_data(posto_id)
    if not posto_data:
        print(f"Posto {posto_id} not found. Skipping.")
        return

    bairro = posto_data["bairro"]
    variation = calculate_variation(posto_id, combustivel, preco)

    pipe = r.pipeline()

    # 1. Update Posto Hash (Latest Info)
    pipe.hset(f"posto:{posto_id}", mapping={
        "nome": posto_data["nome"],
        "bairro": bairro,
        "bandeira": posto_data["bandeira"],
        combustivel: str(preco),
        "updated_at": str(int(timestamp))
    })

    # 2. Update Rankings (Bairro and Global)
    pipe.zadd(f"rank:{combustivel}:{bairro}", {posto_id: preco})
    pipe.zadd(f"rank:global:{combustivel}", {posto_id: preco})

    # 3. Update Time Series (Keep last 7 days)
    pipe.zadd(f"ts:preco:{posto_id}:{combustivel}", {f"{preco}:{evento_id}": int(timestamp)})
    # Trim old data (7 days = 604800 seconds)
    pipe.zremrangebyscore(f"ts:preco:{posto_id}:{combustivel}", 0, int(timestamp) - 604800)

    # 4. Update Variation Alerts (if abs variation > 1%)
    if abs(variation) > 1.0:
        pipe.zadd(f"alerta:variacao:24h:{combustivel}", {posto_id: abs(variation)})
    
    # 5. Increment updates counter in stats
    pipe.hincrby(f"stats:bairro:{bairro}", "updates_count", 1)

    pipe.execute()
    print(f"Processed price: {posto_id} at {bairro} (Var: {variation}%)")

def process_search_event(doc):
    bairro = doc.get("bairro_detectado")
    if bairro:
        r.hincrby(f"stats:bairro:{bairro}", "buscas_hoje", 1)
        # Reset count daily (using expire for simplicity as per spec)
        r.expire(f"stats:bairro:{bairro}", 86400)
        print(f"Processed search: {bairro}")

def run_pipeline():
    print("Pipeline starting... Listening to MongoDB Change Streams.")
    
    search_pipeline = [
        {"$match": {
            "operationType": "insert",
            "ns.coll": {"$in": ["precos_historico", "buscas"]}
        }}
    ]

    try:
        # Watch both collections
        with db.watch(search_pipeline) as stream:
            for change in stream:
                coll = change["ns"]["coll"]
                doc = change["fullDocument"]
                
                if coll == "precos_historico":
                    process_price_event(doc)
                elif coll == "buscas":
                    process_search_event(doc)
    except Exception as e:
        print(f"Pipeline Error: {e}")
        time.sleep(5)
        run_pipeline()

if __name__ == "__main__":
    run_pipeline()
