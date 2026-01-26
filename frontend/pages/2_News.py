"""
Equestrian News Page - Professional Interface
==============================================
Enhanced UI with custom styling and professional loading indicators
"""

import streamlit as st
import os
from dotenv import load_dotenv
from datetime import datetime
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from backend.news_service import EquestrianNewsScraper

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Actualités Équestres | SportLLM",
    page_icon="📰",
    layout="wide"
)

# ============================================================================
# LOAD CUSTOM CSS
# ============================================================================

def load_css():
    """Load custom CSS styling"""
    css_file = Path(__file__).parent.parent / "style.css"
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden !important;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
        h1, h2, h3 {color: #4A5E7C; font-family: 'Georgia', serif;}
        </style>
        """, unsafe_allow_html=True)

load_css()
load_dotenv()

# ============================================================================
# PROFESSIONAL HEADER
# ============================================================================

st.markdown("""
<div class="professional-header">
    <h1 style="margin: 0; color: white;">Actualités Équestres</h1>
    <p style="margin: 0.5rem 0 0 0; color: rgba(255,255,255,0.9);">
        Les dernières nouvelles du monde équestre
    </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# NEWS SCRAPER INITIALIZATION
# ============================================================================

@st.cache_resource
def get_scraper():
    """Initialize the news scraper"""
    return EquestrianNewsScraper(os.getenv("OPENAI_API_KEY"))

@st.cache_data(ttl=86400)
def fetch_news_cached(max_articles):
    """Fetch news articles with 24h cache"""
    scraper = get_scraper()
    return scraper.fetch_news(max_articles=max_articles)

@st.cache_data(ttl=86400)
def get_summary_cached(_articles):
    """Generate weekly summary with 24h cache"""
    scraper = get_scraper()
    return scraper.get_weekly_summary(_articles)

@st.cache_data(ttl=86400)
def get_events_cached(_articles):
    """Extract upcoming events with 24h cache"""
    scraper = get_scraper()
    return scraper.get_upcoming_events(_articles)

# ============================================================================
# SIDEBAR CONTROLS
# ============================================================================

with st.sidebar:
    st.markdown('<h2>Paramètres</h2>', unsafe_allow_html=True)
    
    max_articles = st.slider(
        "Nombre d'articles",
        min_value=5,
        max_value=30,
        value=15,
        step=5
    )
    
    if st.button("Actualiser", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    st.caption(f"Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ============================================================================
# MAIN CONTENT
# ============================================================================

try:
    # Clean loading indicator
    with st.spinner("Chargement des actualités..."):
        articles = fetch_news_cached(max_articles)
    
    if not articles:
        st.warning("Aucune actualité disponible pour le moment.")
        st.stop()
    
    # ========================================================================
    # TABBED INTERFACE
    # ========================================================================
    
    tab1, tab2, tab3 = st.tabs([
        "Résumé Hebdomadaire", 
        "Événements à Venir", 
        "Tous les Articles"
    ])
    
    # ------------------------------------------------------------------------
    # TAB 1: WEEKLY SUMMARY
    # ------------------------------------------------------------------------
    
    with tab1:
        st.markdown("## Résumé de la Semaine")
        
        with st.spinner("Génération du résumé en cours..."):
            summary = get_summary_cached(articles)
        
        # Display in card
        st.markdown(f"""
        <div class="card-container">
            {summary}
        </div>
        """, unsafe_allow_html=True)
        
        sources = set(a['source'] for a in articles)
        st.info(f"Résumé basé sur {len(articles)} articles de {len(sources)} sources")
    
    # ------------------------------------------------------------------------
    # TAB 2: UPCOMING EVENTS
    # ------------------------------------------------------------------------
    
    with tab2:
        st.markdown("## Événements à Venir")
        
        with st.spinner("Extraction des événements..."):
            events = get_events_cached(articles)
        
        if events:
            for event in events:
                st.markdown(f"""
                <div class="card-container">
                    <h3 style="margin-top: 0;">{event['name']}</h3>
                    <p><strong>Date :</strong> {event['date']}</p>
                    <p><strong>Lieu :</strong> {event['location']}</p>
                    <p><strong>Type :</strong> <code>{event['type']}</code></p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucun événement futur identifié dans les actualités récentes.")
    
    # ------------------------------------------------------------------------
    # TAB 3: ALL ARTICLES
    # ------------------------------------------------------------------------
    
    with tab3:
        st.markdown("## Tous les Articles")
        
        # Source filter
        all_sources = sorted(set(a['source'] for a in articles))
        selected_sources = st.multiselect(
            "Filtrer par source :",
            options=all_sources,
            default=all_sources
        )
        
        filtered_articles = [a for a in articles if a['source'] in selected_sources]
        
        st.markdown(f'<p class="text-muted">Affichage de {len(filtered_articles)} articles</p>', unsafe_allow_html=True)
        
        # Display articles
        for i, article in enumerate(filtered_articles, 1):
            with st.expander(f"{i}. {article['title']}", expanded=(i <= 3)):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Source :** {article['source']}")
                    st.markdown(f"**Date :** {article['date'].strftime('%d/%m/%Y %H:%M')}")
                    
                    if article['summary']:
                        st.markdown("**Résumé :**")
                        st.markdown(article['summary'][:400] + ("..." if len(article['summary']) > 400 else ""))
                    
                    if article['link']:
                        st.markdown(f"[Lire l'article complet]({article['link']})")
                
                with col2:
                    days_ago = (datetime.now() - article['date']).days
                    if days_ago == 0:
                        st.success("Aujourd'hui")
                    elif days_ago == 1:
                        st.info("Hier")
                    else:
                        st.caption(f"Il y a {days_ago} jours")

except Exception as e:
    st.error(f"Erreur lors du chargement des actualités")
    st.info("Vérifiez votre connexion internet et votre clé OpenAI API.")
    
    with st.expander("Détails de l'erreur"):
        st.code(str(e))