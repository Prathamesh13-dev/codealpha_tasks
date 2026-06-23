import customtkinter as ctk
import keyboard
import threading
from backend.nlp_engine import FAQEngine

# Initialize the AI Engine
ai_engine = FAQEngine()

# ══════════════════════════════════════════════════════════════════════════════
#  UI SETUP
# ══════════════════════════════════════════════════════════════════════════════
ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.title("AI Desktop Assistant")
app.geometry("400x500")

# This is the magic line that forces the window to stay on top of VS Code/Windows
app.attributes("-topmost", True)

# Create a Chat Output Box
chat_box = ctk.CTkTextbox(app, width=380, height=390, wrap="word")
chat_box.pack(pady=10, padx=10)
chat_box.insert("end", "🤖 Assistant: Ready! Press Ctrl+Alt+Space to hide/show me.\n\n")
chat_box.configure(state="disabled") # Make it read-only

# ══════════════════════════════════════════════════════════════════════════════
#  APP LOGIC
# ══════════════════════════════════════════════════════════════════════════════
def send_message(event=None):
    user_text = input_field.get()
    if not user_text.strip():
        return
        
    # Clear input box and show user message
    input_field.delete(0, "end")
    chat_box.configure(state="normal")
    chat_box.insert("end", f"You: {user_text}\n\n")
    chat_box.see("end") # Scroll to bottom
    chat_box.configure(state="disabled")
    
    # Get AI response
    answer, score, matched_q, category = ai_engine.get_answer(user_text)
    
    # Show AI response
    chat_box.configure(state="normal")
    chat_box.insert("end", f"🤖 AI: {answer}\n\n{'─'*40}\n\n")
    chat_box.see("end")
    chat_box.configure(state="disabled")

# ══════════════════════════════════════════════════════════════════════════════
#  INPUT AREA (Text Box + Button)
# ══════════════════════════════════════════════════════════════════════════════
# Create a frame to hold the input field and button side-by-side
input_frame = ctk.CTkFrame(app, fg_color="transparent")
input_frame.pack(pady=5, padx=10, fill="x")

# Create the Input Field inside the frame
input_field = ctk.CTkEntry(input_frame, width=300, placeholder_text="Ask a question or paste an error...")
input_field.pack(side="left", padx=(0, 10))

# Create the Send Button inside the frame
send_btn = ctk.CTkButton(input_frame, text="Send", width=70, command=send_message)
send_btn.pack(side="right")

# Bind the Enter key so you can STILL use your keyboard
app.bind('<Return>', send_message)

# ══════════════════════════════════════════════════════════════════════════════
#  HOTKEY POPUP LOGIC (Updated for Thread Safety)
# ══════════════════════════════════════════════════════════════════════════════
is_visible = True

def toggle_window():
    global is_visible
    if is_visible:
        app.withdraw() # Hides the window entirely
        is_visible = False
    else:
        app.deiconify() # Brings the window back
        is_visible = True

def safe_toggle():
    # This safely bridges the keyboard background thread to the main GUI thread
    app.after(0, toggle_window)

# Listen for the hotkey in the background and trigger the safe bridge
keyboard.add_hotkey('alt+q', safe_toggle)

# Start the application
if __name__ == "__main__":
    app.mainloop()