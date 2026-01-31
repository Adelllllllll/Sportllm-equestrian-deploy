"""
Configuration & environment variables
"""
import os
from dotenv import load_dotenv

# Charge le .env localement
load_dotenv()

def get_config_value(key, default=None):
    """
    Récupère une configuration depuis streamlit secrets ou variables d'environnement.
    """
    # 1. On essaie de récupérer via Streamlit (utile pour le Cloud)
    try:
        import streamlit as st
        # On utilise .get() sur st.secrets pour éviter de lever l'exception
        # si le fichier secrets.toml n'existe pas.
        val = st.secrets.get(key)
        if val is not None:
            return val
    except Exception:
        # On ignore silencieusement les erreurs Streamlit en local
        pass
    
    # 2. Fallback sur le .env local (via os.getenv)
    return os.getenv(key, default)

# Neo4j Configuration
NEO4J_URI = get_config_value("NEO4J_URI")
NEO4J_USER = get_config_value("NEO4J_USER")
NEO4J_PASSWORD = get_config_value("NEO4J_PASSWORD")
NEO4J_DATABASE = get_config_value("NEO4J_DATABASE", "neo4j")

# OpenAI Configuration
OPENAI_API_KEY = get_config_value("OPENAI_API_KEY")

# Cost Configuration
COST_PER_1K_INPUT = 0.00015
COST_PER_1K_OUTPUT = 0.0006
COST_PER_1K_EMBEDDING = 0.00002  # text-embedding-3-small