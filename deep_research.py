#!/usr/bin/env python3
"""
MCP server that provides a unified research tool for web and academic searches,
follows relevant links, and returns comprehensive information to Claude.

This server integrates DuckDuckGo for web search and Semantic Scholar for academic content.
"""

import sys
import re
import logging
from urllib.parse import quote_plus, unquote
from contextlib import asynccontextmanager

# Set up logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("research-assistant")

# Try to import required dependencies
try:
    import httpx
    from bs4 import BeautifulSoup
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "beautifulsoup4", "mcp"])
    import httpx
    from bs4 import BeautifulSoup
    from mcp.server.fastmcp import FastMCP

# Initialize server with simple lifespan
@asynccontextmanager
async def lifespan(app: FastMCP):
    """Context manager for server lifecycle"""
    logger.info("Server starting up...")
    yield {}
    logger.info("Server shutting down...")

# Initialize the MCP server
mcp = FastMCP(
    "research-assistant",
    dependencies=["httpx", "beautifulsoup4"],
    lifespan=lifespan
)

# Configuration
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
MAX_CONTENT_SIZE = 8000  # Maximum characters in the final response
MAX_RESULTS = 3         # Maximum number of results to process

def safe_truncate(text, max_length, suffix="...\n[Content truncated due to size limits]"):
    """Safely truncate text to max_length with a suffix"""
    if not text or len(text) <= max_length:
        return text
    
    # Try to truncate at a paragraph boundary
    last_para_break = text[:max_length-50].rfind("\n\n")
    if last_para_break > max_length // 2:
        return text[:last_para_break] + "\n\n" + suffix
    
    return text[:max_length] + suffix

@mcp.tool()
async def deep_research(query: str, sources: str = "both", num_results: int = 2) -> str:
    """
    Perform comprehensive research on a topic and return detailed information.

    Args:
        query: The research question or topic
        sources: Which sources to use: "web" for general info, "academic" for scholarly sources, "both" for all sources
        num_results: Number of sources to examine (default 2, max 3)

    Returns:
        Comprehensive research results combining multiple sources
    """
    logger.info(f"Starting research on: {query}, sources: {sources}, num_results: {num_results}")
    
    # Validate inputs
    if num_results > MAX_RESULTS:
        num_results = MAX_RESULTS
        
    sources = sources.lower().strip()
    if sources not in ["web", "academic", "both"]:
        sources = "both"
    
    try:
        # Start with basic intro
        result = f"Research Query: {query}\n\n"
        source_text = "web and academic sources" if sources == "both" else sources + " sources"
        result += f"Searching {source_text}...\n\n"
        
        # Collect web results
        web_urls = []
        if sources in ["web", "both"]:
            try:
                web_results = await _web_search(query, num_results)
                result += "WEB SEARCH RESULTS:\n" + web_results + "\n\n"
                web_urls = re.findall(r"URL: (https?://[^\s]+)", web_results)
                web_urls = web_urls[:num_results]
            except Exception as e:
                logger.error(f"Web search error: {str(e)}")
                result += f"WEB SEARCH ERROR: {str(e)[:100]}\n\n"
        
        # Collect academic results
        academic_urls = []
        if sources in ["academic", "both"]:
            try:
                academic_results = await _academic_search(query, num_results)
                result += "ACADEMIC SEARCH RESULTS:\n" + academic_results + "\n\n"
                academic_urls = re.findall(r"URL: (https?://[^\s]+)", academic_results)
                academic_urls = academic_urls[:num_results]
            except Exception as e:
                logger.error(f"Academic search error: {str(e)}")
                result += f"ACADEMIC SEARCH ERROR: {str(e)[:100]}\n\n"
        
        # Check if we found anything
        if not web_urls and not academic_urls:
            return result + "No valid search results found. Please try a different query."
            
        # Combine URLs
        if sources == "both":
            combined_urls = []
            for i in range(max(len(web_urls), len(academic_urls))):
                if i < len(web_urls):
                    combined_urls.append(("web", web_urls[i]))
                if i < len(academic_urls):
                    combined_urls.append(("academic", academic_urls[i]))
            # Limit to the requested number
            combined_urls = combined_urls[:num_results]
        elif sources == "web":
            combined_urls = [("web", url) for url in web_urls[:num_results]]
        else:  # academic
            combined_urls = [("academic", url) for url in academic_urls[:num_results]]
        
        # Follow URLs to get detailed content
        result += f"DETAILED CONTENT FROM TOP {len(combined_urls)} SOURCES:\n\n"
        
        for i, (source_type, url) in enumerate(combined_urls, 1):
            try:
                # Get content
                page_content = await _follow_link(url)
                
                # Extract title
                title_match = re.search(r"Title: (.+?)\n", page_content)
                title = title_match.group(1) if title_match else f"Source {i}"
                
                # Add to result
                separator = "=" * 40
                result += f"{separator}\nSOURCE {i} ({source_type}): {title}\n{separator}\n\n"
                result += page_content + "\n\n"
            except Exception as e:
                logger.error(f"Error following URL {url}: {str(e)}")
                separator = "=" * 40
                result += f"{separator}\nSOURCE {i} ({source_type}): Error following URL\n{separator}\n"
                result += f"Error: {str(e)[:100]}\n\n"
        
        # Check size and add summary
        # Reserve space for summary
        summary = "\nRESEARCH SUMMARY:\n"
        summary += f"Completed research on: {query}\n"
        source_summary = "web and academic databases" if sources == "both" else sources + " sources"
        summary += f"Examined {len(combined_urls)} sources from {source_summary}\n"
        summary += "The information above represents the most relevant content found on this topic.\n"
        
        # Truncate if needed to ensure summary fits
        max_size = MAX_CONTENT_SIZE - len(summary) - 50
        if len(result) > max_size:
            result = safe_truncate(result, max_size)
        
        # Add summary and return
        result += summary
        logger.info(f"Research complete, returning {len(result)} characters")
        return result
        
    except Exception as e:
        logger.error(f"Error in deep_research: {str(e)}")
        return f"Research error: {str(e)[:200]}"

async def _web_search(query: str, num_results: int) -> str:
    """Perform a web search using DuckDuckGo"""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            # Create search URL
            encoded_query = quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            # Set headers
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml"
            }
            
            # Make request
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            # Parse results
            soup = BeautifulSoup(response.text, "html.parser")
            search_results = []
            
            # Extract results
            result_blocks = soup.select(".result")
            for block in result_blocks:
                if len(search_results) >= num_results:
                    break
                    
                # Get title and URL
                title_elem = block.select_one(".result__title a")
                if not title_elem:
                    continue
                    
                title = title_elem.get_text().strip()
                href = title_elem.get("href", "")
                
                # Extract actual URL from redirect
                if "duckduckgo.com" in href:
                    url_match = re.search(r"uddg=([^&]+)", href)
                    if url_match:
                        href = unquote(url_match.group(1))
                
                # Get snippet
                snippet_elem = block.select_one(".result__snippet")
                snippet = snippet_elem.get_text().strip() if snippet_elem else "No snippet available"
                
                # Add to results
                search_results.append({
                    "title": title[:100],
                    "url": href[:150],
                    "snippet": snippet[:200]
                })
            
            # Format results
            results_text = f"Web search results for: {query}\n\n"
            for i, result in enumerate(search_results, 1):
                results_text += f"{i}. {result['title']}\n"
                results_text += f"   URL: {result['url']}\n"
                results_text += f"   {result['snippet']}\n\n"
                
            return results_text if search_results else f"No web results found for: {query}"
                
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        raise  # Re-raise to handle in the main function

async def _academic_search(query: str, num_results: int) -> str:
    """Perform an academic search using Semantic Scholar"""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            # Create search URL
            encoded_query = quote_plus(query)
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={encoded_query}&limit={num_results}&fields=title,authors,year,venue,url,abstract"
            
            # Make request
            headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                return f"Academic search error: API returned status {response.status_code}"
                
            # Parse results
            json_data = response.json()
            results = json_data.get("data", [])
            
            if not results:
                return "No academic results found. Try refining your search."
                
            # Process results
            search_results = []
            for paper in results:
                title = paper.get("title", "Untitled Paper")
                
                # Get authors
                authors = paper.get("authors", [])
                author_names = [author.get("name", "") for author in authors if author.get("name")]
                author_names = author_names[:3]
                if len(authors) > 3:
                    author_names.append("et al.")
                author_text = ", ".join(author_names) if author_names else "Unknown authors"
                
                # Get publication info
                year = paper.get("year", "")
                venue = paper.get("venue", "")
                pub_info = f"{author_text} ({year})"
                if venue:
                    pub_info += f" - {venue}"
                    
                # Get URL and abstract
                url = paper.get("url", "")
                abstract = paper.get("abstract", "No abstract available")
                
                search_results.append({
                    "title": title[:100],
                    "url": url[:150],
                    "authors_info": pub_info[:150],
                    "snippet": abstract[:200]
                })
                
            # Format results
            results_text = f"Academic search results for: {query}\n\n"
            for i, result in enumerate(search_results, 1):
                results_text += f"{i}. {result['title']}\n"
                if result['url']:
                    results_text += f"   URL: {result['url']}\n"
                results_text += f"   {result['authors_info']}\n"
                results_text += f"   {result['snippet']}\n\n"
                
            return results_text
            
    except Exception as e:
        logger.error(f"Academic search error: {str(e)}")
        raise  # Re-raise to handle in the main function

async def _follow_link(url: str) -> str:
    """Visit a URL and extract its content"""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=8.0) as client:
            # Set headers
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml"
            }
            
            # Make request
            response = await client.get(url, headers=headers)
            
            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            if "application/pdf" in content_type:
                return f"Title: PDF Document\nURL: {url}\n\nContent: [PDF document - contents cannot be extracted directly]"
                
            # Parse HTML
            soup = BeautifulSoup(response.text[:100000], "html.parser")  # Limit size
            
            # Get title
            title = soup.title.string.strip() if soup.title and soup.title.string else "No title"
            
            # Get description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            description = meta_desc["content"] if meta_desc and meta_desc.has_attr("content") else "No description available"
            
            # Get content
            content_texts = []
            
            # Try to get paragraphs
            paragraphs = soup.find_all('p')
            for i, p in enumerate(paragraphs):
                if i >= 5:  # Limit to 5 paragraphs
                    break
                text = p.get_text().strip()
                if text and len(text) > 15:
                    content_texts.append(text[:300])
                    
            # If not enough paragraphs, try other elements
            if len(content_texts) < 2:
                elements = soup.find_all(['h1', 'h2', 'h3', 'p'])
                for i, elem in enumerate(elements):
                    if i >= 8:
                        break
                    text = elem.get_text().strip()
                    if text and len(text) > 10:
                        content_texts.append(text[:200])
                        
            # If still no content, use whatever text we can find
            if not content_texts:
                all_text = soup.get_text()
                clean_text = re.sub(r'\s+', ' ', all_text).strip()
                content_texts = [clean_text[:500]]
                
            # Format output
            content = "\n\n".join(content_texts)
            result = f"Title: {title[:100]}\nURL: {url}\nDescription: {description[:200]}\n\nContent:\n{content}"
            
            return result
            
    except Exception as e:
        logger.error(f"Error following link: {str(e)}")
        raise  # Re-raise to handle in the main function

@mcp.prompt()
def deep_research(topic: str) -> str:
    """
    Create a prompt for comprehensive, multi-stage research on a topic.

    Args:
        topic: The topic to research

    Returns:
        A prompt for comprehensive iterative research with APA citations
    """
    return (
        f"I need to do comprehensive research on: {topic}\n\n"
        f"Please follow this multi-step research process:\n\n"
        f"1. INITIAL EXPLORATION: Use the deep_research tool to gather information from both web and academic sources.\n\n"
        f"2. PRELIMINARY SYNTHESIS: Organize the key findings, identifying main concepts, perspectives, and knowledge gaps. "
        f"Create an artifact for your synthesis to improve readability and organization. Include sections for methodology, "
        f"key findings, and areas requiring further investigation.\n\n"
        f"3. VISUAL REPRESENTATION: Where appropriate, create data visualizations to illustrate key concepts, trends, "
        f"or relationships found in the research. Consider using:\n"
        f"   - Timeline charts for historical developments\n"
        f"   - Comparison tables for contrasting perspectives\n"
        f"   - Concept maps to show relationships between ideas\n"
        f"   - Flowcharts to illustrate processes\n"
        f"   - Bar/pie charts for statistical information\n"
        f"Present these visualizations as part of your analysis artifact.\n\n"
        f"4. FOLLOW-UP RESEARCH: Based on the initial findings, identify 2-3 specific aspects that need deeper investigation. "
        f"Conduct targeted follow-up research on these aspects using the deep_research tool again with more specific queries.\n\n"
        f"5. COMPREHENSIVE SYNTHESIS: Integrate all gathered information into a coherent summary that explains the main points, "
        f"different perspectives, and current understanding of the topic. Highlight how the follow-up research addressed the "
        f"knowledge gaps or expanded on key concepts from the initial exploration. Create a final artifact that includes:\n"
        f"   - Executive summary\n"
        f"   - Methodology\n"
        f"   - Key findings with visualizations\n"
        f"   - Analysis and interpretation\n"
        f"   - Conclusions and implications\n\n"
        f"6. REFERENCES: Include a properly formatted reference list at the end in APA 7th edition format. For each source used in your synthesis, create "
        f"an appropriate citation. When exact publication dates are unavailable, use the best available information (like website "
        f"copyright dates or 'n.d.' if no date is found). Format web sources as:\n"
        f"Author, A. A. (Year, Month Day). Title of page. Site Name. URL\n\n"
        f"For academic sources, use:\n"
        f"Author, A. A., & Author, B. B. (Year). Title of article. Journal Name, Volume(Issue), page range. DOI or URL\n\n"
        f"This iterative approach with proper citations and visual elements will provide a thorough understanding of {topic} "
        f"that integrates information from multiple authoritative sources and presents it in a well-organized, visually "
        f"enhanced format."
    )

# Start the server
if __name__ == "__main__":
    try:
        logger.info("Starting research-assistant MCP server...")
        mcp.run()
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        sys.exit(1)
