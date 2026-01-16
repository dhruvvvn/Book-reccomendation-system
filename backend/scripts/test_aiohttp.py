import aiohttp
import asyncio

async def main():
    print("Testing aiohttp...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://www.google.com') as resp:
                print(f"Status: {resp.status}")
                print("Success!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
