"""Main Streamlit application for AI Recipe Analyzer."""

import streamlit as st
import sys
import os
import time
import re
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urlparse

# Add src directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from utils.config import setup_logging, validate_aws_config, get_app_info
    from utils.observability import obs_manager, trace_function
    from services.bedrock_service import BedrockService
    from services.web_scraper import WebScraperService
    from services.recipe_detector import RecipeDetectorService
    from services.rag_service import RAGService
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.stop()

# Initialize logging
setup_logging()


class RecipeAnalyzerApp:
    """Main application class for the Recipe Analyzer."""
    
    def __init__(self):
        """Initialize the application."""
        self.setup_page_config()
        self.initialize_session_state()
        self.initialize_services()
    
    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="AI Recipe Analyzer",
            page_icon="🍳",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def initialize_session_state(self):
        """Initialize session state variables."""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "processing" not in st.session_state:
            st.session_state.processing = False
        
        if "last_analysis" not in st.session_state:
            st.session_state.last_analysis = None
        
        if "services_initialized" not in st.session_state:
            st.session_state.services_initialized = False
        
        if "error_count" not in st.session_state:
            st.session_state.error_count = 0
    
    def initialize_services(self):
        """Initialize AI services with error handling."""
        if not st.session_state.services_initialized:
            try:
                with st.spinner("Initializing AI services..."):
                    self.bedrock_service = BedrockService()
                    self.web_scraper = WebScraperService()
                    self.recipe_detector = RecipeDetectorService()
                    self.rag_service = RAGService()
                    
                    st.session_state.services_initialized = True
                    
            except Exception as e:
                st.error(f"Failed to initialize services: {str(e)}")
                st.info("Some features may not be available. Please check your configuration.")
                return False
        else:
            # Services already initialized
            self.bedrock_service = BedrockService()
            self.web_scraper = WebScraperService()
            self.recipe_detector = RecipeDetectorService()
            self.rag_service = RAGService()
        
        return True
    
    def render_header(self):
        """Render application header."""
        st.title("🍳 AI Recipe Analyzer")
        st.markdown("""
        ### Extract ingredients from recipe URLs or search for dish recipes
        
        **Two ways to get recipes:**
        - 📄 **URL Analysis**: Enter a recipe webpage URL to extract ingredients
        - 🔍 **Dish Search**: Enter a dish name to search our recipe knowledge base
        """)
    
    def render_sidebar(self):
        """Render sidebar with configuration and status."""
        with st.sidebar:
            st.header("⚙️ Configuration")
            
            # Application info
            app_info = get_app_info()
            config_status = validate_aws_config()
            
            with st.expander("📋 Application Info", expanded=False):
                st.write(f"**Service:** {app_info['service_name']}")
                st.write(f"**Model:** {app_info['model_id']}")
                st.write(f"**Region:** {app_info['region']}")
                st.write(f"**Debug:** {'On' if app_info['debug_mode'] else 'Off'}")
            
            # Service status
            st.subheader("🔧 Service Status")
            
            if config_status["aws_configured"]:
                st.success("✅ AWS configured")
            else:
                st.error("❌ AWS not configured")
            
            if config_status["bedrock_configured"]:
                st.success("✅ Bedrock configured")
            else:
                st.error("❌ Bedrock not configured")
            
            if config_status["knowledge_base_configured"]:
                st.success("✅ Knowledge Base configured")
            else:
                st.warning("⚠️ Knowledge Base not configured")
            
            if st.session_state.services_initialized:
                st.success("✅ Services initialized")
            else:
                st.warning("⚠️ Services not initialized")
            
            # Observability status
            if obs_manager.is_initialized:
                st.success("✅ Observability active")
            else:
                st.warning("⚠️ Observability inactive")
            
            # Configuration issues
            if config_status["issues"]:
                with st.expander("⚠️ Configuration Issues", expanded=True):
                    for issue in config_status["issues"]:
                        st.error(f"• {issue}")
            
            # Session statistics
            with st.expander("📊 Session Stats", expanded=False):
                st.write(f"**Messages:** {len(st.session_state.messages)}")
                st.write(f"**Errors:** {st.session_state.error_count}")
                if st.session_state.last_analysis:
                    st.write(f"**Last Analysis:** {st.session_state.last_analysis.get('timestamp', 'Unknown')}")
                
                if st.button("Clear History"):
                    st.session_state.messages = []
                    st.session_state.last_analysis = None
                    st.session_state.error_count = 0
                    st.success("History cleared!")
                    st.rerun()
    
    def validate_url(self, url: str) -> tuple[bool, str]:
        """Validate URL format and safety."""
        if not url.strip():
            return False, "Please enter a URL"
        
        # Basic URL format validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, "Invalid URL format. Please include http:// or https://"
            
            if parsed.scheme not in ['http', 'https']:
                return False, "Only HTTP and HTTPS URLs are supported"
            
            # Check for local/private URLs
            if any(local in parsed.netloc.lower() for local in ['localhost', '127.0.0.1', '0.0.0.0']):
                return False, "Local URLs are not allowed for security reasons"
            
            return True, ""
            
        except Exception:
            return False, "Invalid URL format"
    
    def validate_dish_name(self, dish_name: str) -> tuple[bool, str]:
        """Validate dish name input."""
        if not dish_name.strip():
            return False, "Please enter a dish name"
        
        if len(dish_name.strip()) < 2:
            return False, "Dish name must be at least 2 characters long"
        
        if len(dish_name.strip()) > 100:
            return False, "Dish name must be less than 100 characters"
        
        # Check for reasonable characters (letters, numbers, spaces, common punctuation)
        if not re.match(r'^[a-zA-Z0-9\s\-.,()\'\"]+$', dish_name.strip()):
            return False, "Dish name contains invalid characters"
        
        return True, ""
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add message to chat history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "metadata": metadata or {}
        }
        st.session_state.messages.append(message)
    
    def display_chat_history(self):
        """Display chat message history."""
        if not st.session_state.messages:
            st.info("👋 Welcome! Enter a recipe URL or dish name to get started.")
            return
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                
                # Display timestamp
                st.caption(f"🕒 {message['timestamp']}")
                
                # Display metadata if available
                if message.get("metadata"):
                    metadata = message["metadata"]
                    
                    # Show analysis results
                    if "analysis_result" in metadata:
                        result = metadata["analysis_result"]
                        # Check if this is a RAG search result or URL analysis result
                        if "recipe_found" in result:
                            self.display_rag_search_result(result)
                        else:
                            self.display_analysis_result(result)
                    
                    # Show error details
                    if "error_details" in metadata:
                        with st.expander("🔍 Error Details"):
                            st.code(metadata["error_details"])
    
    def display_analysis_result(self, result: Dict[str, Any]):
        """Display recipe analysis results in a formatted way."""
        if not result:
            return
        
        # Recipe detection status
        is_recipe = result.get("is_recipe", False)
        confidence = result.get("detection_confidence", 0.0)
        
        if is_recipe:
            st.success(f"✅ Recipe detected (confidence: {confidence:.1%})")
        else:
            st.warning(f"❌ Not a recipe (confidence: {confidence:.1%})")
            if result.get("detection_reason"):
                st.write(f"**Reason:** {result['detection_reason']}")
            return
        
        # Display ingredients if available
        ingredients = result.get("ingredients", [])
        if ingredients:
            st.subheader("🥘 Ingredients")
            
            # Show serving size if available
            serving_size = result.get("serving_size", "")
            if serving_size:
                st.write(f"**Serves:** {serving_size}")
            
            # Display ingredients in a table
            ingredient_data = []
            for ing in ingredients:
                ingredient_data.append({
                    "Ingredient": ing.get("name", ""),
                    "Quantity": ing.get("quantity", ""),
                    "Unit": ing.get("unit", ""),
                    "Notes": ing.get("notes", "")
                })
            
            if ingredient_data:
                st.dataframe(ingredient_data, use_container_width=True)
            
            # Copy ingredients button
            ingredients_text = self.format_ingredients_for_copy(ingredients)
            if st.button("📋 Copy Ingredients", key=f"copy_{result.get('url', 'ingredients')}"):
                st.code(ingredients_text, language="text")
                st.success("Ingredients formatted for copying!")
        
        # Show analysis metadata
        with st.expander("📊 Analysis Details"):
            col1, col2 = st.columns(2)
    
    def display_rag_search_result(self, result: Dict[str, Any]):
        """Display RAG search results in a formatted way."""
        if not result:
            return
        
        # Recipe search status
        recipe_found = result.get("recipe_found", False)
        confidence = result.get("confidence", 0.0)
        
        if recipe_found:
            st.success(f"✅ Recipe found (confidence: {confidence:.1%})")
            
            # Display recipe answer
            answer = result.get("answer", "")
            if answer:
                st.subheader("📖 Recipe Information")
                st.write(answer)
            
            # Display ingredients if available
            ingredients = result.get("ingredients", [])
            if ingredients:
                st.subheader("🥘 Ingredients")
                
                # Display ingredients as list
                for ingredient in ingredients:
                    if isinstance(ingredient, str):
                        st.write(f"• {ingredient}")
                    elif isinstance(ingredient, dict):
                        name = ingredient.get("name", "")
                        quantity = ingredient.get("quantity", "")
                        unit = ingredient.get("unit", "")
                        notes = ingredient.get("notes", "")
                        
                        ingredient_text = f"• {name}"
                        if quantity:
                            ingredient_text += f" - {quantity}"
                        if unit:
                            ingredient_text += f" {unit}"
                        if notes:
                            ingredient_text += f" ({notes})"
                        
                        st.write(ingredient_text)
            
            # Display instructions if available
            instructions = result.get("instructions", [])
            if instructions:
                st.subheader("👩‍🍳 Instructions")
                for i, instruction in enumerate(instructions, 1):
                    st.write(f"{i}. {instruction}")
        else:
            st.warning(f"❌ No recipe found (confidence: {confidence:.1%})")
            
            # Show the AI response even if no recipe was found
            answer = result.get("answer", "")
            if answer:
                st.write(f"**Response:** {answer}")
        
        # Show sources if available
        sources = result.get("sources", [])
        if sources:
            with st.expander(f"📚 Sources ({len(sources)} documents)"):
                for i, source in enumerate(sources, 1):
                    st.write(f"**Source {i}:**")
                    content = source.get("content", "")
                    if content:
                        st.write(content)
                    
                    metadata = source.get("metadata", {})
                    if metadata:
                        st.json(metadata)
                    st.divider()
        
        # Show search metadata
        with st.expander("📊 Search Details"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Recipe Found:** {recipe_found}")
                st.write(f"**Confidence:** {confidence:.2f}")
                st.write(f"**Processing Time:** {result.get('processing_time', 'N/A')} seconds")
                st.write(f"**Language:** {result.get('language', 'Unknown')}")
            
            with col2:
                st.write(f"**Recipe Name:** {result.get('recipe_name', 'N/A')}")
                st.write(f"**Sources Count:** {len(sources)}")
                st.write(f"**Query Used:** {result.get('query_used', 'N/A')}")
                if result.get("timestamp"):
                    st.write(f"**Timestamp:** {result['timestamp']}")
            
            if result.get("error"):
                st.error(f"**Error:** {result['error']}")
    
    def format_ingredients_for_copy(self, ingredients: list) -> str:
        """Format ingredients list for easy copying."""
        if not ingredients:
            return "No ingredients found."
        
        lines = ["INGREDIENTS:", "=" * 12]
        
        for i, ing in enumerate(ingredients, 1):
            name = ing.get("name", "")
            quantity = ing.get("quantity", "")
            unit = ing.get("unit", "")
            notes = ing.get("notes", "")
            
            line = f"{i:2d}. {name}"
            if quantity:
                line += f" ({quantity}"
                if unit:
                    line += f" {unit}"
                line += ")"
            if notes:
                line += f" - {notes}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    @trace_function("streamlit_analyze_url")
    def analyze_recipe_url(self, url: str) -> Dict[str, Any]:
        """Analyze recipe from URL."""
        try:
            start_time = time.time()
            
            # Record the analysis request
            obs_manager.record_metric("streamlit_analysis_request", 1.0, {
                "type": "url",
                "success": "pending"
            })
            
            # Perform analysis
            result = self.recipe_detector.analyze_url(url)
            
            processing_time = time.time() - start_time
            result["total_processing_time"] = processing_time
            
            # Record success metrics
            obs_manager.record_metric("streamlit_analysis_request", 1.0, {
                "type": "url",
                "success": "true",
                "is_recipe": str(result.get("is_recipe", False))
            })
            
            obs_manager.record_metric("streamlit_processing_time", processing_time, {
                "type": "url_analysis"
            })
            
            return result
            
        except Exception as e:
            # Record error metrics
            obs_manager.record_metric("streamlit_analysis_request", 1.0, {
                "type": "url",
                "success": "false",
                "error": "analysis_failed"
            })
            
            st.session_state.error_count += 1
            raise e
    
    @trace_function("streamlit_search_dish")
    def search_dish_recipe(self, dish_name: str) -> Dict[str, Any]:
        """Search for dish recipe using RAG."""
        try:
            start_time = time.time()
            
            # Record the search request
            obs_manager.record_metric("streamlit_analysis_request", 1.0, {
                "type": "dish_search",
                "success": "pending"
            })
            
            # Perform RAG search
            result = self.rag_service.search_recipe(dish_name)
            
            processing_time = time.time() - start_time
            result["total_processing_time"] = processing_time
            
            # Record success metrics
            obs_manager.record_metric("streamlit_analysis_request", 1.0, {
                "type": "dish_search",
                "success": "true",
                "found_recipe": str(bool(result.get("recipe_found", False)))
            })
            
            obs_manager.record_metric("streamlit_processing_time", processing_time, {
                "type": "dish_search"
            })
            
            return result
            
        except Exception as e:
            # Record error metrics
            obs_manager.record_metric("streamlit_analysis_request", 1.0, {
                "type": "dish_search",
                "success": "false",
                "error": "search_failed"
            })
            
            st.session_state.error_count += 1
            raise e
    
    def handle_url_input(self):
        """Handle URL input form."""
        with st.form("url_form", clear_on_submit=True):
            st.subheader("📄 Analyze Recipe URL")
            
            url = st.text_input(
                "Enter recipe URL:",
                placeholder="https://example.com/recipe-page",
                help="Enter a full URL to a recipe webpage"
            )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                submit_url = st.form_submit_button("🔍 Analyze URL")
            with col2:
                if url:
                    is_valid, error_msg = self.validate_url(url)
                    if is_valid:
                        st.success("✅ Valid URL format")
                    else:
                        st.error(f"❌ {error_msg}")
            
            if submit_url:
                is_valid, error_msg = self.validate_url(url)
                
                if not is_valid:
                    st.error(error_msg)
                    return
                
                if st.session_state.processing:
                    st.warning("⏳ Analysis already in progress...")
                    return
                
                # Add user message
                self.add_message("user", f"Analyze recipe URL: {url}")
                
                # Process URL
                st.session_state.processing = True
                
                try:
                    with st.spinner(f"🔍 Analyzing recipe from {url}..."):
                        result = self.analyze_recipe_url(url)
                        
                        st.session_state.last_analysis = result
                        
                        # Add assistant response
                        if result.get("is_recipe", False):
                            response = f"✅ Found recipe with {result.get('total_ingredients', 0)} ingredients!"
                        else:
                            response = f"❌ No recipe detected. {result.get('detection_reason', '')}"
                        
                        self.add_message("assistant", response, {"analysis_result": result})
                        
                        st.success("Analysis complete!")
                        st.rerun()
                        
                except Exception as e:
                    error_msg = f"❌ Analysis failed: {str(e)}"
                    self.add_message("assistant", error_msg, {"error_details": str(e)})
                    st.error(error_msg)
                
                finally:
                    st.session_state.processing = False
    
    def handle_dish_input(self):
        """Handle dish name input form."""
        with st.form("dish_form", clear_on_submit=True):
            st.subheader("🔍 Search Recipe by Dish Name")
            
            dish_name = st.text_input(
                "Enter dish name:",
                placeholder="e.g., Chicken Teriyaki, Pasta Carbonara",
                help="Enter the name of a dish to search our recipe database"
            )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                submit_dish = st.form_submit_button("🔍 Search Recipe")
            with col2:
                if dish_name:
                    is_valid, error_msg = self.validate_dish_name(dish_name)
                    if is_valid:
                        st.success("✅ Valid dish name")
                    else:
                        st.error(f"❌ {error_msg}")
            
            if submit_dish:
                is_valid, error_msg = self.validate_dish_name(dish_name)
                
                if not is_valid:
                    st.error(error_msg)
                    return
                
                if st.session_state.processing:
                    st.warning("⏳ Search already in progress...")
                    return
                
                # Add user message
                self.add_message("user", f"Search recipe for: {dish_name}")
                
                # Process dish search
                st.session_state.processing = True
                
                try:
                    with st.spinner(f"🔍 Searching for {dish_name} recipes..."):
                        result = self.search_dish_recipe(dish_name)
                        
                        st.session_state.last_analysis = result
                        
                        # Add assistant response
                        if result.get("recipe_found", False):
                            response = f"✅ Found recipe for {dish_name}!"
                        else:
                            response = f"❌ No recipe found for {dish_name}. {result.get('message', '')}"
                        
                        self.add_message("assistant", response, {"analysis_result": result})
                        
                        st.success("Search complete!")
                        st.rerun()
                        
                except Exception as e:
                    error_msg = f"❌ Search failed: {str(e)}"
                    self.add_message("assistant", error_msg, {"error_details": str(e)})
                    st.error(error_msg)
                
                finally:
                    st.session_state.processing = False
    
    def render_main_interface(self):
        """Render the main chat interface."""
        # Input section
        col1, col2 = st.columns(2)
        
        with col1:
            self.handle_url_input()
        
        with col2:
            self.handle_dish_input()
        
        # Processing indicator
        if st.session_state.processing:
            st.info("⏳ Processing your request...")
        
        # Chat history
        st.divider()
        st.subheader("💬 Chat History")
        self.display_chat_history()
    
    def render_help_section(self):
        """Render help and instructions."""
        with st.expander("📖 How to Use", expanded=False):
            st.markdown("""
            ### 🔍 Recipe URL Analysis
            
            1. **Enter a Recipe URL**: Paste the full URL of a recipe webpage
            2. **Click "Analyze URL"**: The AI will fetch and analyze the page
            3. **View Results**: See if it's a recipe and extract ingredients
            
            **Supported URL formats:**
            - `https://example.com/recipe-page`
            - `http://cooking-site.com/recipes/dish-name`
            
            ### 🔍 Dish Name Search
            
            1. **Enter Dish Name**: Type the name of a dish you want to cook
            2. **Click "Search Recipe"**: Search our knowledge base for recipes
            3. **View Results**: Get recipe instructions and ingredients
            
            **Example searches:**
            - "Chicken Teriyaki"
            - "Pasta Carbonara"
            - "Chocolate Chip Cookies"
            
            ### ✨ Features
            
            - **Multi-language support**: Supports Japanese and English recipes
            - **Smart detection**: AI-powered recipe classification
            - **Structured extraction**: Organized ingredient lists with quantities
            - **Chat history**: Keep track of your recipe searches
            - **Copy ingredients**: Easy copy-paste for shopping lists
            
            ### ⚠️ Limitations
            
            - Recipe detection accuracy depends on webpage structure
            - Some recipe formats may not be fully supported
            - Knowledge base searches are limited to stored recipes
            - Local URLs (localhost) are blocked for security
            """)
        
        with st.expander("🔧 Troubleshooting", expanded=False):
            st.markdown("""
            ### Common Issues
            
            **"AWS not configured"**
            - Check your `.env` file has correct AWS credentials
            - Verify AWS region is set correctly
            
            **"Services not initialized"**
            - Restart the application
            - Check all dependencies are installed
            
            **"Analysis failed"**
            - Check if the URL is accessible
            - Try a different recipe website
            - Check your internet connection
            
            **"No recipe detected"**
            - The webpage might not contain a recipe
            - Try a more popular recipe website
            - Check if the page has clear ingredient lists
            
            ### Need Help?
            
            If you continue to experience issues:
            1. Check the sidebar for configuration status
            2. View error details in the chat history
            3. Check application logs for detailed error information
            """)
    
    def run(self):
        """Run the main application."""
        # Initialize services
        services_ok = self.initialize_services()
        
        # Render UI components
        self.render_header()
        self.render_sidebar()
        
        if services_ok:
            self.render_main_interface()
        else:
            st.error("❌ Unable to initialize services. Please check your configuration.")
            st.info("Check the sidebar for configuration details.")
        
        # Help section
        self.render_help_section()


def main():
    """Main application entry point."""
    try:
        app = RecipeAnalyzerApp()
        app.run()
    except Exception as e:
        st.error(f"❌ Application error: {str(e)}")
        st.info("Please refresh the page or check your configuration.")


if __name__ == "__main__":
    main()