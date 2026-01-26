"""
🐴 Equestrian News Scraper - ULTIMATE VERSION
Maximum sources + Easy to add new ones
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict
import feedparser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
import re


class EquestrianNewsScraper:
    """
    Ultimate equestrian news scraper with maximum source coverage
    Easy to add/remove sources as needed
    """
    
    def __init__(self, openai_api_key: str):
        """Initialize scraper with GPT for summarization"""
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            openai_api_key=openai_api_key
        )
        
        # ══════════════════════════════════════════════════════════════
        # 📰 RSS FEEDS - Easy to add more!
        # ══════════════════════════════════════════════════════════════
        self.rss_sources = {
            # Working sources ✅
            "Cheval Magazine": "https://www.chevalmag.com/feed/",
            "L'Éperon": "https://www.leperon.fr/feed/",
            "FEI": "https://www.fei.org/feed",
            "Grand Prix Magazine": "https://www.grandprix-replay.com/feed/",
            "Terre de Sport Équestre": "https://www.terredesportequestre.com/feed",
            "L'Équipe Équitation": "https://www.lequipe.fr/Equitation/rss.xml",
            
            # Add your own RSS feeds here! 👇
            # "Source Name": "https://source.com/feed/",
        }
        
        # ══════════════════════════════════════════════════════════════
        # 🌐 WEB SCRAPING SOURCES - Requires custom logic
        # ══════════════════════════════════════════════════════════════
        self.web_sources = {
            "FFE": {
                "url": "https://www.ffe.com/actualites",
                "enabled": True,
            },
            "IFCE": {
                "url": "https://www.ifce.fr/ifce/connaissances/actualites/",
                "enabled": True,
            },
            "Équipe France": {
                "url": "https://www.equipe-france.fr/equitation",
                "enabled": True,
            },
            "Petit Galop": {
                "url": "https://www.petit-galop.fr/",
                "enabled": True,  # Set to True to enable
            },
        }
    
    def fetch_news(self, max_articles: int = 25) -> List[Dict]:
        """
        Fetch news from all enabled sources
        Tries RSS first, then web scraping
        """
        all_articles = []
        
        print("📡 Fetching from RSS feeds...")
        print("─" * 60)
        
        # Try all RSS sources
        for source_name, url in self.rss_sources.items():
            articles = self._try_rss_source(source_name, url, max_articles // 2)
            if articles:
                all_articles.extend(articles)
                print(f"✅ {source_name}: {len(articles)} articles")
            else:
                print(f"⚠️  {source_name}: No articles (RSS may be unavailable)")
        
        print("\n🌐 Fetching from web sources...")
        print("─" * 60)
        
        # Try enabled web scraping sources
        for source_name, config in self.web_sources.items():
            if not config.get("enabled", False):
                print(f"⏭️  {source_name}: Disabled")
                continue
            
            articles = self._try_web_source(source_name, config["url"], max_articles // 3)
            if articles:
                all_articles.extend(articles)
                print(f"✅ {source_name}: {len(articles)} articles")
            else:
                print(f"⚠️  {source_name}: No articles found")
        
        # Sort by date
        all_articles.sort(key=lambda x: x['date'], reverse=True)
        
        # Deduplicate by title
        seen_titles = set()
        unique_articles = []
        for article in all_articles:
            title_lower = article['title'].lower()[:100]  # First 100 chars
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_articles.append(article)
        
        return unique_articles[:max_articles]
    
    def _try_rss_source(self, source_name: str, url: str, max_articles: int) -> List[Dict]:
        """Try to fetch from RSS feed (with robust error handling)"""
        articles = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                return []
            
            for entry in feed.entries[:max_articles]:
                try:
                    article = {
                        'source': source_name,
                        'title': entry.get('title', 'Sans titre'),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'summary': self._clean_html(
                            entry.get('summary', entry.get('description', ''))
                        ),
                        'date': self._parse_date(entry)
                    }
                    articles.append(article)
                except:
                    continue
        
        except Exception as e:
            pass  # Silent fail, will try other sources
        
        return articles
    
    def _try_web_source(self, source_name: str, url: str, max_articles: int) -> List[Dict]:
        """Try to scrape website (dispatches to specific scrapers)"""
        
        # Dispatch to specific scraper based on source
        if source_name == "FFE":
            return self._scrape_ffe(max_articles)
        elif source_name == "IFCE":
            return self._scrape_ifce(max_articles)
        elif source_name == "Équipe France":
            return self._scrape_equipe_france(max_articles)
        elif source_name == "Petit Galop":
            return self._scrape_petit_galop(max_articles)
        else:
            return self._scrape_generic(source_name, url, max_articles)
    
    def _scrape_ffe(self, max_articles: int = 10) -> List[Dict]:
        """Scrape FFE actualités"""
        articles = []
        
        try:
            url = "https://www.ffe.com/actualites"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            news_items = soup.find_all('article', limit=max_articles)
            
            for item in news_items:
                try:
                    title_elem = item.find(['h2', 'h3'])
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    link_elem = item.find('a', href=True)
                    link = ''
                    if link_elem:
                        href = link_elem.get('href', '')
                        link = href if href.startswith('http') else f"https://www.ffe.com{href}"
                    
                    summary_elem = item.find('p')
                    summary = summary_elem.get_text(strip=True)[:400] if summary_elem else ''
                    
                    if title:
                        articles.append({
                            'source': 'FFE',
                            'title': title,
                            'link': link,
                            'published': '',
                            'summary': summary,
                            'date': datetime.now()
                        })
                except:
                    continue
        
        except Exception as e:
            pass
        
        return articles
    
    def _scrape_ifce(self, max_articles: int = 10) -> List[Dict]:
        """Scrape IFCE actualités"""
        articles = []
        
        try:
            url = "https://www.ifce.fr/ifce/connaissances/actualites/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try multiple selectors
            news_items = soup.find_all('article', limit=max_articles)
            if not news_items:
                news_items = soup.find_all(['div', 'li'], class_=re.compile('(news|actualite|article)'), limit=max_articles)
            
            for item in news_items:
                try:
                    title_elem = item.find(['h1', 'h2', 'h3', 'h4'])
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    link_elem = item.find('a', href=True)
                    link = ''
                    if link_elem:
                        href = link_elem.get('href', '')
                        link = href if href.startswith('http') else f"https://www.ifce.fr{href}"
                    
                    summary_elem = item.find('p')
                    summary = summary_elem.get_text(strip=True)[:400] if summary_elem else ''
                    
                    if title:
                        articles.append({
                            'source': 'IFCE',
                            'title': title,
                            'link': link,
                            'published': '',
                            'summary': summary,
                            'date': datetime.now()
                        })
                except:
                    continue
        
        except Exception as e:
            pass
        
        return articles
    
    def _scrape_equipe_france(self, max_articles: int = 10) -> List[Dict]:
        """Scrape Équipe France équitation"""
        articles = []
        
        try:
            url = "https://www.equipe-france.fr/equitation"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find news articles
            news_items = soup.find_all(['article', 'div'], class_=re.compile('(news|article|actualite)'), limit=max_articles)
            
            for item in news_items:
                try:
                    title_elem = item.find(['h2', 'h3', 'h4'])
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    link_elem = item.find('a', href=True)
                    link = ''
                    if link_elem:
                        href = link_elem.get('href', '')
                        link = href if href.startswith('http') else f"https://www.equipe-france.fr{href}"
                    
                    summary_elem = item.find('p')
                    summary = summary_elem.get_text(strip=True)[:400] if summary_elem else ''
                    
                    if title:
                        articles.append({
                            'source': 'Équipe France',
                            'title': title,
                            'link': link,
                            'published': '',
                            'summary': summary,
                            'date': datetime.now()
                        })
                except:
                    continue
        
        except Exception as e:
            pass
        
        return articles
    
    def _scrape_petit_galop(self, max_articles: int = 10) -> List[Dict]:
        """Scrape Petit Galop"""
        articles = []
        
        try:
            url = "https://www.petit-galop.fr/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            news_items = soup.find_all(['article', 'div'], class_=re.compile('(post|article)'), limit=max_articles)
            
            for item in news_items:
                try:
                    title_elem = item.find(['h2', 'h3'])
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    link_elem = item.find('a', href=True)
                    link = ''
                    if link_elem:
                        href = link_elem.get('href', '')
                        link = href if href.startswith('http') else f"https://www.petit-galop.fr{href}"
                    
                    summary_elem = item.find('p')
                    summary = summary_elem.get_text(strip=True)[:400] if summary_elem else ''
                    
                    if title:
                        articles.append({
                            'source': 'Petit Galop',
                            'title': title,
                            'link': link,
                            'published': '',
                            'summary': summary,
                            'date': datetime.now()
                        })
                except:
                    continue
        
        except Exception as e:
            pass
        
        return articles
    
    def _scrape_generic(self, source_name: str, url: str, max_articles: int) -> List[Dict]:
        """Generic web scraper for any site"""
        articles = []
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try common article selectors
            news_items = soup.find_all(['article', 'div'], class_=re.compile('(news|article|post)'), limit=max_articles)
            
            for item in news_items:
                try:
                    title_elem = item.find(['h1', 'h2', 'h3'])
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    link_elem = item.find('a', href=True)
                    link = link_elem.get('href', '') if link_elem else ''
                    
                    summary_elem = item.find('p')
                    summary = summary_elem.get_text(strip=True)[:400] if summary_elem else ''
                    
                    if title:
                        articles.append({
                            'source': source_name,
                            'title': title,
                            'link': link,
                            'published': '',
                            'summary': summary,
                            'date': datetime.now()
                        })
                except:
                    continue
        
        except Exception as e:
            pass
        
        return articles
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags"""
        if not text:
            return ""
        clean = re.sub(r'<[^>]+>', '', text)
        return clean.strip()[:500]
    
    def _parse_date(self, entry) -> datetime:
        """Parse publication date"""
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
        except:
            pass
        return datetime.now()
    
    def get_weekly_summary(self, articles: List[Dict]) -> str:
        """Generate weekly summary using GPT"""
        
        if not articles:
            return "Aucune actualité disponible."
        
        two_weeks_ago = datetime.now() - timedelta(days=14)
        recent_articles = [a for a in articles if a['date'] > two_weeks_ago]
        
        if not recent_articles:
            recent_articles = articles[:10]
        
        articles_text = "\n\n".join([
            f"[{a['source']}] {a['title']}\n{a['summary'][:250]}..."
            for a in recent_articles[:12]
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Tu es un expert en sports équestres. 
Tu résumes les actualités équestres récentes en français.

Ton résumé doit:
- Être concis (250-350 mots maximum)
- Mentionner les événements importants
- Identifier les compétitions majeures
- Noter les performances remarquables
- Signaler les événements à venir si mentionnés
- Utiliser un ton professionnel mais accessible

Structure suggérée:
🏆 Compétitions et résultats majeurs
📅 Événements à venir
💡 Autres actualités importantes"""),
            ("user", "Voici les actualités équestres récentes:\n\n{articles}\n\nRésumé:")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({"articles": articles_text})
        
        return response.content
    
    def get_upcoming_events(self, articles: List[Dict]) -> List[Dict]:
        """Extract upcoming events - ONLY 2025+"""
        
        if not articles:
            return []
        
        articles_text = "\n\n".join([
            f"{a['title']}\n{a['summary'][:200]}..."
            for a in articles[:15]
        ])
        
        current_year = datetime.now().year
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Tu es un extracteur d'événements équestres.
Analyse les actualités et liste UNIQUEMENT les événements FUTURS mentionnés.

DATE ACTUELLE: Nous sommes en janvier {current_year}.

RÈGLES STRICTES:
- NE PAS inclure d'événements de 2024 ou avant
- Inclure SEULEMENT les événements de {current_year} et après
- Si un événement est en janvier {current_year} et déjà passé, ne l'inclus PAS

Format de réponse EXACT (un événement par ligne):
ÉVÉNEMENT | DATE | LIEU | TYPE

Exemples:
Jumping de Paris | Mars {current_year} | Paris, France | CSI5*
Championnats du monde | Août {current_year} | Allemagne | Championnat

Si AUCUN événement futur, réponds: AUCUN"""),
            ("user", "Actualités:\n\n{articles}\n\nÉvénements futurs:")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({"articles": articles_text})
        
        # Parse response
        events = []
        for line in response.content.strip().split('\n'):
            if 'AUCUN' in line or '|' not in line:
                continue
            
            try:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4:
                    events.append({
                        'name': parts[0],
                        'date': parts[1],
                        'location': parts[2],
                        'type': parts[3]
                    })
            except:
                continue
        
        return events
