"""
AI Assignment - Task 2: Recipe Chatbot Backend (FastAPI)
This API provides recipe suggestions based on ingredients using RAG approach with Ollama
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import requests
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="Recipe Chatbot API",
    description="AI-powered recipe recommendation system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:1b"  # Small model for CPU

# Load recipes database
try:
    with open('recipes.json', 'r') as f:
        recipes_data = json.load(f)
        RECIPES = recipes_data['recipes']
    print(f"✅ Loaded {len(RECIPES)} recipes from database")
except FileNotFoundError:
    print("⚠️ Warning: recipes.json not found. Creating empty database.")
    RECIPES = []


# Pydantic models for API
class IngredientQuery(BaseModel):
    """Model for ingredient-based query"""
    ingredients: List[str]
    max_results: Optional[int] = 5


class ChatQuery(BaseModel):
    """Model for general chat query"""
    message: str


class RecipeResponse(BaseModel):
    """Model for recipe response"""
    id: int
    name: str
    ingredients: List[str]
    instructions: str
    cuisine: str
    prep_time: str
    difficulty: str
    match_score: float


class ChatResponse(BaseModel):
    """Model for chat response"""
    message: str
    recipes: Optional[List[RecipeResponse]] = None


# Helper Functions
def search_recipes_by_ingredients(user_ingredients: List[str], max_results: int = 5) -> List[dict]:
    """
    Search recipes that match the given ingredients using simple matching.
    Returns recipes ranked by number of matching ingredients.
    """
    user_ingredients_lower = [ing.lower().strip() for ing in user_ingredients]
    matched_recipes = []
    
    for recipe in RECIPES:
        # Count how many user ingredients are in this recipe
        recipe_ingredients_lower = [ing.lower() for ing in recipe['ingredients']]
        matches = sum(1 for user_ing in user_ingredients_lower 
                     if any(user_ing in recipe_ing for recipe_ing in recipe_ingredients_lower))
        
        if matches > 0:
            match_score = (matches / len(user_ingredients_lower)) * 100
            matched_recipes.append({
                **recipe,
                'match_score': round(match_score, 2)
            })
    
    # Sort by match score (descending)
    matched_recipes.sort(key=lambda x: x['match_score'], reverse=True)
    
    return matched_recipes[:max_results]


def generate_ollama_response(prompt: str, context: str = "") -> str:
    """
    Generate response using Ollama local LLM.
    """
    try:
        # Construct full prompt with context
        full_prompt = f"""You are a helpful recipe assistant. Be conversational and friendly.

Context (Available Recipes):
{context}

User Query: {prompt}

Provide a helpful, concise response. If recipes are available in context, suggest them naturally."""

        payload = {
            "model": MODEL_NAME,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 300  # Limit response length for speed
            }
        }
        
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.json()['response']
        else:
            return "I'm having trouble connecting to my recipe knowledge. Here are the recipes I found for you!"
            
    except requests.exceptions.RequestException as e:
        print(f"Ollama error: {e}")
        return "I found some great recipes for you based on your ingredients!"


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "message": "Recipe Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "/search": "Search recipes by ingredients (POST)",
            "/chat": "Chat with recipe bot (POST)",
            "/recipes": "Get all recipes (GET)",
            "/health": "Health check (GET)"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if Ollama is running
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        ollama_status = "connected" if response.status_code == 200 else "disconnected"
    except:
        ollama_status = "disconnected"
    
    return {
        "status": "healthy",
        "recipes_loaded": len(RECIPES),
        "ollama_status": ollama_status,
        "model": MODEL_NAME
    }


@app.get("/recipes")
async def get_all_recipes():
    """Get all available recipes"""
    return {
        "total": len(RECIPES),
        "recipes": RECIPES
    }


@app.post("/search", response_model=ChatResponse)
async def search_recipes(query: IngredientQuery):
    """
    Search for recipes based on ingredients.
    
    Example request:
    {
        "ingredients": ["eggs", "onions"],
        "max_results": 5
    }
    """
    if not query.ingredients:
        raise HTTPException(status_code=400, detail="Please provide at least one ingredient")
    
    # Search for matching recipes
    matched_recipes = search_recipes_by_ingredients(query.ingredients, query.max_results)
    
    if not matched_recipes:
        return ChatResponse(
            message=f"I couldn't find any recipes with {', '.join(query.ingredients)}. Try different ingredients!",
            recipes=[]
        )
    
    # Create context for LLM
    context = "\n\n".join([
        f"Recipe {i+1}: {recipe['name']} ({recipe['cuisine']}, {recipe['difficulty']})\n"
        f"Ingredients: {', '.join(recipe['ingredients'])}\n"
        f"Instructions: {recipe['instructions']}\n"
        f"Match Score: {recipe['match_score']}%"
        for i, recipe in enumerate(matched_recipes)
    ])
    
    # Generate conversational response using Ollama
    user_message = f"I have {', '.join(query.ingredients)}. What can I cook?"
    llm_response = generate_ollama_response(user_message, context)
    
    # Convert to RecipeResponse format
    recipe_responses = [
        RecipeResponse(**recipe)
        for recipe in matched_recipes
    ]
    
    return ChatResponse(
        message=llm_response,
        recipes=recipe_responses
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(query: ChatQuery):
    """
    General chat endpoint for conversational queries.
    
    Example request:
    {
        "message": "I want to make something with eggs and onions"
    }
    """
    if not query.message.strip():
        raise HTTPException(status_code=400, detail="Please provide a message")
    
    # Try to extract ingredients from message (simple keyword matching)
    common_ingredients = [
        "egg", "eggs", "onion", "onions", "tomato", "tomatoes", "chicken", 
        "rice", "potato", "potatoes", "garlic", "ginger", "cheese", "bread",
        "milk", "butter", "flour", "pasta", "noodles", "vegetables", "fish"
    ]
    
    message_lower = query.message.lower()
    found_ingredients = [ing for ing in common_ingredients if ing in message_lower]
    
    if found_ingredients:
        # Search for recipes with found ingredients
        matched_recipes = search_recipes_by_ingredients(found_ingredients, max_results=3)
        
        if matched_recipes:
            context = "\n\n".join([
                f"Recipe: {recipe['name']}\n"
                f"Cuisine: {recipe['cuisine']}\n"
                f"Difficulty: {recipe['difficulty']}\n"
                f"Ingredients: {', '.join(recipe['ingredients'][:8])}..."
                for recipe in matched_recipes
            ])
            
            llm_response = generate_ollama_response(query.message, context)
            
            recipe_responses = [RecipeResponse(**recipe) for recipe in matched_recipes]
            
            return ChatResponse(
                message=llm_response,
                recipes=recipe_responses
            )
    
    # General query without specific ingredients
    llm_response = generate_ollama_response(query.message)
    
    return ChatResponse(
        message=llm_response,
        recipes=None
    )


# Run the server
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🍳 RECIPE CHATBOT API STARTING...")
    print("="*60)
    print(f"📚 Loaded {len(RECIPES)} recipes")
    print(f"🤖 Using Ollama model: {MODEL_NAME}")
    print("🌐 API will be available at: http://localhost:8001")
    print("📖 Documentation at: http://localhost:8001/docs")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
