import asyncio
import os
from dotenv import load_dotenv

# Load env vars
load_dotenv()

from app.services.reranking import RerankingService

async def test_analyze():
    print("Initializing Reranking Service...")
    service = RerankingService()
    
    query = 'i want the book "The way of the superior man"'
    print(f"\nAnalyzing query: {query}")
    
    analysis = await service.analyze_query(
        user_message=query,
        user_profile_summary="User likes self-help."
    )
    
    print("\n--- RESULT ---")
    print(f"specific_book_requested: {analysis.get('specific_book_requested')}")
    print(f"needs_book_search: {analysis.get('needs_book_search')}")
    
    if analysis.get('specific_book_requested'):
        print("\nSUCCESS: Title extracted.")
    else:
        print("\nFAILURE: specific_book_requested is None or empty.")

if __name__ == "__main__":
    asyncio.run(test_analyze())
