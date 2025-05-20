import os
import time
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Global cache for warmed models
_warmed_models = {}

async def warm_up_model():
    """
    Warms up the Gemini model to avoid cold start latency.
    Returns the warmed model instance.
    """
    model_name = os.getenv("MODEL", "gemini-pro")
    cache_key = model_name  # Just use the model name as the cache key
    
    # Check if we already have a warmed model
    if cache_key in _warmed_models:
        logger.info(f"Using cached model {cache_key}")
        return _warmed_models[cache_key]
    
    logger.info(f"Warming up model {model_name}")
    start_time = time.time()
    
    try:
        # Configure the API
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("No Google API key found in environment variables")
            return None
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # Send a simple query to warm up the model
        response = model.generate_content("Hello")
        
        end_time = time.time()
        logger.info(f"Model warm-up complete in {end_time - start_time:.2f} seconds")
        
        # Cache the warmed model
        _warmed_models[cache_key] = model
        return model
        
    except Exception as e:
        logger.error(f"Error warming up model: {e}")
        return None

def get_warmed_model():
    """
    Gets the previously warmed model or returns None if not available.
    """
    model_name = os.getenv("MODEL", "gemini-pro")
    return _warmed_models.get(model_name) 