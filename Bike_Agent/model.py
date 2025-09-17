from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

model = ChatGoogleGenerativeAI(model='gemini-2.5-flash')

parser = StrOutputParser()

yes_detection_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""
You are a helpful assistant.

Determine if the user's most recent message is an affirmative confirmation such as:
- 'yes'
- 'yeah'
- 'yup'
- 'uh-huh'
- 'sure'
- 'definitely'
- 'of course'
- 'okay'
- or similar.

Return ONLY 'True' if the message clearly means yes.
Return ONLY 'False' if it does NOT clearly mean yes.

Do NOT return anything else. Only output 'True' or 'False'.
    """),
    MessagesPlaceholder(variable_name="messages")
])

summarize_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""You are a conversation summarizer for a university admission assistant. 
    Your task is to concisely summarize the key information from the AI's response while:
    1. Maintaining a natural, conversational tone
    2. Preserving all critical details (requirements, deadlines, processes)
    3. Keeping it under 80 words
    4. Removing any redundant phrases like 'based on the document'
    5. Formatting lists clearly when present
    
    Speak directly to the user (use "you" instead of "the applicant").
    """),
    MessagesPlaceholder(variable_name="messages"),
])

bye_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""
        Analyze the user's message and determine if they want to end the conversation.
        Respond with ONLY 'True' if the message clearly indicates ending the conversation
        (e.g., 'bye', 'goodbye', 'that's all', 'thank you', 'end chat', etc.).
        Respond with ONLY 'False' if the message doesn't indicate ending the conversation.
        Do not add any explanations or other text.
        """),
    MessagesPlaceholder(variable_name="messages"),
])

admission_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""
        Analyze the user's message and **strictly** determine if they are expressing **only initial intent** to start admission.  
        **Only return 'True' if the message is a direct request to begin admission (no follow-up questions).**  

        **Examples of 'True':**  
        - "I want to take admission."  
        - "I want to apply for B.Tech."  
        - "Sign me up for the course."  

        **Examples of 'False':**  
        - "What is the admission process?" (→ handled by another model)  
        - "How do I apply?" (→ handled by another model)  
        - "I want to take admission. What’s next?" (→ `False`, because it asks for process)  
        - "Can you give me the contact number?" (→ `False`, not direct intent)  

        **Only return 'True' or 'False'—no explanations.**   
        """),
    MessagesPlaceholder(variable_name="messages"),
])

language_detection_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""
        Analyze the user's message to identify the language it is written in.

        **Strictly return ONLY the corresponding Google TTS language code** as per the following mapping:
        
        - Hindi -> hi-IN
        - Gujarati -> gu-IN
        - English -> en-US
        - French -> fr-FR
        - Spanish -> es-ES

        Do not include any explanations, greetings, or other text.

        ---
        **Examples:**
        
        - **User Input:** "Hello, I would like to know more about your services."
        - **Your Output:** en-US

        - **User Input:** "नमस्ते, आप कैसे हैं?"
        - **Your Output:** hi-IN
                  
        - **User Input:** "Mujhe admission lena hai."
        - **Your Output:** hi-IN
                  
        - **User Input:** "Mare admission levu che"
        - **Your Output:** gu-IN
        
        - **User Input:** "કેમ છો?"
        - **Your Output:** gu-IN
        ---
    """),
    MessagesPlaceholder(variable_name="messages"),
])

yes_chain = yes_detection_prompt | model | parser       
summarize_chain = summarize_prompt | model | parser
bye_chain = bye_prompt | model | parser
admission_chain = admission_prompt | model | parser
language_detection_chain = language_detection_prompt | model  | parser

date_extraction_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""
You are a helpful assistant.

Extract the date or dates mentioned in the user's message. 
The user may speak in English, Hindi, or a mix of both.
Return ONLY the date(s) in a standard, unambiguous format (YYYY-MM-DD if possible).
If multiple dates are present, return them as a comma-separated list.
If no date is found, return "None".

Do NOT return any explanations or extra text.

---
Examples:

- User: "Can you reschedule my appointment to 5th September 2025?"
- Output: 2025-09-05

- User: "I am available on 12/10/2025 or 15/10/2025."
- Output: 2025-10-12, 2025-10-15

- User: "चलो अगले सोमवार को करते हैं।"
- Output: [Return the date for next Monday in YYYY-MM-DD format]

- User: "कोई तारीख नहीं चाहिए।"
- Output: None
---
"""),
    MessagesPlaceholder(variable_name="messages"),
])

date_extraction_chain = date_extraction_prompt | model | parser

def extract_dates(text):
    try:
        messages = [HumanMessage(content=text)]
        result = date_extraction_chain.invoke({"messages": messages})
        return result.strip()
    except Exception as e:
        print(f"Error extracting dates: {e}")
        return "None"

def is_yes(text):
    try:
        # Create the message structure
        messages = [
            HumanMessage(content=f"check:\n\n{text}")
        ]
        
        # Invoke the chain with the messages
        result = yes_chain.invoke({"messages": messages})
        return result.strip().lower() == 'true'
    except Exception as e:
        print(f"Error checking yes: {e}")
        return False

def summarize(text):
    try:
        # Create the message structure
        messages = [
            HumanMessage(content=f"Please summarize this text:\n\n{text}")
        ]
        
        # Invoke the chain with the messages
        result = summarize_chain.invoke({"messages": messages})
        # print("Generated Summary:", result)
        return result
    except Exception as e:
        print(f"Error during summarization: {e}")
        return "Sorry, I couldn't generate a summary at this time."

def is_bye(text):
    try:
        messages = [
            HumanMessage(content=f"check:\n\n{text}")
        ]

        result = bye_chain.invoke({"messages":messages})
        return result.strip().lower() == 'true'
    except Exception as e:
        print(f"Error checking good bye: {e}")
        return False
    
def want_admission(text):
    try:
        messages = [
            HumanMessage(content=f"check:\n\n{text}")
        ]

        result = admission_chain.invoke({"messages":messages})
        return result.strip().lower() == 'true'
    except Exception as e:
        print(f"Error checking good bye: {e}")
        return False


def detect_language(text):
    try:
        messages = [
            HumanMessage(content=text)
        ]

        # Invoke the language detection chain
        result = language_detection_chain.invoke({"messages": messages})

        # The AIMessage object's content holds the language name.
        # .strip() removes any leading/trailing whitespace.
        language_name = result
        
        return language_name
        
    except Exception as e:
        print(f"An error occurred during language detection: {e}")
        return "Unknown"


def conversation_loop():
    print("Conversation started. Type 'bye' or similar to end.")
    while True:
        user_input = input("You: ")
        if is_yes(user_input):
            print("AI: Great! Let's proceed.")
        
        if is_bye(user_input):
            print("AI: Goodbye! Have a great day!")
            break
        
        if want_admission(user_input):
            print("AI: give me your number")
        # If not goodbye, proceed with summarization
        summary = summarize(user_input)
        print(f"AI Summary: {summary}")

# Example usage
if __name__ == "__main__":
    conversation_loop()