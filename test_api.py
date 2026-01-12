import httpx
import asyncio

async def test_api():
    url = "http://localhost:8000/analyze"
    
    # Create dummy files
    with open("test_guitar.wav", "wb") as f:
        f.write(b"dummy audio content" * 1000)
    with open("test_song.wav", "wb") as f:
        f.write(b"dummy audio content" * 1000)

    files = {
        "guitar_sample": ("test_guitar.wav", open("test_guitar.wav", "rb"), "audio/wav"),
        "original_song": ("test_song.wav", open("test_song.wav", "rb"), "audio/wav")
    }

    try:
        async with httpx.AsyncClient() as client:
            print("Sending request...")
            async with client.stream("POST", url, files=files) as response:
                print(f"Status Code: {response.status_code}")
                if response.status_code != 200:
                    print(f"Error Response: {await response.aread()}")
                else:
                    async for line in response.aiter_lines():
                        print(f"Received: {line}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())
