import os
from dotenv import load_dotenv
from firecrawl import V1FirecrawlApp

load_dotenv()

class FirecrawlService:
    """Thin wrapper around the Firecrawl API for searching and scraping web pages."""

    def __init__(self):
        """Connect to Firecrawl using the FIRECRAWL_API_KEY from the .env file."""
        # Load the API key from the environment and fail fast if it's missing
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("missing FIRECRAWL_API_KEY")
        self.app = V1FirecrawlApp(api_key=api_key)

    def search_companies(self, query: str, num_results: int = 5):
        """Run a web search and return a list of result documents. Returns an empty list on failure."""
        try:
            response = self.app.search(
                query=f"{query} company pricing",
                limit=num_results
            )
            # response.data is a list of V1FirecrawlDocument objects
            return response.data if response and response.data else []
        except Exception as e:
            print(e)
            return []

    def scrape_company_pages(self, url: str):
        """Scrape a single URL and return its content as a document. Returns None on failure."""
        try:
            result = self.app.scrape_url(
                url,
                formats=["markdown"]
            )
            return result
        except Exception as e:
            print(e)
            return None
