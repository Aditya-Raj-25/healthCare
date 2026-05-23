import structlog
import json
from groq import AsyncGroq
from app.core.config import settings
from app.voice.connection_manager import manager
from app.tools.appointments import book_appointment, reschedule_appointment, cancel_appointment

logger = structlog.get_logger(__name__)

# Initialize the Groq client if an API key is available
client = None
if settings.GROQ_API_KEY:
    try:
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    except Exception as e:
        logger.error("Failed to initialize Groq client", error=str(e))

# In-memory chat history mapping session_id to a list of messages
chat_histories = {}

SYSTEM_INSTRUCTION = (
    "You are a gentle, empathetic, and highly efficient medical receptionist AI. "
    "Your primary goal is to help patients book medical appointments and manage their healthcare needs. "
    "A user is speaking to you via voice. "
    "Respond with exceptional empathy and kindness. Keep your answers conversational and concise (since they will be read aloud). "
    "To successfully book an appointment, you MUST politely ask for and collect the following details from the patient: "
    "1. Their full name "
    "2. Their age "
    "3. Their phone number "
    "4. Their symptoms or reason for the visit "
    "Do not ask for everything all at once. Ask for these details naturally during the conversation. "
    "Once you have collected the required details, AND the user agrees to a specific date and time, trigger the `book_appointment` tool. "
    "If the user wants to cancel or reschedule, trigger the respective tools. "
    "Do not provide definitive medical diagnoses. Instead, focus on gathering this information to schedule them with a doctor. "
    "CRITICAL: You must respond in the exact SAME language the user speaks to you (English, Hindi, or Tamil). "
    "If they speak Hindi, reply in Hindi. If they speak Tamil, reply in Tamil."
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Books a new medical appointment for a patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string", "description": "Full name of the patient"},
                    "date": {"type": "string", "description": "Date of appointment in YYYY-MM-DD format (e.g. 2026-05-24)"},
                    "time": {"type": "string", "description": "Time of appointment in HH:MM format (e.g. 14:30)"},
                    "patient_age": {"type": "integer"},
                    "patient_phone": {"type": "string"},
                    "symptoms": {"type": "string"}
                },
                "required": ["patient_name", "date", "time", "patient_age", "patient_phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_appointment",
            "description": "Reschedules an existing appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string", "description": "The unique appointment ID to reschedule"},
                    "new_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "new_time": {"type": "string", "description": "HH:MM"}
                },
                "required": ["appointment_id", "new_date", "new_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancels an existing appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string", "description": "The unique appointment ID to cancel"}
                },
                "required": ["appointment_id"]
            }
        }
    }
]

async def process_transcript_with_llm(session_id: str, transcript: str, language: str = "en-US"):
    """
    Takes the final transcript from the user, sends it to the LLM with context,
    handles tool execution if requested, and sends the final response back down the websocket.
    """
    if not client:
        logger.warning("Groq client not initialized. Cannot process transcript.", session_id=session_id)
        await manager.send_personal_message(
            json.dumps({"event_type": "ai_response", "message": "AI is not configured. Missing API key."}),
            session_id
        )
        return

    logger.info("Sending transcript to LLM", session_id=session_id, transcript=transcript, language=language)

    # Convert language code to language name for strict enforcement
    lang_map = {"en-US": "English", "hi": "Hindi", "ta": "Tamil"}
    target_language = lang_map.get(language, "English")

    # Initialize history for this session if it doesn't exist
    if session_id not in chat_histories:
        chat_histories[session_id] = [
            {"role": "system", "content": SYSTEM_INSTRUCTION}
        ]

    history = chat_histories[session_id]
    
    # Strictly enforce language on every turn to prevent hallucination
    enforcement_prompt = f"USER TRANSCRIPT: {transcript}\n\n[SYSTEM DIRECTIVE: You MUST respond in {target_language}. Do not use any other language.]"
    history.append({"role": "user", "content": enforcement_prompt})

    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=history,
            max_tokens=256,
            temperature=0.7,
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        
        if response_message.tool_calls:
            # Append the tool call to history
            history.append(response_message)
            
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                logger.info("LLM called tool", function_name=function_name, arguments=arguments)
                
                tool_output = "Error: Tool execution failed."
                
                try:
                    if function_name == "book_appointment":
                        tool_output = await book_appointment(session_id=session_id, **arguments)
                    elif function_name == "reschedule_appointment":
                        tool_output = await reschedule_appointment(session_id=session_id, **arguments)
                    elif function_name == "cancel_appointment":
                        tool_output = await cancel_appointment(session_id=session_id, **arguments)
                except Exception as e:
                    logger.error("Tool execution failed", error=str(e))
                    tool_output = f"Error: {str(e)}"
                
                # Append tool result to history
                history.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_output
                })
            
            # Second call to get the final response based on tool execution
            second_response = await client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=history,
                max_tokens=256,
                temperature=0.7
            )
            ai_text = second_response.choices[0].message.content
            history.append({"role": "assistant", "content": ai_text})
        else:
            ai_text = response_message.content
            history.append({"role": "assistant", "content": ai_text})
        
        logger.info("LLM response generated", session_id=session_id, response=ai_text)
        
        # Send the response back to the client
        await manager.send_personal_message(
            json.dumps({"event_type": "ai_response", "message": ai_text}),
            session_id
        )

    except Exception as e:
        logger.error("Error generating LLM response", session_id=session_id, error=str(e))
        await manager.send_personal_message(
            json.dumps({"event_type": "ai_response", "message": "Sorry, I encountered an error processing your request."}),
            session_id
        )
