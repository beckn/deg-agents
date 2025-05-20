import time
import os
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

# Check which LLM provider you're using based on environment variables
if os.getenv("OPENAI_API_KEY"):
    print("Testing OpenAI API latency...")
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
    
    async def test_openai_latency():
        print(f"Using model: {model}")
        start_time = time.time()
        
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello, how are you?"}]
        )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        print(f"OpenAI API call took {elapsed:.2f} seconds")
        print(f"Response: {response.choices[0].message.content[:100]}...")
        return elapsed

    asyncio.run(test_openai_latency())

elif os.getenv("ANTHROPIC_API_KEY"):
    print("Testing Anthropic API latency...")
    import anthropic
    
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL_NAME", "claude-2")
    
    def test_anthropic_latency():
        print(f"Using model: {model}")
        start_time = time.time()
        
        response = client.completions.create(
            model=model,
            prompt=f"\n\nHuman: Hello, how are you?\n\nAssistant:",
            max_tokens_to_sample=100
        )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        print(f"Anthropic API call took {elapsed:.2f} seconds")
        print(f"Response: {response.completion[:100]}...")
        return elapsed
    
    test_anthropic_latency()

elif os.getenv("GOOGLE_API_KEY"):
    print("Testing Google Gemini API latency...")
    api_key = os.getenv("GOOGLE_API_KEY")
    model_name = "gemini-2.0-flash"  # Try this model first

    print(f"Using model: {model_name}")

    # Configure the API
    genai.configure(api_key=api_key)

    # Create the model
    model = genai.GenerativeModel(model_name)

    # Test simple query
    def test_simple_query():
        prompt = "Hello, how are you?"
        
        print(f"\nTesting simple query: '{prompt}'")
        start_time = time.time()
        
        try:
            response = model.generate_content(prompt)
            end_time = time.time()
            
            print(f"Response time: {end_time - start_time:.2f} seconds")
            print(f"Response: {response.text[:100]}...")
        except Exception as e:
            print(f"Error: {e}")

    # Test with chat history context
    def test_with_context():
        chat = model.start_chat(history=[])
        
        print("\nTesting with chat context")
        
        # First message
        print("Sending first message...")
        start_time = time.time()
        response = chat.send_message("Hello, my name is Alex")
        end_time = time.time()
        print(f"First response time: {end_time - start_time:.2f} seconds")
        print(f"Response: {response.text[:100]}...")
        
        # Second message (with context)
        print("\nSending second message with context...")
        start_time = time.time()
        response = chat.send_message("What's my name?")
        end_time = time.time()
        print(f"Second response time: {end_time - start_time:.2f} seconds")
        print(f"Response: {response.text[:100]}...")

    # Run the tests
    if __name__ == "__main__":
        test_simple_query()
        test_with_context()

else:
    print("No recognized LLM API keys found in environment variables.")
    print("Please set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY in your .env file.")