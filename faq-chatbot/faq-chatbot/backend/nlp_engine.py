from google import genai
import os
# We no longer need the hardcoded FAQ list because the AI knows the answers!
FAQ_DATA = []

class FAQEngine:
    def __init__(self, faq_data=None):
        # Initialize the new Gemini client
        # Replace YOUR_API_KEY_HERE with your actual key (keep the quotes)
        self.client = genai.Client(
        API_KEY = os.getenv("GOOGLE_API_KEY"))

    def get_answer(self, query: str):
        # This prompt gives the AI its personality and instructions
        prompt = f"""
        You are a highly advanced Windows desktop assistant and an expert programmer.
        The user is interacting with you from a floating desktop widget.
        
        If they ask about Windows settings (like "where is the control panel"), give them direct, step-by-step navigation instructions.
        If they paste a VS Code or programming error, explain what the error means and provide the exact code to fix it.
        Keep your answers concise, formatting code in markdown where appropriate.
        
        User Query: {query}
        """
        
        try:
            # Generate the response using the new SDK syntax
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            answer = response.text
            
            # app.py expects a tuple of (answer, score, matched_question, category)
            return answer, 1.0, "Live AI Generation", "AI Assistant"
            
        except Exception as e:
            # If your internet drops or the API key is wrong, it will tell you gracefully
            error_message = f"**Connection Error:** I couldn't reach the AI brain.\n`{str(e)}`\n\nDid you paste your API key correctly?"
            return error_message, 0.0, "Error", "Error"