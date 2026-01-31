# test_connection.py
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 1. Charger les variables
load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

print(f"1. Tentative de connexion à : {uri}")
print(f"2. Utilisateur : {user}")
print(f"3. Mot de passe (longueur) : {len(password) if password else 'VIDE'}")

if not uri or not password:
    print("❌ ERREUR : Les variables d'environnement ne sont pas chargées !")
    exit()

try:
    # Test basique de connexion
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    print("✅ CONNEXION RÉUSSIE ! Le serveur est accessible.")
    
    # Test de lecture
    with driver.session() as session:
        count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
        print(f"✅ La base contient {count} nœuds.")
        
    driver.close()
except Exception as e:
    print("\n❌ ÉCHEC DE LA CONNEXION :")
    print(e)
    print("\n💡 Pistes de solution :")
    print("- Si l'erreur est 'Unauthorized' -> Vérifiez le mot de passe.")
    print("- Si l'erreur est 'ServiceUnavailable' -> Vérifiez l'URI ou le Pare-feu.")
    print("- Si vous êtes sur un réseau d'école/entreprise -> Le port 7687 est souvent bloqué.")