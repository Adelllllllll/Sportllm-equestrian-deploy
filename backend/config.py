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
    try:
        import streamlit as st
        # On vérifie si la clé existe dans st.secrets
        if key in st.secrets:
            return st.secrets[key]
    except ImportError:
        # Streamlit n'est pas installé ou utilisé dans ce contexte
        pass
    
    # Fallback sur les variables d'environnement classiques (.env ou système)
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