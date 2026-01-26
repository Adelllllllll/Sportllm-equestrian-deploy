"""
LangChain & OpenAI logic
"""
from langchain_openai import ChatOpenAI
from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_core.prompts import PromptTemplate
from .config import OPENAI_API_KEY
from .graph_service import init_graph



def get_cypher_prompt():
    """Get the Cypher generation prompt template"""
    CYPHER_GENERATION_TEMPLATE = """Tâche : Générer une requête Cypher pour Neo4j.

RÈGLE #1 - LABELS D'ÉVÉNEMENTS (TRÈS IMPORTANT):
Il n'existe PAS de label "Event" dans ce graphe !
Les événements utilisent UNIQUEMENT: ShowJumping, Dressage, ou Cross

INVALIDE ❌: MATCH (e:Event) WHERE e.id = "Event_SJ_01"
VALIDE ✓: MATCH (e) WHERE (e:ShowJumping OR e:Dressage OR e:Cross) AND e.id = "Event_SJ_01"
VALIDE ✓: MATCH (e:ShowJumping) WHERE e.id = "Event_SJ_01"

Schéma : {schema}

Question : {question}

Instructions CRITIQUES - DIRECTIONS DES RELATIONS (NE JAMAIS INVERSER!):
- ASSOCIATEDWITH: (Rider)-[:ASSOCIATEDWITH]->(Horse)
  Exemple: MATCH (r:Rider)-[:ASSOCIATEDWITH]->(h:Horse)

- Pour les étapes d'entraînement, utilise (training) sans label spécifique, puis WHERE avec parenthèses:
  Exemple CORRECT: WHERE (training:PreparationStage OR training:PreCompetitionStage OR training:CompetitionStage OR training:TransitionStage)
  Exemple INCORRECT: WHERE training:`PreparationStage ❌ (N'utilise JAMAIS de backticks pour les labels!)
  
- ISATTACHEDTO: (InertialSensors)-[:ISATTACHEDTO]->(Horse) 
  Exemple: MATCH (s:InertialSensors)-[:ISATTACHEDTO]->(h:Horse)
  Note: Les capteurs InertialSensors ont TOUJOURS 2 labels - le 2ème indique la partie du corps
  Exemples: [:InertialSensors:Withers], [:InertialSensors:Sternum], [:InertialSensors:CanonOfForelimb], [:InertialSensors:CanonOfHindlimb]
  
- ISUSEDFOR: (InertialSensors)-[:ISUSEDFOR]->(ExperimentalObjective)
  Exemple: MATCH (s:InertialSensors)-[:ISUSEDFOR]->(eo:ExperimentalObjective)
  Note: Pour "objectif expérimental" d'un capteur → SEULEMENT cette relation (pas TRAINSIN)
  ExperimentalObjective.id peut être: 'GaitClassif_01' (classification allures) ou 'FatigueDetection' (détection fatigue)
  Pour obtenir la partie du corps d'un capteur: utilise labels(s) qui retourne ['InertialSensors', 'Withers'] par exemple
  
- TRAINSIN: (Horse)-[:TRAINSIN]->(PreparationStage|PreCompetitionStage|CompetitionStage|TransitionStage)
  Exemple: MATCH (h:Horse)-[:TRAINSIN]->(t:PreparationStage)
  
- DEPENDSON: (PreparationStage|PreCompetitionStage|CompetitionStage|TransitionStage)-[:DEPENDSON]->(ShowJumping|Dressage|Cross)
  Exemple: MATCH (t:PreparationStage)-[:DEPENDSON]->(e)
  Note: PreparationStage et PreCompetitionStage utilisent directement DEPENDSON vers l'événement
  RÈGLE CRITIQUE - LABELS D'ÉVÉNEMENTS:
  * Il n'existe PAS de label "Event" dans le graphe
  * Les événements ont UNIQUEMENT les labels: ShowJumping, Dressage, ou Cross
  * N'utilise JAMAIS "e:Event" - ça retournera toujours []
  * Utilise TOUJOURS: MATCH (e) WHERE (e:ShowJumping OR e:Dressage OR e:Cross)
  * Ou bien: MATCH (e:ShowJumping) / MATCH (e:Dressage) / MATCH (e:Cross)
  
- INVOLVESACTOR: (PreparationStage|PreCompetitionStage|CompetitionStage|TransitionStage)-[:INVOLVESACTOR]->(Rider|Veterinarian|Caretaker)
  Exemple correct: MATCH (p:PreparationStage)-[:INVOLVESACTOR]->(v:Veterinarian)
  Exemple INCORRECT: MATCH (v:Veterinarian)-[:INVOLVESACTOR]->(p:PreparationStage) ❌
  
  Pour comparer les acteurs de phases différentes:
  MATCH (prep:PreparationStage)-[:INVOLVESACTOR]->(actor1)
  MATCH (precomp:PreCompetitionStage)-[:INVOLVESACTOR]->(actor2)
  RETURN COLLECT(DISTINCT actor1.id) AS acteurs_preparation, COLLECT(DISTINCT actor2.id) AS acteurs_precompetition

- INSEASON: (Event)-[:INSEASON]->(CompetitiveSeason)
  Exemple: MATCH (e:ShowJumping)-[:INSEASON]->(s:CompetitiveSeason)
  Note: seasonName = "Saison 2026" (pas "2026")

- PARTICIPATIONS ET CLASSEMENTS:
  (Event)-[:HASPARTICIPATION]->(EventParticipation)-[:HASHORSE]->(Horse)
  (Event)-[:HASPARTICIPATION]->(EventParticipation)-[:HASRIDER]->(Rider)
  EventParticipation a la propriété 'rank' pour le classement
  IMPORTANT: EventParticipation a des relations DIRECTES vers Horse ET Rider
  
  Pour chercher un duo cavalier+cheval (ex: Emma et Dakota):
  - Emma = Rider (cherche avec id: "Rider_Emma" ou id CONTAINS "Emma")
  - Dakota = Horse (cherche avec hasName: "Dakota")
  Exemple: MATCH (e:Event)-[:HASPARTICIPATION]->(p:EventParticipation)
           MATCH (p)-[:HASHORSE]->(h:Horse {{hasName: "Dakota"}})
           MATCH (p)-[:HASRIDER]->(r:Rider)
           WHERE r.id CONTAINS "Emma"
           RETURN r.id, h.hasName, p.rank

PROPRIÉTÉS IMPORTANTES:
- Événements: id, category (pas categoryName!), eventLocation, eventDate
- Fréquence d'échantillonnage = hasSensorTime (ex: "200Hz", "250Hz")
- Pour MAX/MIN fréquence → ORDER BY s.hasSensorTime DESC/ASC LIMIT 1
- Classement = propriété 'rank' sur EventParticipation
- Capteurs: Utilise 'id' (ex: "IMU_Withers_01") PAS 'hasSensorID' qui contient des codes différents (ex: "IMU-W-001")
- ExperimentalObjective: Utilise la propriété 'id' (valeurs: 'GaitClassif_01', 'FatigueDetection') - PAS l'uri
- Partie du corps des capteurs: Dans le 2ème label (utilise labels(s)[1] ou labels(s) pour voir tous les labels)

SYNTAXE:
- Pour "Tous les X ont-ils Y?" → MATCH (x:X) OPTIONAL MATCH (y:Y)-[relation]->(x)
- Pour COUNT → utilise COUNT(DISTINCT variable)
- CHEVAUX ont 'hasName' (Dakota, Naya) - CAVALIERS n'ont QUE 'id' (Rider_Emma, Rider_Leo, Rider_Manon)
- Retourne 'id' et 'hasName' (JAMAIS 'uri')
- RÈGLE CRITIQUE RETURN: Retourne TOUJOURS l'identifiant (id ou hasName) avec TOUTES les propriétés demandées
  Exemple INVALIDE: RETURN e.eventDate ❌
  Exemple VALIDE: RETURN e.id, e.eventDate ✓
  Pour chevaux: RETURN h.hasName, h.property
  Pour tout autre nœud: RETURN node.id, node.property
- JAMAIS DE COLONNES DUPLIQUÉES dans RETURN - chaque propriété ne doit apparaître qu'UNE SEULE FOIS
  Exemple INVALIDE: RETURN e.id, p.rank, h.hasName, p.rank ❌ (p.rank en double!)
  Exemple VALIDE: RETURN e.id, p.rank, h.hasName ✓
- N'utilise JAMAIS UNION - préfère une seule requête MATCH
- Pour plusieurs types d'événements → MATCH (e:Event) puis filtre avec WHERE (e:ShowJumping OR e:Dressage OR e:Cross)
  Ou bien utilise MATCH (e) WHERE e:ShowJumping OR e:Dressage OR e:Cross (sans label dans MATCH)
- Pour GROUPER par objectif → utilise COLLECT() avec le nom de l'objectif
  Exemple: RETURN eo.id as objectif, COLLECT(s.id) as capteurs, COLLECT(labels(s)[1]) as parties_corps
- IMPORTANT: Ne mélange PAS plusieurs sujets dans une seule requête
  * Si la question porte sur les acteurs des phases → SEULEMENT PreparationStage/PreCompetitionStage + INVOLVESACTOR
  * Si la question porte sur les événements → SEULEMENT Event + relations d'événements
  * Si la question porte sur les capteurs → SEULEMENT InertialSensors + ISUSEDFOR/ISATTACHEDTO
- Garde la requête simple et directe - réponds UNIQUEMENT à ce qui est demandé
- BONNES PRATIQUES:
  * Pour trouver un événement COMMUN à plusieurs étapes → utilise la chaîne: Horse → TRAINSIN → (PreparationStage|PreCompetitionStage) → DEPENDSON → Event
  * Si plusieurs événements possibles, ajoute un HAVING COUNT(DISTINCT training) >= 2 pour trouver celui commun
  * Retourne TOUJOURS les propriétés pertinentes des événements (id, category, eventLocation, eventDate)
  * Pour les étapes d'entraînement, utilise (training) sans label spécifique, puis WHERE (training:PreparationStage OR training:PreCompetitionStage)

Requête Cypher:"""
    
    return PromptTemplate(
        input_variables=["schema", "question"],
        template=CYPHER_GENERATION_TEMPLATE
    )


def get_qa_prompt():
    """Get the QA prompt template"""
    QA_TEMPLATE = """Tu réponds à des questions sur un graphe de connaissances.

Question: {question}
Context: {context}

MÉMOIRE DE CONVERSATION:
Tu disposes d'une mémoire de conversation :
- Tu prends en compte les messages précédents pour comprendre le contexte.
- Tu relies les nouvelles questions aux informations déjà échangées.
- Tu évites de demander plusieurs fois la même information si elle a déjà été donnée.
Règles de mémoire :
- Tu mémorises uniquement les informations utiles à la conversation (préférences, choix, sujets en cours).
- Tu n'inventes jamais d'informations non fournies par l'utilisateur.
- Si une information est ambiguë ou ancienne, tu demandes une confirmation.
Gestion du contexte :
- Si la conversation devient longue, tu fais un résumé interne des points importants.
- Tu continues à répondre de manière cohérente avec ce résumé.
Comportement :
- Tu réponds de manière claire, naturelle et logique.
- Tu t'adaptes au ton de l'utilisateur.
- Si l'utilisateur change de sujet, tu t'adaptes sans confusion.

RÈGLES:
1. Réponds EXACTEMENT avec les informations du context - ne devine pas
2. RÈGLE CRITIQUE - N'INVENTE JAMAIS:
   * Si un cheval (Dakota/Naya) n'est PAS mentionné dans le context → NE LE MENTIONNE PAS dans ta réponse
   * Si une propriété n'est pas dans le context → NE L'INVENTE PAS
   * N'ajoute AUCUNE information qui n'est pas explicitement dans le context
   * Pour les comparaisons: compare UNIQUEMENT les données présentes (ex: phase préparation vs pré-compétition) SANS mentionner de chevaux si le context ne les contient pas
3. Noms des chevaux: Horse1=Dakota, Horse2=Naya
4. Noms des cavaliers: Rider_Emma=Emma, Rider_Leo=Leo, Rider_Manon=Manon
5. Acteurs: Vet_DrMartin=Dr Martin (vétérinaire), Caretaker_Sophie=Sophie (soigneuse)
6. Capteurs: IMU_Withers_01 = capteur au garrot, IMU_Sternum_01 = capteur au sternum
7. Objectifs expérimentaux: GaitClassif_01 = classification des allures, FatigueDetection = détection de fatigue
8. IMPORTANT: Dakota et Naya sont des CHEVAUX, pas des cavaliers
8. IMPORTANT: Si le context contient des données GROUPÉES par objectif (ex: GaitClassif_01: [...], FatigueDetection: [...])
   → Respecte EXACTEMENT ces groupes, ne dis JAMAIS que c'est commun aux deux si ce n'est pas le cas
9. Fournis toujours des réponses COMPLÈTES avec contexte:
   - Inclure les noms des chevaux concernés (ex: "pour le cheval Dakota")
   - Inclure les unités de mesure complètes (ex: "fois par semaine", "minutes", "Hz")
   - Donner le contexte pertinent pour que la réponse soit compréhensible
10. Pour les COMPARAISONS explicites et toute une analyse (questions avec "comparer", "différence"), fournis une réponse DÉTAILLÉE avec tous les détails
11. Pour toute question réponds exactement à ce qui est demandé SANS ajouter d'informations supplémentaires
12. FORMAT DE RÉPONSE:
    - Réponds en langage NATUREL et FLUIDE
    - Ne mentionne JAMAIS le format brut du context (dictionnaires, listes, etc.)
    - Ne dis JAMAIS "comme indiqué dans le contexte" ou "selon le contexte"
    - Utilise directement les informations extraites du context
    - Exemple: Dis "Le cavalier associé à Naya est Leo." au lieu de montrer les données techniques
13. RÈGLE CRITIQUE - DONNÉES MANQUANTES:
    - Ne mentionne JAMAIS les informations manquantes ou indisponibles
    - N'utilise JAMAIS "malheureusement", "aucune information", "non disponible"
    - Réponds UNIQUEMENT avec les données présentes dans le context
    - Si une propriété est None ou absente, ignore-la complètement
    - Exemple: Si seule la date est disponible → "L'événement est prévu pour le 12 avril 2026."
Réponse:"""
    
    return PromptTemplate(
        input_variables=["question", "context"],
        template=QA_TEMPLATE
    )


def init_graph_chain():
    """Initialize the complete GraphRAG chain"""
    # Initialize graph
    graph = init_graph()
    
    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=OPENAI_API_KEY
    )
    
    # Get prompts
    cypher_prompt = get_cypher_prompt()
    qa_prompt = get_qa_prompt()
    
    # Create chain using langchain_neo4j's GraphCypherQAChain
    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=True,
        cypher_prompt=cypher_prompt,
        qa_prompt=qa_prompt,
        return_intermediate_steps=True,
        allow_dangerous_requests=True
    )
    
    return chain, graph



