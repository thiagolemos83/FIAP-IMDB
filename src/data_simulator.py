import random
import time
from datetime import datetime, timedelta
from pymongo import MongoClient
from faker import Faker

fake = Faker('pt_BR')

# Configuration
MONGO_URI = "mongodb://localhost:27017/?replicaSet=rs0&directConnection=true"
DB_NAME = "radar_combustivel"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

COMBUSTIVEIS = ["gasolina_comum", "etanol", "diesel_s10"]
BAIRROS = ["bela_vista", "pinheiros", "itaim_bibi", "vila_madalena", "moema"]

def seed_postos(n=10):
    if db.postos.count_documents({}) > 0:
        print("Postos already seeded.")
        return list(db.postos.find({}, {"_id": 0, "posto_id": 1}))

    print(f"Seeding {n} postos...")
    postos = []
    for i in range(n):
        posto_id = f"POSTO_{i+1:03d}"
        bairro = random.choice(BAIRROS)
        posto = {
            "posto_id": posto_id,
            "nome": f"Posto {fake.company()}",
            "endereco": f"{fake.street_name()}, {random.randint(1, 2000)}",
            "bairro": bairro,
            "cidade": "São Paulo",
            "uf": "SP",
            "localizacao": {
                "type": "Point",
                "coordinates": [float(fake.longitude()), float(fake.latitude())]
            },
            "bandeira": random.choice(["Shell", "Ipiranga", "Petrobras", "Ale"]),
            "servicos": random.sample(["troca_oleo", "lavagem", "conveniencia"], k=random.randint(1, 3)),
            "ativo": True,
            "metadata": {
                "updated_at": datetime.utcnow()
            }
        }
        postos.append(posto)
    
    db.postos.insert_many(postos)
    db.postos.create_index([("posto_id", 1)], unique=True)
    db.postos.create_index([("localizacao", "2dsphere")])
    return [{"posto_id": p["posto_id"]} for p in postos]

def generate_price_event(postos):
    posto = random.choice(postos)
    combustivel = random.choice(COMBUSTIVEIS)
    
    # Realistic base prices
    base_prices = {"gasolina_comum": 5.50, "etanol": 4.10, "diesel_s10": 6.00}
    price = base_prices[combustivel] * random.uniform(0.95, 1.05)
    
    event = {
        "evento_id": f"EVT_{int(time.time() * 1000)}",
        "posto_id": posto["posto_id"],
        "tipo_combustivel": combustivel,
        "preco": round(price, 3),
        "timestamp": datetime.utcnow(),
        "origem": "simulator"
    }
    db.precos_historico.insert_one(event)
    print(f"Inserted price: {posto['posto_id']} - {combustivel}: R$ {price:.3f}")

def generate_search_event():
    event = {
        "busca_id": f"BUSCA_{int(time.time() * 1000)}",
        "user_id": f"USER_{random.randint(1, 100)}",
        "timestamp": datetime.utcnow(),
        "localizacao_busca": {
            "type": "Point",
            "coordinates": [float(fake.longitude()), float(fake.latitude())]
        },
        "raio_km": random.choice([2, 5, 10]),
        "combustivel_filtro": random.choice(COMBUSTIVEIS),
        "bairro_detectado": random.choice(BAIRROS),
        "resultados_retornados": random.randint(0, 10)
    }
    db.buscas.insert_one(event)
    print(f"Inserted search in {event['bairro_detectado']}")

if __name__ == "__main__":
    try:
        postos = seed_postos()
        print("Simulator running. Press Ctrl+C to stop.")
        while True:
            # Randomly pick between price and search events
            if random.random() < 0.7:
                generate_price_event(postos)
            else:
                generate_search_event()
            
            time.sleep(random.uniform(1.0, 3.0))
    except KeyboardInterrupt:
        print("Simulator stopped.")
    except Exception as e:
        print(f"Error: {e}")
