import asyncio
from providers.chicago_crashes import ChicagoCrashProvider


async def main():
    provider = ChicagoCrashProvider()
    
    print("Fetching Chicago crash data...")
    print(f"URL: {provider.url}\n")
    
    try:
        # Fetch with limit to keep output manageable
        data = await provider.fetch_with_limit(5)
        
        print(f"Successfully fetched {len(data)} records:\n")
        
        for i, record in enumerate(data, 1):
            print(f"Record {i}:")
            for key, value in record.items():
                print(f"  {key}: {value}")
            print()
    
    except Exception as e:
        print(f"Error fetching data: {e}")


if __name__ == "__main__":
    asyncio.run(main())
