"""
Configuration & environment variables
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Cost Configuration
COST_PER_1K_INPUT = 0.00015
COST_PER_1K_OUTPUT = 0.0006
COST_PER_1K_EMBEDDING = 0.00002  # text-embedding-3-small
