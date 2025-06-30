"""Web scraping service for fetching recipe web pages."""

import json
import logging
import time
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from ..settings import settings
    from ..utils.observability import trace_function, obs_manager
except ImportError:
    # Direct import when running as script
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from settings import settings
    from utils.observability import trace_function, obs_manager

logger = logging.getLogger(__name__)


class WebScraperService:
    """Service for fetching and parsing web page content."""
    
    # User agents for rotation to be polite
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0'
    ]
    
    def __init__(self):
        """Initialize the web scraper service."""
        self.session = None
        self.last_request_time = 0
        self.current_user_agent_index = 0
        
        # Initialize session
        self._initialize_session()
        
        logger.info(f"WebScraperService initialized with {settings.WEB_SCRAPER_DELAY}s rate limit")
    
    def _initialize_session(self) -> None:
        """Initialize the requests session with proper configuration."""
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self._update_headers()
        
        logger.debug("Requests session initialized with retry strategy")
    
    def _update_headers(self) -> None:
        """Update session headers with rotated user agent."""
        user_agent = self.USER_AGENTS[self.current_user_agent_index]
        
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
        
        # Rotate user agent for next request
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.USER_AGENTS)
    
    def _validate_url(self, url: str) -> bool:
        """Validate if the URL is properly formatted and safe."""
        try:
            parsed = urlparse(url)
            
            # Check basic URL structure
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Only allow HTTP and HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Avoid local/private IPs for security
            if any(private in parsed.netloc.lower() for private in ['localhost', '127.0.0.1', '0.0.0.0']):
                logger.warning(f"Rejected local URL for security: {url}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False
    
    def _rate_limit(self) -> None:
        """Implement rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < settings.WEB_SCRAPER_DELAY:
            sleep_time = settings.WEB_SCRAPER_DELAY - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    @trace_function("web_scraper_fetch")
    def fetch_page_content(self, url: str) -> Dict[str, Any]:
        """
        Fetch and parse content from a web page.
        
        Args:
            url: The URL to fetch content from
            
        Returns:
            Dictionary containing parsed content and metadata
        """
        if not self._validate_url(url):
            raise ValueError(f"Invalid or unsafe URL: {url}")
        
        # Apply rate limiting
        self._rate_limit()
        
        # Update headers for this request
        self._update_headers()
        
        try:
            logger.info(f"Fetching content from: {url}")
            start_time = time.time()
            
            # Make the request with timeout
            response = self.session.get(
                url,
                timeout=(10, 30),  # (connection_timeout, read_timeout)
                allow_redirects=True,
                stream=False
            )
            
            response_time = time.time() - start_time
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                logger.warning(f"Non-HTML content type: {content_type}")
            
            # Parse the content
            result = self._parse_html_content(response, url)
            result['response_time'] = response_time
            result['final_url'] = response.url  # After redirects
            
            logger.info(f"Successfully fetched content from {url} in {response_time:.2f}s")
            
            # Record metrics
            obs_manager.record_metric("web_scraper_request", 1.0, {
                "success": "true",
                "status_code": str(response.status_code)
            })
            obs_manager.record_metric("web_scraper_response_time", response_time, {
                "domain": urlparse(url).netloc
            })
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching URL: {url}")
            obs_manager.record_metric("web_scraper_request", 1.0, {
                "success": "false",
                "error": "timeout"
            })
            raise RuntimeError("Request timeout - the website took too long to respond")
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while fetching URL {url}: {e}")
            obs_manager.record_metric("web_scraper_request", 1.0, {
                "success": "false",
                "error": "connection"
            })
            raise RuntimeError("Connection error - unable to reach the website")
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            logger.error(f"HTTP error {status_code} while fetching URL: {url}")
            obs_manager.record_metric("web_scraper_request", 1.0, {
                "success": "false",
                "error": f"http_{status_code}"
            })
            
            if status_code == 404:
                raise RuntimeError("Page not found (404)")
            elif status_code == 403:
                raise RuntimeError("Access forbidden (403) - website may be blocking automated requests")
            elif status_code == 429:
                raise RuntimeError("Rate limited (429) - too many requests")
            else:
                raise RuntimeError(f"HTTP error {status_code}")
                
        except Exception as e:
            logger.error(f"Unexpected error while fetching URL {url}: {e}")
            obs_manager.record_metric("web_scraper_request", 1.0, {
                "success": "false",
                "error": "unknown"
            })
            raise RuntimeError(f"Failed to fetch page content: {str(e)}")
    
    def _parse_html_content(self, response: requests.Response, original_url: str) -> Dict[str, Any]:
        """Parse HTML content and extract relevant information."""
        try:
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic content
            result = {
                "url": original_url,
                "final_url": response.url,
                "status_code": response.status_code,
                "title": self._extract_title(soup),
                "content": self._extract_main_content(soup),
                "meta_description": self._extract_meta_description(soup),
                "structured_data": self._extract_structured_data(soup),
                "recipe_indicators": self._detect_recipe_indicators(soup),
                "links": self._extract_links(soup, response.url),
                "images": self._extract_images(soup, response.url),
                "content_length": len(response.content),
                "encoding": response.encoding
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing HTML content: {e}")
            raise RuntimeError(f"Failed to parse HTML content: {str(e)}")
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try title tag first
        title_tag = soup.find('title')
        if title_tag and title_tag.get_text().strip():
            return title_tag.get_text().strip()
        
        # Try Open Graph title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title.get('content').strip()
        
        # Try h1 as fallback
        h1_tag = soup.find('h1')
        if h1_tag and h1_tag.get_text().strip():
            return h1_tag.get_text().strip()
        
        return "Untitled Page"
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main text content from the page."""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form']):
            element.decompose()
        
        # Try to find main content areas (in order of preference)
        content_selectors = [
            'article',
            '[role="main"]',
            'main',
            '.content',
            '.main-content',
            '.post-content',
            '.entry-content',
            '.recipe',
            '.recipe-content',
            '.recipe-card',
            '#content',
            '#main-content'
        ]
        
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                text = content_element.get_text(separator=' ', strip=True)
                if len(text) > 100:  # Must have substantial content
                    logger.debug(f"Found main content using selector: {selector}")
                    return self._clean_text(text)
        
        # Fallback to body content
        body = soup.find('body')
        if body:
            text = body.get_text(separator=' ', strip=True)
            return self._clean_text(text)
        
        # Last resort - all text
        return self._clean_text(soup.get_text(separator=' ', strip=True))
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        return text.strip()
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract meta description."""
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc.get('content').strip()
        
        # Try Open Graph description
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            return og_desc.get('content').strip()
        
        return None
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract structured data (JSON-LD, microdata) from the page."""
        structured_data = {}
        
        # Extract JSON-LD data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        json_ld_data = []
        
        for script in json_ld_scripts:
            try:
                if script.string:
                    data = json.loads(script.string)
                    json_ld_data.append(data)
                    logger.debug("Found JSON-LD structured data")
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse JSON-LD data: {e}")
        
        if json_ld_data:
            structured_data['json_ld'] = json_ld_data
        
        # Extract microdata
        microdata = self._extract_microdata(soup)
        if microdata:
            structured_data['microdata'] = microdata
        
        return structured_data
    
    def _extract_microdata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract microdata from the page."""
        microdata = {}
        
        # Find elements with itemtype
        items = soup.find_all(attrs={'itemtype': True})
        
        for item in items:
            item_type = item.get('itemtype')
            if item_type:
                # Extract recipe-related microdata
                if 'Recipe' in item_type:
                    microdata['has_recipe'] = True
                    microdata['recipe_type'] = item_type
                    
                    # Extract recipe properties
                    recipe_props = {}
                    for prop_elem in item.find_all(attrs={'itemprop': True}):
                        prop_name = prop_elem.get('itemprop')
                        prop_value = prop_elem.get_text(strip=True)
                        if prop_name and prop_value:
                            recipe_props[prop_name] = prop_value
                    
                    if recipe_props:
                        microdata['recipe_properties'] = recipe_props
        
        return microdata
    
    def _detect_recipe_indicators(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Detect various indicators that suggest this is a recipe page."""
        indicators = {
            'has_recipe_microdata': False,
            'has_recipe_json_ld': False,
            'has_ingredient_list': False,
            'has_instructions': False,
            'recipe_keywords': [],
            'confidence_score': 0.0
        }
        
        # Check for microdata
        if soup.find(attrs={'itemtype': lambda x: x and 'Recipe' in x}):
            indicators['has_recipe_microdata'] = True
            indicators['confidence_score'] += 0.3
        
        # Check for JSON-LD recipe data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                if script.string and 'Recipe' in script.string:
                    indicators['has_recipe_json_ld'] = True
                    indicators['confidence_score'] += 0.3
                    break
            except:
                pass
        
        # Check for ingredient-related elements
        ingredient_selectors = [
            '.ingredient', '.ingredients', '[class*="ingredient"]',
            '.recipe-ingredient', '.recipe-ingredients',
            'ul li', 'ol li'  # Common list patterns
        ]
        
        text_content = soup.get_text().lower()
        
        # Look for ingredient keywords
        ingredient_keywords = ['ingredients', 'cups', 'tbsp', 'tsp', 'ounces', 'grams', 'pounds']
        found_ingredients = [kw for kw in ingredient_keywords if kw in text_content]
        
        if found_ingredients or any(soup.select(sel) for sel in ingredient_selectors):
            indicators['has_ingredient_list'] = True
            indicators['confidence_score'] += 0.2
        
        # Check for instruction-related elements
        instruction_keywords = ['instructions', 'directions', 'method', 'steps', 'preparation']
        found_instructions = [kw for kw in instruction_keywords if kw in text_content]
        
        if found_instructions:
            indicators['has_instructions'] = True
            indicators['confidence_score'] += 0.2
        
        # Recipe-specific keywords
        recipe_keywords = ['recipe', 'cook', 'bake', 'prepare', 'serve', 'minutes', 'degrees']
        found_recipe_keywords = [kw for kw in recipe_keywords if kw in text_content]
        indicators['recipe_keywords'] = found_recipe_keywords
        
        if found_recipe_keywords:
            indicators['confidence_score'] += min(len(found_recipe_keywords) * 0.05, 0.2)
        
        # Normalize confidence score
        indicators['confidence_score'] = min(indicators['confidence_score'], 1.0)
        
        return indicators
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract relevant links from the page."""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            text = link.get_text(strip=True)
            
            if href and text:
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                
                links.append({
                    'url': absolute_url,
                    'text': text,
                    'title': link.get('title', '')
                })
        
        # Limit to first 50 links to avoid excessive data
        return links[:50]
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract image information from the page."""
        images = []
        
        for img in soup.find_all('img', src=True):
            src = img.get('src')
            alt = img.get('alt', '')
            
            if src:
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, src)
                
                images.append({
                    'src': absolute_url,
                    'alt': alt,
                    'title': img.get('title', '')
                })
        
        # Limit to first 20 images
        return images[:20]
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session."""
        return {
            'current_user_agent': self.session.headers.get('User-Agent', ''),
            'total_user_agents': len(self.USER_AGENTS),
            'rate_limit_delay': settings.WEB_SCRAPER_DELAY,
            'last_request_time': self.last_request_time
        }