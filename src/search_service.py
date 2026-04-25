# -*- coding: utf-8 -*-
"""
Search service module.

Responsibilities:
1. Provide a unified news search interface.
2. Support KR search through Naver and global search through Tavily, Brave, and SerpAPI.
3. Support multi-key load balancing and failover.
4. Cache and format search results.
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from itertools import cycle
import requests
from newspaper import Article, Config

from data_provider.us_index_mapping import is_us_index_code

logger = logging.getLogger(__name__)


def fetch_url_content(url: str, timeout: int = 5) -> str:
    """Fetch article text from a URL with newspaper3k."""
    try:
        config = Config()
        config.browser_user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        config.request_timeout = timeout
        config.fetch_images = False
        config.memoize_articles = False

        article = Article(url, config=config, language='ko')
        article.download()
        article.parse()

        text = article.text.strip()

        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)

        return text[:1500]
    except Exception as e:
        logger.debug(f"Fetch content failed for {url}: {e}")

    return ""


@dataclass
class SearchResult:
    """Search result value object."""
    title: str
    snippet: str  # Summary text.
    url: str
    source: str  # Source website.
    published_date: Optional[str] = None
    
    def to_text(self) -> str:
        """Convert the result into text."""
        date_str = f" ({self.published_date})" if self.published_date else ""
        return f"[{self.source}] {self.title}{date_str}\n{self.snippet}"


@dataclass 
class SearchResponse:
    """Search response."""
    query: str
    results: List[SearchResult]
    provider: str  # Search provider used.
    success: bool = True
    error_message: Optional[str] = None
    search_time: float = 0.0  # Search duration in seconds.
    
    def to_context(self, max_results: int = 5) -> str:
        """Convert search results into context text for AI analysis."""
        if not self.success or not self.results:
            return f"'{self.query}' 검색에서 관련 결과를 찾지 못했습니다."
        
        lines = [f"[{self.query} 검색 결과](출처: {self.provider})"]
        for i, result in enumerate(self.results[:max_results], 1):
            lines.append(f"\n{i}. {result.to_text()}")
        
        return "\n".join(lines)


class BaseSearchProvider(ABC):
    """Base class for search providers."""
    
    def __init__(self, api_keys: List[str], name: str):
        """
        Initialize the search provider.

        Args:
            api_keys: API key list. Multiple keys are used for load balancing.
            name: Search provider name.
        """
        self._api_keys = api_keys
        self._name = name
        self._key_cycle = cycle(api_keys) if api_keys else None
        self._key_usage: Dict[str, int] = {key: 0 for key in api_keys}
        self._key_errors: Dict[str, int] = {key: 0 for key in api_keys}
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_available(self) -> bool:
        """Return whether any API key is available."""
        return bool(self._api_keys)
    
    def _get_next_key(self) -> Optional[str]:
        """
        Get the next usable API key.

        Strategy: round-robin with skip for keys that have too many errors.
        """
        if not self._key_cycle:
            return None
        
        # Try each key at most once.
        for _ in range(len(self._api_keys)):
            key = next(self._key_cycle)
            # Skip keys with too many recent errors.
            if self._key_errors.get(key, 0) < 3:
                return key
        
        # Reset error counters if every key has recent failures.
        logger.warning(f"[{self._name}] All API keys have errors; resetting error counters")
        self._key_errors = {key: 0 for key in self._api_keys}
        return self._api_keys[0] if self._api_keys else None
    
    def _record_success(self, key: str) -> None:
        """Record successful key use."""
        self._key_usage[key] = self._key_usage.get(key, 0) + 1
        # Reduce the error counter after a successful request.
        if key in self._key_errors and self._key_errors[key] > 0:
            self._key_errors[key] -= 1
    
    def _record_error(self, key: str) -> None:
        """Record a key error."""
        self._key_errors[key] = self._key_errors.get(key, 0) + 1
        logger.warning(f"[{self._name}] API key {key[:8]}... error count: {self._key_errors[key]}")
    
    @abstractmethod
    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """Execute a provider-specific search."""
        pass
    
    def search(self, query: str, max_results: int = 5, days: int = 7) -> SearchResponse:
        """
        Execute a search.

        Args:
            query: Search query.
            max_results: Maximum result count.
            days: Freshness window in days.

        Returns:
            SearchResponse object.
        """
        api_key = self._get_next_key()
        if not api_key:
            return SearchResponse(
                query=query,
                results=[],
                provider=self._name,
                success=False,
                error_message=f"{self._name} API Key가 설정되지 않았습니다."
            )
        
        start_time = time.time()
        try:
            response = self._do_search(query, api_key, max_results, days=days)
            response.search_time = time.time() - start_time
            
            if response.success:
                self._record_success(api_key)
                logger.info(
                    f"[{self._name}] Search '{query}' succeeded, "
                    f"results={len(response.results)}, elapsed={response.search_time:.2f}s"
                )
            else:
                self._record_error(api_key)
            
            return response
            
        except Exception as e:
            self._record_error(api_key)
            elapsed = time.time() - start_time
            logger.error(f"[{self._name}] Search '{query}' failed: {e}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self._name,
                success=False,
                error_message=str(e),
                search_time=elapsed
            )


class TavilySearchProvider(BaseSearchProvider):
    """
    Tavily search provider.

    Features:
    - Search API optimized for AI/LLM workflows.
    - Free tier includes a limited monthly request quota.
    - Returns structured search results.

    Docs: https://docs.tavily.com/
    """
    
    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Tavily")
    
    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """Execute a Tavily search."""
        try:
            from tavily import TavilyClient
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="tavily-python이 설치되어 있지 않습니다. 실행: pip install tavily-python"
            )
        
        try:
            client = TavilyClient(api_key=api_key)
            
            # Execute the search with advanced depth and a recent time window.
            response = client.search(
                query=query,
                search_depth="advanced",  # Request richer results.
                max_results=max_results,
                include_answer=False,
                include_raw_content=False,
                days=days,  # Restrict results to the recent freshness window.
            )
            
            # Log the raw provider response at debug level only.
            logger.info(f"[Tavily] Search completed, query='{query}', results={len(response.get('results', []))}")
            logger.debug(f"[Tavily] Raw response: {response}")

            # Parse results.
            results = []
            for item in response.get('results', []):
                results.append(SearchResult(
                    title=item.get('title', ''),
                    snippet=item.get('content', '')[:500],
                    url=item.get('url', ''),
                    source=self._extract_domain(item.get('url', '')),
                    published_date=item.get('published_date'),
                ))
            
            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
            
        except Exception as e:
            error_msg = str(e)
            # Normalize quota errors into a Korean user-facing message.
            if 'rate limit' in error_msg.lower() or 'quota' in error_msg.lower():
                error_msg = f"API 할당량을 모두 사용했습니다: {error_msg}"
            
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract a domain name from a URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or 'Unknown source'
        except Exception:
            return 'Unknown source'


class SerpAPISearchProvider(BaseSearchProvider):
    """
    SerpAPI search provider.

    Features:
    - Supports Google and other search engines.
    - Free tier includes a limited monthly request quota.
    - Returns live search results.

    Docs: https://serpapi.com/
    """
    
    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "SerpAPI")
    
    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """Execute a SerpAPI search."""
        try:
            from serpapi import GoogleSearch
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=(
                    "google-search-results가 설치되어 있지 않습니다. "
                    "실행: pip install google-search-results"
                )
            )
        
        try:
            # Determine the tbs freshness parameter.
            tbs = "qdr:w"  # Default to one week.
            if days <= 1:
                tbs = "qdr:d"  # Past 24 hours.
            elif days <= 7:
                tbs = "qdr:w"  # Past week.
            elif days <= 30:
                tbs = "qdr:m"  # Past month.
            else:
                tbs = "qdr:y"  # Past year.

            # Use Google search for Knowledge Graph, Answer Box, and organic results.
            params = {
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "google_domain": "google.com",
                "hl": "en",
                "gl": "us",
                "tbs": tbs,
                "num": max_results,
            }
            
            search = GoogleSearch(params)
            response = search.get_dict()
            
            logger.debug(f"[SerpAPI] Raw response keys: {response.keys()}")

            # Parse results.
            results = []
            
            # 1. Parse Knowledge Graph.
            kg = response.get('knowledge_graph', {})
            if kg:
                title = kg.get('title', 'Knowledge Graph')
                desc = kg.get('description', '')
                
                # Extract extra attributes.
                details = []
                for key in ['type', 'founded', 'headquarters', 'employees', 'ceo']:
                    val = kg.get(key)
                    if val:
                        details.append(f"{key}: {val}")
                        
                snippet = f"{desc}\n" + " | ".join(details) if details else desc
                
                results.append(SearchResult(
                    title=f"[Knowledge Graph] {title}",
                    snippet=snippet,
                    url=kg.get('source', {}).get('link', ''),
                    source="Google Knowledge Graph"
                ))
                
            # 2. Parse Answer Box.
            ab = response.get('answer_box', {})
            if ab:
                ab_title = ab.get('title', 'Answer Box')
                ab_snippet = ""
                
                # Financial answer.
                if ab.get('type') == 'finance_results':
                    stock = ab.get('stock', '')
                    price = ab.get('price', '')
                    currency = ab.get('currency', '')
                    movement = ab.get('price_movement', {})
                    mv_val = movement.get('percentage', 0)
                    mv_dir = movement.get('movement', '')
                    
                    ab_title = f"[Quote Card] {stock}"
                    ab_snippet = f"Price: {price} {currency}\nMove: {mv_dir} {mv_val}%"
                    
                    # Extract table data.
                    if 'table' in ab:
                        table_data = []
                        for row in ab['table']:
                            if 'name' in row and 'value' in row:
                                table_data.append(f"{row['name']}: {row['value']}")
                        if table_data:
                            ab_snippet += "\n" + "; ".join(table_data)
                            
                # Plain-text answer.
                elif 'snippet' in ab:
                    ab_snippet = ab.get('snippet', '')
                    list_items = ab.get('list', [])
                    if list_items:
                        ab_snippet += "\n" + "\n".join([f"- {item}" for item in list_items])
                
                elif 'answer' in ab:
                    ab_snippet = ab.get('answer', '')
                    
                if ab_snippet:
                    results.append(SearchResult(
                        title=f"[Answer Box] {ab_title}",
                        snippet=ab_snippet,
                        url=ab.get('link', '') or ab.get('displayed_link', ''),
                        source="Google Answer Box"
                    ))

            # 3. Parse Related Questions.
            rqs = response.get('related_questions', [])
            for rq in rqs[:3]:
                question = rq.get('question', '')
                snippet = rq.get('snippet', '')
                link = rq.get('link', '')
                
                if question and snippet:
                     results.append(SearchResult(
                        title=f"[Related Question] {question}",
                        snippet=snippet,
                        url=link,
                        source="Google Related Questions"
                     ))

            # 4. Parse organic results.
            organic_results = response.get('organic_results', [])

            for item in organic_results[:max_results]:
                link = item.get('link', '')
                snippet = item.get('snippet', '')

                # Enrich snippets with fetched page text when available, capped for performance.
                content = ""
                if link:
                   try:
                       fetched_content = fetch_url_content(link, timeout=5)
                       if fetched_content:
                           content = fetched_content
                           if len(content) > 500:
                               snippet = f"{snippet}\n\n[페이지 상세]\n{content[:500]}..."
                           else:
                               snippet = f"{snippet}\n\n[페이지 상세]\n{content}"
                   except Exception as e:
                       logger.debug(f"[SerpAPI] Fetch content failed: {e}")

                results.append(SearchResult(
                    title=item.get('title', ''),
                    snippet=snippet[:1000],
                    url=link,
                    source=item.get('source', self._extract_domain(link)),
                    published_date=item.get('date'),
                ))

            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
            
        except Exception as e:
            error_msg = str(e)
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract a domain name from a URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace('www.', '') or 'Unknown source'
        except Exception:
            return 'Unknown source'


class NaverSearchProvider(BaseSearchProvider):
    """Naver Search provider for Korean market research."""

    API_ENDPOINT = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Naver")

    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """Execute a Naver news search."""
        client_id, client_secret = self._split_key(api_key)
        if not client_id or not client_secret:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="Invalid Naver API key format. Use client_id:client_secret.",
            )

        try:
            response = requests.get(
                self.API_ENDPOINT,
                headers={
                    "X-Naver-Client-Id": client_id,
                    "X-Naver-Client-Secret": client_secret,
                },
                params={
                    "query": query,
                    "display": min(max_results, 100),
                    "sort": "date",
                },
                timeout=10,
            )

            if response.status_code != 200:
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=f"HTTP {response.status_code}: {response.text[:200]}",
                )

            data = response.json()
            results = []
            for item in data.get("items", [])[:max_results]:
                results.append(
                    SearchResult(
                        title=self._strip_html(item.get("title", "")),
                        snippet=self._strip_html(item.get("description", ""))[:500],
                        url=item.get("originallink") or item.get("link", ""),
                        source=self._extract_domain(item.get("originallink") or item.get("link", "")),
                        published_date=item.get("pubDate"),
                    )
                )

            logger.info(f"[Naver] Search completed, query='{query}', results={len(results)}")
            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
        except requests.exceptions.Timeout:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="Request timed out",
            )
        except requests.exceptions.RequestException as e:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=f"Network request failed: {str(e)}",
            )
        except ValueError as e:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=f"JSON parsing failed: {str(e)}",
            )

    @staticmethod
    def _split_key(api_key: str) -> Tuple[str, str]:
        """Split a Naver key value in client_id:client_secret format."""
        if ":" not in api_key:
            return "", ""
        client_id, client_secret = api_key.split(":", 1)
        return client_id.strip(), client_secret.strip()

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove simple HTML tags that Naver includes in snippets."""
        import re
        return re.sub(r"<[^>]+>", "", text or "")

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract a domain from a URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or 'Unknown source'
        except Exception:
            return 'Unknown source'


class BraveSearchProvider(BaseSearchProvider):
    """
    Brave Search provider.

    Features:
    - Privacy-first independent search engine.
    - Large web index.
    - Free tier available.
    - Supports freshness filtering.

    Docs: https://brave.com/search/api/
    """

    API_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Brave")

    def _do_search(self, query: str, api_key: str, max_results: int, days: int = 7) -> SearchResponse:
        """Execute a Brave Search query."""
        try:
            # Request headers.
            headers = {
                'X-Subscription-Token': api_key,
                'Accept': 'application/json'
            }

            # Determine the freshness parameter.
            if days <= 1:
                freshness = "pd"  # Past day.
            elif days <= 7:
                freshness = "pw"  # Past week
            elif days <= 30:
                freshness = "pm"  # Past month
            else:
                freshness = "py"  # Past year

            params = {
                "q": query,
                "count": min(max_results, 20),
                "freshness": freshness,
                "search_lang": "en",
                "country": "US",
                "safesearch": "moderate"
            }

            response = requests.get(
                self.API_ENDPOINT,
                headers=headers,
                params=params,
                timeout=10
            )

            # Check HTTP status code.
            if response.status_code != 200:
                error_msg = self._parse_error(response)
                logger.warning(f"[Brave] Search failed: {error_msg}")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )

            # Parse response.
            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"응답 JSON 파싱에 실패했습니다: {str(e)}"
                logger.error(f"[Brave] {error_msg}")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )

            logger.info(f"[Brave] Search completed, query='{query}'")
            logger.debug(f"[Brave] Raw response: {data}")

            # Parse search results.
            results = []
            web_data = data.get('web', {})
            web_results = web_data.get('results', [])

            for item in web_results[:max_results]:
                # Parse published date in ISO 8601 format.
                published_date = None
                age = item.get('age') or item.get('page_age')
                if age:
                    try:
                        # Convert ISO format to a simple date string.
                        dt = datetime.fromisoformat(age.replace('Z', '+00:00'))
                        published_date = dt.strftime('%Y-%m-%d')
                    except (ValueError, AttributeError):
                        published_date = age  # Keep original value on parse failure.

                results.append(SearchResult(
                    title=item.get('title', ''),
                    snippet=item.get('description', '')[:500],
                    url=item.get('url', ''),
                    source=self._extract_domain(item.get('url', '')),
                    published_date=published_date
                ))

            logger.info(f"[Brave] Parsed {len(results)} result(s)")

            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True
            )

        except requests.exceptions.Timeout:
            error_msg = "요청 시간이 초과되었습니다."
            logger.error(f"[Brave] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except requests.exceptions.RequestException as e:
            error_msg = f"네트워크 요청에 실패했습니다: {str(e)}"
            logger.error(f"[Brave] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"알 수 없는 오류: {str(e)}"
            logger.error(f"[Brave] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )

    def _parse_error(self, response) -> str:
        """Parse an error response."""
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                error_data = response.json()
                # Brave API error format.
                if 'message' in error_data:
                    return error_data['message']
                if 'error' in error_data:
                    return error_data['error']
                return str(error_data)
            return response.text[:200]
        except Exception:
            return f"HTTP {response.status_code}: {response.text[:200]}"

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract a domain name from a URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or 'Unknown source'
        except Exception:
            return 'Unknown source'


class SearchService:
    """
    Search service.

    Features:
    1. Manage multiple search engines.
    2. Route KR research to Naver when configured.
    3. Route US/global research to global search providers.
    4. Aggregate and format search results.
    5. Provide enhanced fallback searches when quote data sources fail.
    """

    # Enhanced Korean market search keyword templates.
    ENHANCED_SEARCH_KEYWORDS = [
        "{name} 주가 오늘",
        "{name} {code} 최신 시세 추세",
        "{name} 주식 분석 차트",
        "{name} 기술적 분석",
        "{name} {code} 등락 거래량",
    ]

    # Enhanced US/global market search keyword templates.
    ENHANCED_SEARCH_KEYWORDS_EN = [
        "{name} stock price today",
        "{name} {code} latest quote trend",
        "{name} stock analysis chart",
        "{name} technical analysis",
        "{name} {code} performance volume",
    ]
    
    def __init__(
        self,
        naver_keys: Optional[List[str]] = None,
        tavily_keys: Optional[List[str]] = None,
        brave_keys: Optional[List[str]] = None,
        serpapi_keys: Optional[List[str]] = None,
        news_max_age_days: int = 3,
    ):
        """
        Initialize search service.

        Args:
            naver_keys: Naver API key pairs in client_id:client_secret format.
            tavily_keys: Tavily API key list.
            brave_keys: Brave Search API key list.
            serpapi_keys: SerpAPI key list.
            news_max_age_days: Maximum news freshness window in days.
        """
        self._providers: List[BaseSearchProvider] = []
        self.news_max_age_days = max(1, news_max_age_days)

        # Search engines are ordered by routing preference.
        if naver_keys:
            self._providers.append(NaverSearchProvider(naver_keys))
            logger.info(f"Configured Naver search with {len(naver_keys)} API key pair(s)")

        if tavily_keys:
            self._providers.append(TavilySearchProvider(tavily_keys))
            logger.info(f"Configured Tavily search with {len(tavily_keys)} API key(s)")

        if brave_keys:
            self._providers.append(BraveSearchProvider(brave_keys))
            logger.info(f"Configured Brave Search with {len(brave_keys)} API key(s)")

        if serpapi_keys:
            self._providers.append(SerpAPISearchProvider(serpapi_keys))
            logger.info(f"Configured SerpAPI search with {len(serpapi_keys)} API key(s)")
        
        if not self._providers:
            logger.warning("No search provider API keys configured; news search will be unavailable")

        # In-memory search result cache: {cache_key: (timestamp, SearchResponse)}
        self._cache: Dict[str, Tuple[float, 'SearchResponse']] = {}
        # Default cache TTL in seconds (10 minutes)
        self._cache_ttl: int = 600
    
    @staticmethod
    def _is_foreign_stock(stock_code: str) -> bool:
        """Return True for US/global symbols."""
        import re
        code = stock_code.strip()
        if code.upper() in {"KOSPI", "KOSDAQ"}:
            return False
        if re.match(r'^[A-Za-z]{1,5}(\.[A-Za-z])?$', code):
            return True
        return False

    _ETF_NAME_KEYWORDS = ('ETF', 'ETN', 'FUND', 'TRUST', 'INDEX', 'TRACKER', 'UNIT', 'KODEX', 'TIGER')

    @staticmethod
    def is_index_or_etf(stock_code: str, stock_name: str) -> bool:
        """
        Judge if symbol is index-tracking ETF or market index.
        For such symbols, analysis focuses on index movement only, not issuer company risks.
        """
        code = (stock_code or '').strip().split('.')[0]
        if not code:
            return False
        if is_us_index_code(code):
            return True
        name_upper = (stock_name or '').upper()
        return any(kw in name_upper for kw in SearchService._ETF_NAME_KEYWORDS)

    def _providers_for_stock(self, stock_code: str) -> List[BaseSearchProvider]:
        """Return providers in the correct order for a KR or US/global symbol."""
        is_us_or_global = self._is_foreign_stock(stock_code)
        if is_us_or_global:
            return [provider for provider in self._providers if provider.name != "Naver"]

        naver_providers = [provider for provider in self._providers if provider.name == "Naver"]
        global_providers = [provider for provider in self._providers if provider.name != "Naver"]
        return naver_providers + global_providers

    @property
    def is_available(self) -> bool:
        """Return whether any search provider is available."""
        return any(p.is_available for p in self._providers)

    def _cache_key(self, query: str, max_results: int, days: int) -> str:
        """Build a cache key from query parameters."""
        return f"{query}|{max_results}|{days}"

    def _get_cached(self, key: str) -> Optional['SearchResponse']:
        """Return cached SearchResponse if still valid, else None."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, response = entry
        if time.time() - ts > self._cache_ttl:
            del self._cache[key]
            return None
        logger.debug(f"Search cache hit: {key[:60]}...")
        return response

    def _put_cache(self, key: str, response: 'SearchResponse') -> None:
        """Store a successful SearchResponse in cache."""
        # Hard cap: evict oldest entries when cache exceeds limit
        _MAX_CACHE_SIZE = 500
        if len(self._cache) >= _MAX_CACHE_SIZE:
            now = time.time()
            # First pass: remove expired entries
            expired = [k for k, (ts, _) in self._cache.items() if now - ts > self._cache_ttl]
            for k in expired:
                del self._cache[k]
            # Second pass: if still over limit, evict oldest entries (FIFO)
            if len(self._cache) >= _MAX_CACHE_SIZE:
                excess = len(self._cache) - _MAX_CACHE_SIZE + 1
                oldest = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])[:excess]
                for k in oldest:
                    del self._cache[k]
        self._cache[key] = (time.time(), response)
    
    def search_stock_news(
        self,
        stock_code: str,
        stock_name: str,
        max_results: int = 5,
        focus_keywords: Optional[List[str]] = None
    ) -> SearchResponse:
        """
        Search stock-related news.

        Args:
            stock_code: Stock code or symbol.
            stock_name: Stock name.
            max_results: Maximum number of results.
            focus_keywords: Optional priority keywords.

        Returns:
            SearchResponse object.
        """
        # Bound the search freshness by weekday and NEWS_MAX_AGE_DAYS.
        today_weekday = datetime.now().weekday()
        if today_weekday == 0:
            weekday_days = 3
        elif today_weekday >= 5:
            weekday_days = 2
        else:
            weekday_days = 1
        search_days = min(weekday_days, self.news_max_age_days)

        is_foreign = self._is_foreign_stock(stock_code)
        if focus_keywords:
            query = " ".join(focus_keywords)
        elif is_foreign:
            query = f"{stock_name} {stock_code} stock latest news"
        else:
            query = f"{stock_name} {stock_code} 주식 최신 뉴스"

        logger.info(f"Search stock news: {stock_name}({stock_code}), query='{query}', freshness={search_days}d")

        # Check cache first
        cache_key = self._cache_key(query, max_results, search_days)
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.info(f"Using cached search results: {stock_name}({stock_code})")
            return cached

        for provider in self._providers_for_stock(stock_code):
            if not provider.is_available:
                continue
            
            response = provider.search(query, max_results, days=search_days)
            
            if response.success and response.results:
                logger.info(f"{provider.name} search succeeded")
                self._put_cache(cache_key, response)
                return response
            else:
                logger.warning(f"{provider.name} search failed: {response.error_message}; trying next provider")

        # All providers failed.
        return SearchResponse(
            query=query,
            results=[],
            provider="None",
            success=False,
            error_message="사용 가능한 검색 엔진이 없거나 모든 검색이 실패했습니다."
        )
    
    def search_stock_events(
        self,
        stock_code: str,
        stock_name: str,
        event_types: Optional[List[str]] = None
    ) -> SearchResponse:
        """Search stock-specific events that can affect trading decisions."""
        if event_types is None:
            if self._is_foreign_stock(stock_code):
                event_types = ["earnings report", "insider selling", "quarterly results"]
            else:
                event_types = ["실적 발표", "공시", "수급 변화"]
        
        event_query = " OR ".join(event_types)
        query = f"{stock_name} ({event_query})"
        
        logger.info(f"Search stock events: {stock_name}({stock_code}) - {event_types}")
        
        for provider in self._providers_for_stock(stock_code):
            if not provider.is_available:
                continue
            
            response = provider.search(query, max_results=5)
            
            if response.success:
                return response
        
        return SearchResponse(
            query=query,
            results=[],
            provider="None",
            success=False,
            error_message="이벤트 검색에 실패했습니다."
        )
    
    def search_comprehensive_intel(
        self,
        stock_code: str,
        stock_name: str,
        max_searches: int = 3
    ) -> Dict[str, SearchResponse]:
        """
        Run multi-dimensional stock intelligence search.

        Args:
            stock_code: Stock code or symbol.
            stock_name: Stock name.
            max_searches: Maximum number of search dimensions to run.

        Returns:
            Mapping from dimension name to SearchResponse.
        """
        results = {}
        search_count = 0

        is_foreign = self._is_foreign_stock(stock_code)
        is_index_etf = self.is_index_or_etf(stock_code, stock_name)

        if is_foreign:
            search_dimensions = [
                {
                    'name': 'latest_news',
                    'query': f"{stock_name} {stock_code} latest news events",
                    'desc': '최신 뉴스',
                },
                {
                    'name': 'market_analysis',
                    'query': f"{stock_name} analyst rating target price report",
                    'desc': '기관 분석',
                },
                {
                    'name': 'risk_check',
                    'query': (
                        f"{stock_name} {stock_code} index performance outlook tracking error"
                        if is_index_etf else f"{stock_name} risk insider selling lawsuit litigation"
                    ),
                    'desc': '리스크 점검',
                },
                {
                    'name': 'earnings',
                    'query': (
                        f"{stock_name} {stock_code} index performance composition outlook"
                        if is_index_etf else f"{stock_name} earnings revenue profit growth forecast"
                    ),
                    'desc': '실적 전망',
                },
                {
                    'name': 'industry',
                    'query': (
                        f"{stock_name} {stock_code} index sector allocation holdings"
                        if is_index_etf else f"{stock_name} industry competitors market share outlook"
                    ),
                    'desc': '산업 분석',
                },
            ]
        else:
            search_dimensions = [
                {
                    'name': 'latest_news',
                    'query': f"{stock_name} {stock_code} 최신 뉴스 주요 이슈",
                    'desc': '최신 뉴스',
                },
                {
                    'name': 'market_analysis',
                    'query': f"{stock_name} 증권사 리포트 목표주가 투자의견",
                    'desc': '기관 분석',
                },
                {
                    'name': 'risk_check',
                    'query': (
                        f"{stock_name} 지수 추적오차 순자산 성과"
                        if is_index_etf else f"{stock_name} 공시 소송 리스크 악재"
                    ),
                    'desc': '리스크 점검',
                },
                {
                    'name': 'earnings',
                    'query': (
                        f"{stock_name} 지수 구성 순자산 추적 성과"
                        if is_index_etf else f"{stock_name} 실적 발표 매출 영업이익 전망"
                    ),
                    'desc': '실적 전망',
                },
                {
                    'name': 'industry',
                    'query': (
                        f"{stock_name} 지수 구성종목 업종 비중"
                        if is_index_etf else f"{stock_name} 업종 경쟁사 시장점유율 전망"
                    ),
                    'desc': '산업 분석',
                },
            ]
        
        logger.info(f"Starting multi-dimensional intelligence search: {stock_name}({stock_code})")
        
        provider_index = 0
        
        for dim in search_dimensions:
            if search_count >= max_searches:
                break
            
            available_providers = [p for p in self._providers_for_stock(stock_code) if p.is_available]
            if not available_providers:
                break
            
            provider = available_providers[provider_index % len(available_providers)]
            provider_index += 1
            
            logger.info(f"[Intel search] {dim['desc']}: using {provider.name}")
            
            response = provider.search(dim['query'], max_results=3, days=self.news_max_age_days)
            results[dim['name']] = response
            search_count += 1
            
            if response.success:
                logger.info(f"[Intel search] {dim['desc']}: fetched {len(response.results)} result(s)")
            else:
                logger.warning(f"[Intel search] {dim['desc']}: search failed - {response.error_message}")
            
            # Avoid sending requests too quickly across providers.
            time.sleep(0.5)
        
        return results
    
    def format_intel_report(self, intel_results: Dict[str, SearchResponse], stock_name: str) -> str:
        """
        Format intelligence search results into a report.

        Args:
            intel_results: Multi-dimensional search results.
            stock_name: Stock name.

        Returns:
            Formatted intelligence report text.
        """
        lines = [f"[{stock_name} 리서치 검색 결과]"]
        
        display_order = ['latest_news', 'market_analysis', 'risk_check', 'earnings', 'industry']
        
        for dim_name in display_order:
            if dim_name not in intel_results:
                continue
                
            resp = intel_results[dim_name]
            
            dim_desc = dim_name
            if dim_name == 'latest_news': dim_desc = '📰 최신 뉴스'
            elif dim_name == 'market_analysis': dim_desc = '📈 기관 분석'
            elif dim_name == 'risk_check': dim_desc = '⚠️ 리스크 점검'
            elif dim_name == 'earnings': dim_desc = '📊 실적 전망'
            elif dim_name == 'industry': dim_desc = '🏭 산업 분석'
            
            lines.append(f"\n{dim_desc} (출처: {resp.provider}):")
            if resp.success and resp.results:
                for i, r in enumerate(resp.results[:4], 1):
                    date_str = f" [{r.published_date}]" if r.published_date else ""
                    lines.append(f"  {i}. {r.title}{date_str}")
                    snippet = r.snippet[:150] if len(r.snippet) > 20 else r.snippet
                    lines.append(f"     {snippet}...")
            else:
                lines.append("  관련 정보를 찾지 못했습니다")
        
        return "\n".join(lines)
    
    def batch_search(
        self,
        stocks: List[Dict[str, str]],
        max_results_per_stock: int = 3,
        delay_between: float = 1.0
    ) -> Dict[str, SearchResponse]:
        """
        Batch search news for multiple stocks.
        
        Args:
            stocks: List of stocks
            max_results_per_stock: Max results per stock
            delay_between: Delay between searches (seconds)
            
        Returns:
            Dict of results
        """
        results = {}
        
        for i, stock in enumerate(stocks):
            if i > 0:
                time.sleep(delay_between)
            
            code = stock.get('code', '')
            name = stock.get('name', '')
            
            response = self.search_stock_news(code, name, max_results_per_stock)
            results[code] = response
        
        return results

    def search_stock_price_fallback(
        self,
        stock_code: str,
        stock_name: str,
        max_attempts: int = 3,
        max_results: int = 5
    ) -> SearchResponse:
        """
        Enhance search when data sources fail.
        
        When configured market data sources fail to get stock data, use search engines to
        find stock trends and price info as supplemental data for AI analysis.
        
        Strategy:
        1. Search using multiple keyword templates
        2. Try all available search engines for each keyword
        3. Aggregate and deduplicate results
        
        Args:
            stock_code: Stock Code
            stock_name: Stock Name
            max_attempts: Max search attempts (using different keywords)
            max_results: Max results to return
            
        Returns:
            SearchResponse object with aggregated results
        """

        if not self.is_available:
            return SearchResponse(
                query=f"{stock_name} price trend",
                results=[],
                provider="None",
                success=False,
                error_message="검색 엔진 API Key가 설정되지 않았습니다."
            )

        logger.info(f"[Enhanced search] Data source failed; starting enhanced search: {stock_name}({stock_code})")
        
        all_results = []
        seen_urls = set()
        successful_providers = []
        
        is_foreign = self._is_foreign_stock(stock_code)
        keywords = self.ENHANCED_SEARCH_KEYWORDS_EN if is_foreign else self.ENHANCED_SEARCH_KEYWORDS
        for i, keyword_template in enumerate(keywords[:max_attempts]):
            query = keyword_template.format(name=stock_name, code=stock_code)
            
            logger.info(f"[Enhanced search] Attempt {i+1}/{max_attempts}: {query}")
            
            for provider in self._providers_for_stock(stock_code):
                if not provider.is_available:
                    continue
                
                try:
                    response = provider.search(query, max_results=3)
                    
                    if response.success and response.results:
                        for result in response.results:
                            if result.url not in seen_urls:
                                seen_urls.add(result.url)
                                all_results.append(result)
                                
                        if provider.name not in successful_providers:
                            successful_providers.append(provider.name)
                        
                        logger.info(f"[Enhanced search] {provider.name} returned {len(response.results)} result(s)")
                        break
                    else:
                        logger.debug(f"[Enhanced search] {provider.name} returned no results or failed")
                        
                except Exception as e:
                    logger.warning(f"[Enhanced search] {provider.name} search exception: {e}")
                    continue
            
            if i < max_attempts - 1:
                time.sleep(0.5)
        
        if all_results:
            final_results = all_results[:max_results]
            provider_str = ", ".join(successful_providers) if successful_providers else "None"
            
            logger.info(f"[Enhanced search] Completed with {len(final_results)} result(s), providers={provider_str}")
            
            return SearchResponse(
                query=f"{stock_name}({stock_code}) price trend",
                results=final_results,
                provider=provider_str,
                success=True,
            )
        else:
            logger.warning("[Enhanced search] No search attempts returned results")
            return SearchResponse(
                query=f"{stock_name}({stock_code}) price trend",
                results=[],
                provider="None",
                success=False,
                error_message="보강 검색에서 관련 정보를 찾지 못했습니다."
            )

    def search_stock_with_enhanced_fallback(
        self,
        stock_code: str,
        stock_name: str,
        include_news: bool = True,
        include_price: bool = False,
        max_results: int = 5
    ) -> Dict[str, SearchResponse]:
        """
        Search news and optional price trend context.

        This is mainly used as a fallback when quote data sources are unavailable.

        Args:
            stock_code: Stock code or symbol.
            stock_name: Stock name.
            include_news: Whether to search news.
            include_price: Whether to search price trend information.
            max_results: Maximum results for each search type.

        Returns:
            Mapping containing news and optional price SearchResponse values.
        """
        results = {}
        
        if include_news:
            results['news'] = self.search_stock_news(
                stock_code, 
                stock_name, 
                max_results=max_results
            )
        
        if include_price:
            results['price'] = self.search_stock_price_fallback(
                stock_code,
                stock_name,
                max_attempts=3,
                max_results=max_results
            )
        
        return results

    def format_price_search_context(self, response: SearchResponse) -> str:
        """
        Format price search results as AI analysis context.

        Args:
            response: Search response object.

        Returns:
            Formatted context text.
        """
        if not response.success or not response.results:
            return (
                "[주가 추세 검색] 관련 정보를 찾지 못했습니다. "
                "다른 데이터 채널을 기준으로 판단하세요."
            )
        
        lines = [
            f"[주가 추세 검색 결과](출처: {response.provider})",
            "⚠️ 참고: 아래 정보는 웹 검색 기반이며 지연되거나 부정확할 수 있습니다.",
            ""
        ]
        
        for i, result in enumerate(response.results, 1):
            date_str = f" [{result.published_date}]" if result.published_date else ""
            lines.append(f"{i}. [{result.source}] {result.title}{date_str}")
            lines.append(f"   {result.snippet[:200]}...")
            lines.append("")
        
        return "\n".join(lines)


# Convenience singleton helpers.
_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    """Return the SearchService singleton."""
    global _search_service
    
    if _search_service is None:
        from src.config import get_config
        config = get_config()
        
        _search_service = SearchService(
            naver_keys=config.naver_api_keys,
            tavily_keys=config.tavily_api_keys,
            brave_keys=config.brave_api_keys,
            serpapi_keys=config.serpapi_keys,
            news_max_age_days=config.news_max_age_days,
        )
    
    return _search_service


def reset_search_service() -> None:
    """Reset the SearchService singleton for tests."""
    global _search_service
    _search_service = None


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
    )
    
    service = get_search_service()
    
    if service.is_available:
        print("=== Search stock news ===")
        response = service.search_stock_news("005930", "삼성전자")
        print(f"검색 상태: {'성공' if response.success else '실패'}")
        print(f"검색 엔진: {response.provider}")
        print(f"결과 수: {len(response.results)}")
        print(f"소요 시간: {response.search_time:.2f}s")
        print("\n" + response.to_context())
    else:
        print("검색 엔진 API Key가 설정되지 않아 테스트를 건너뜁니다.")
