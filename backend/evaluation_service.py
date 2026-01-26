"""
Semantic evaluation logic
"""
import json
from typing import Dict
import numpy as np
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from .config import OPENAI_API_KEY


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def calculate_semantic_similarity(answer: str, ground_truth: str, embeddings) -> float:
    """
    Calculate semantic similarity using embeddings
    Returns 0-1 score
    """
    if not answer or not ground_truth or "error" in answer.lower():
        return 0.0
    
    try:
        # Get embeddings
        answer_embedding = embeddings.embed_query(answer)
        truth_embedding = embeddings.embed_query(ground_truth)
        
        # Calculate similarity
        similarity = cosine_similarity(answer_embedding, truth_embedding)
        
        # Normalize to 0-1 range (cosine is -1 to 1)
        normalized = (similarity + 1) / 2
        
        return float(normalized)
    except Exception as e:
        print(f"⚠️  Embedding error: {e}")
        return 0.0


def llm_judge_answer(question: str, answer: str, ground_truth: str, judge_llm) -> Dict:
    """
    Use LLM to judge if answer is correct
    Returns scores for correctness, completeness, and accuracy
    """
    if not answer or "error" in answer.lower():
        return {
            'correctness': 0.0,
            'completeness': 0.0,
            'accuracy': 0.0,
            'overall': 0.0,
            'reasoning': 'Answer failed or contains error'
        }
    
    judge_prompt = f"""Tu es un évaluateur expert qui compare des réponses à des questions.

Question: {question}

Réponse de référence (ground truth): {ground_truth}

Réponse à évaluer: {answer}

Évalue la réponse sur ces critères (note de 0 à 1):

1. CORRECTNESS (Exactitude): La réponse contient-elle les bonnes informations?
   - 1.0 = Toutes les informations sont correctes
   - 0.5 = Certaines informations correctes, d'autres incorrectes
   - 0.0 = Informations incorrectes

2. COMPLETENESS (Complétude): La réponse couvre-t-elle tous les éléments de la ground truth?
   - 1.0 = Tous les éléments importants sont présents
   - 0.5 = Certains éléments manquent
   - 0.0 = La plupart des éléments manquent

3. ACCURACY (Précision): Les détails (noms, nombres, dates) sont-ils exacts?
   - 1.0 = Tous les détails sont exacts
   - 0.5 = Quelques erreurs de détails
   - 0.0 = Nombreuses erreurs de détails

IMPORTANT:
- La réponse peut être reformulée différemment et reste correcte
- Une réponse plus courte mais qui contient l'essentiel peut être bonne
- Focus sur le SENS, pas sur la formulation exacte

Réponds UNIQUEMENT en JSON (sans markdown):
{{
  "correctness": 0.0-1.0,
  "completeness": 0.0-1.0,
  "accuracy": 0.0-1.0,
  "overall": 0.0-1.0,
  "reasoning": "Explication courte"
}}"""

    try:
        response = judge_llm.invoke(judge_prompt)
        result_text = response.content.strip()
        
        # Remove markdown code blocks if present
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(result_text)
        
        # Ensure all scores are present
        result.setdefault('correctness', 0.0)
        result.setdefault('completeness', 0.0)
        result.setdefault('accuracy', 0.0)
        result.setdefault('overall', 0.0)
        result.setdefault('reasoning', 'No reasoning provided')
        
        return result
        
    except Exception as e:
        print(f"⚠️  LLM judge error: {e}")
        return {
            'correctness': 0.0,
            'completeness': 0.0,
            'accuracy': 0.0,
            'overall': 0.0,
            'reasoning': f'Evaluation error: {str(e)}'
        }


def init_evaluator():
    """Initialize LLM judge and embeddings"""
    judge_llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=OPENAI_API_KEY
    )
    
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY
    )
    
    return judge_llm, embeddings
