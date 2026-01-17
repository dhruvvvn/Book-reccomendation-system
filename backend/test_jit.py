import asyncio
import os
from dotenv import load_dotenv

# Load env vars
load_dotenv()

from app.services.description import DescriptionService

async def test_jit():
    print("Initializing Description Service...")
    service = DescriptionService()
    
    title = "The Way of the Superior Man"
    print(f"Searching for: {title}")
    
    desc = await service.get_or_generate(
        book_id="test_id_123",
        title=title,
        author="",
        genre="Self-Help"
    )
    
    print("\n--- RESULT ---")
    print(f"Description length: {len(desc)}")
    print(f"Description preview: {desc[:100]}...")
    
    if desc == "Description not available.":
        print("\nFAILURE: Service returned 'Description not available.'")
    else:
        print("\nSUCCESS: Service returned a description.")

if __name__ == "__main__":
    asyncio.run(test_jit())
