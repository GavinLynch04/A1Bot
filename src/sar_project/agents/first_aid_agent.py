import os
from sar_project.agents.base_agent import SARBaseAgent
import google.generativeai as genai
from sar_project.knowledge.knowledge_base_firstaid import KnowledgeBase
import json
from dotenv import load_dotenv
load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

class FirstAidAgent(SARBaseAgent):
    def __init__(self, name="firstaid_specialist"):
        super().__init__(
            name=name,
            role="First-Aid Specialist",
            system_message="""You are a first aid specialist for search and rescue operations. Your role is to:
            1. Understand patient condition
            2. Understand search and rescue conditions/environment
            3. Provide recommendations on first aid based on #1 and #2
            4. Monitor changing conditions
            Respond as if you are talking to a SAR personnel, give them guidence on their question. Respond to their question not to the criteria above, just adhere to it.
            User question: """
        )

    def process_request(self, message):
        """Process first-aid-related requests"""
        try:
            prompt = self.generate_prompt(message)
            return self.query_gemini(prompt)
        except Exception as e:
            return {"error": str(e)}

    def generate_prompt(self, message):
        return (self.system_message +
                message +
                "\n Below is expert guidance, use it at your discretion to formulate your response: \n" +
                base.retrieve_relevant_text(message) +
                "\n Take into account the rescuee and rescuer data (if any), as well as previous chat history (if any) below to maintain consistency." +
                str(base.data) +
                "Chat History: " + str(base.chat_history))

    def query_gemini(self, prompt, model="gemini-pro", max_tokens=None):
        """Query Google Gemini API and return response."""
        try:
            response = genai.GenerativeModel(model).generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {e}"

    #Finish this
    def update_user_data(self, message):
        prompt = (
        "Update the following JSON data based on the user message. If there is no new relevant data, leave JSON as is."
        "Return only valid JSON without any extra text.\n\n"
        "Current JSON Data:\n"
        f"{json.dumps(base.data, indent=2)}\n\n"
        "User Message:\n"
        f"{message}"
        )

        response = self.query_gemini(prompt)

        try:
            base.chat_history.append(message)
            base.data = json.loads(response)
        except json.JSONDecodeError:
            # Handle the error or log for debugging.
            raise ValueError("LLM returned invalid JSON.")

    def get_status(self):
        """Get the agent's current status"""
        return getattr(self, "status", "unknown")

if __name__ == "__main__":
    agent = FirstAidAgent()
    base = KnowledgeBase()
    while True:
        userInput = input("Enter a first-aid-related request: ")
        agent.update_user_data(userInput)
        print(agent.process_request(userInput))
