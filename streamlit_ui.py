"""
AI Assignment - Task 2: Recipe Chatbot UI (Streamlit)
Beautiful and interactive chatbot interface
"""

import streamlit as st
import requests
import json
from typing import List, Dict

# Configuration
API_URL = "http://localhost:8001"

# Page configuration
st.set_page_config(
    page_title="Recipe Chatbot 🍳",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #FF6B6B;
        margin-bottom: 1rem;
    }
    .recipe-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #FF6B6B;
        margin-bottom: 1rem;
    }
    .match-score {
        background-color: #4ECDC4;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: bold;
    }
    .difficulty-easy { color: #2ecc71; font-weight: bold; }
    .difficulty-medium { color: #f39c12; font-weight: bold; }
    .difficulty-hard { color: #e74c3c; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=3)
        return response.status_code == 200
    except:
        return False


def search_recipes_by_ingredients(ingredients: List[str], max_results: int = 5) -> Dict:
    """Call the /search endpoint"""
    try:
        payload = {
            "ingredients": ingredients,
            "max_results": max_results
        }
        response = requests.post(f"{API_URL}/search", json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return {"message": "Error searching recipes", "recipes": []}
    except Exception as e:
        return {"message": f"Error: {str(e)}", "recipes": []}


def chat_with_bot(message: str) -> Dict:
    """Call the /chat endpoint"""
    try:
        payload = {"message": message}
        response = requests.post(f"{API_URL}/chat", json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return {"message": "Error communicating with bot", "recipes": None}
    except Exception as e:
        return {"message": f"Error: {str(e)}", "recipes": None}


def display_recipe_card(recipe: Dict, index: int):
    """Display a recipe in a card format"""
    difficulty_class = f"difficulty-{recipe['difficulty'].lower()}"
    
    st.markdown(f"""
    <div class="recipe-card">
        <h3>🍽️ {recipe['name']} <span class="match-score">{recipe['match_score']}% Match</span></h3>
        <p><strong>Cuisine:</strong> {recipe['cuisine']} | 
           <strong>Prep Time:</strong> {recipe['prep_time']} | 
           <strong>Difficulty:</strong> <span class="{difficulty_class}">{recipe['difficulty']}</span></p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander(f"📋 View Full Recipe - {recipe['name']}", expanded=False):
        st.markdown("**Ingredients:**")
        cols = st.columns(2)
        mid = len(recipe['ingredients']) // 2
        with cols[0]:
            for ing in recipe['ingredients'][:mid]:
                st.write(f"• {ing}")
        with cols[1]:
            for ing in recipe['ingredients'][mid:]:
                st.write(f"• {ing}")
        
        st.markdown("**Instructions:**")
        st.write(recipe['instructions'])


def main():
    # Header
    st.markdown('<p class="main-header">🍳 AI Recipe Chatbot</p>', unsafe_allow_html=True)
    st.markdown("### Find delicious recipes based on your ingredients!")
    
    # Check API health
    if not check_api_health():
        st.error("⚠️ Backend API is not running! Please start the FastAPI server first.")
        st.code("python app.py", language="bash")
        return
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Mode selection
        mode = st.radio(
            "Choose Mode:",
            ["🔍 Search by Ingredients", "💬 Chat with Bot"],
            help="Search mode finds recipes by ingredients. Chat mode is conversational."
        )
        
        st.divider()
        
        # Additional info
        st.markdown("### 📊 Stats")
        try:
            health = requests.get(f"{API_URL}/health").json()
            st.metric("Total Recipes", health['recipes_loaded'])
            st.metric("Ollama Status", health['ollama_status'].upper())
            st.metric("Model", health['model'])
        except:
            st.warning("Cannot fetch stats")
        
        st.divider()
        
        # Instructions
        st.markdown("### 💡 How to Use")
        if mode == "🔍 Search by Ingredients":
            st.markdown("""
            1. Enter ingredients (comma-separated)
            2. Click 'Find Recipes'
            3. View matched recipes
            """)
        else:
            st.markdown("""
            1. Type your message
            2. Click 'Send'
            3. Get AI-powered suggestions
            """)
    
    # Main content area
    if mode == "🔍 Search by Ingredients":
        # Ingredient search mode
        st.subheader("🔍 Search Recipes by Ingredients")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            ingredients_input = st.text_input(
                "Enter ingredients (comma-separated):",
                placeholder="e.g., eggs, onions, tomatoes",
                help="Type ingredients separated by commas"
            )
        
        with col2:
            max_results = st.number_input(
                "Max Results:",
                min_value=1,
                max_value=10,
                value=5,
                step=1
            )
        
        if st.button("🔍 Find Recipes", type="primary", use_container_width=True):
            if ingredients_input.strip():
                with st.spinner("🔎 Searching for recipes..."):
                    ingredients = [ing.strip() for ing in ingredients_input.split(",")]
                    result = search_recipes_by_ingredients(ingredients, max_results)
                    
                    # Display AI response
                    st.success("🤖 AI Assistant Says:")
                    st.info(result['message'])
                    
                    # Display recipes
                    if result['recipes']:
                        st.markdown(f"### 📚 Found {len(result['recipes'])} Recipe(s)")
                        for idx, recipe in enumerate(result['recipes'], 1):
                            display_recipe_card(recipe, idx)
                    else:
                        st.warning("No recipes found with those ingredients. Try different ones!")
            else:
                st.warning("⚠️ Please enter at least one ingredient!")
    
    else:
        # Chat mode
        st.subheader("💬 Chat with Recipe Bot")
        
        # Initialize chat history in session state
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "recipes" in message and message["recipes"]:
                    for idx, recipe in enumerate(message["recipes"], 1):
                        display_recipe_card(recipe, idx)
        
        # Chat input
        if prompt := st.chat_input("Ask me anything about recipes..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Get bot response
            with st.chat_message("assistant"):
                with st.spinner("🤔 Thinking..."):
                    result = chat_with_bot(prompt)
                    st.markdown(result['message'])
                    
                    if result['recipes']:
                        for idx, recipe in enumerate(result['recipes'], 1):
                            display_recipe_card(recipe, idx)
                    
                    # Add to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result['message'],
                        "recipes": result['recipes']
                    })
        
        # Clear chat button
        if st.session_state.messages:
            if st.button("🗑️ Clear Chat History"):
                st.session_state.messages = []
                st.rerun()
    
    # Footer
    st.divider()
    st.markdown("""
    <p style="text-align: center; color: #666; font-size: 0.9rem;">
        Made with ❤️ using Streamlit, FastAPI, and Ollama | AI Assignment Task 2
    </p>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
