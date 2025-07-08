# chatbot_agents.py (Fixed and Synced with mtl_api.py)

import os
import requests
import base64
from PIL import Image
from dotenv import load_dotenv
import tempfile # New import for temporary files
import shutil   # New import for shutil.copyfile

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain.tools import BaseTool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()

# --- 1. Define Custom Tool ---
from typing import ClassVar

class MTLImagePredictionTool(BaseTool):
    name: str = "mtl_image_prediction"
    # IMPORTANT: Description now tells the LLM to expect a FILE PATH
    description: str = "Useful for predicting fruit type, ripeness, and disease from a plant image. Input should be the full path to the image file (e.g., 'C:/temp/image.jpg'). This tool will read the image from the path, convert it to base64, and send it for prediction."

    mtl_api_url: ClassVar[str] = 'http://localhost:5001/predict_image'

    def _run(self, image_path: str) -> str: # Tool now accepts a file path string
        """Use the tool."""
        try:
            # Step 1: Read the image file from the provided path
            if not os.path.exists(image_path):
                return f"Error: Image file not found at path: {image_path}"

            with open(image_path, "rb") as img_file:
                img_bytes = img_file.read()

            # Step 2: Encode the raw image bytes to base64 within the tool
            image_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # Debugging print to confirm full base64 length from *within* the tool
            print(f"DEBUG (Tool): Full base64 string length being sent to API: {len(image_base64)} characters")

            # Step 3: Send the base64 string to the MTL API
            response = requests.post(
                self.mtl_api_url,
                json={"image_base64": image_base64},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            
            return (f"Predictions:\nFruit: {data.get('fruit', 'N/A')}\n"
                    f"Ripeness: {data.get('ripeness', 'N/A')}\n"
                    f"Disease: {data.get('disease', 'N/A')}")
        
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to the prediction API. Is it running?"
        except requests.exceptions.HTTPError as http_err:
            return f"Error from MTL tool (HTTP): {http_err} - {http_err.response.text}"
        except Exception as e:
            return f"An unexpected error occurred in MTL tool: {e}"

    async def _arun(self, image_path: str):
        raise NotImplementedError("Async not supported.")

# --- 2. Wikipedia Tool ---
wikipedia_tool = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())

# --- 3. Load LLM ---
try:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    print("Gemini model loaded.")
except Exception as e:
    print(f"Error loading Gemini: {e}")
    llm = None

# --- 4. Tools ---
tools = [MTLImagePredictionTool(), wikipedia_tool]

# --- 5. Prompt Template ---
prompt_template = PromptTemplate(
    input_variables=["input", "tool_names", "tools", "agent_scratchpad"],
    template="""
You are a highly specialized plant care assistant. Your primary goal is to help users by identifying plant issues, determining ripeness, or providing general plant information.

Here are the tools you have access to:
{tool_names}

Tool Descriptions:
{tools}

**Crucial Instruction:**
When the user provides an image for analysis, it will be made available as a local file. You will be explicitly told the path to this image. **If the user asks for image analysis or prediction and provides an image path, you MUST use the `mtl_image_prediction` tool with the provided file path as its exact input.** Do NOT try to interpret the image yourself or ask for URLs.

Your thought process should strictly follow this format:

Thought: You should always think about what to do.
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
{agent_scratchpad}
"""
)

# --- 6. Agent Setup ---
if llm:
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt_template
    )

    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
else:
    agent_executor = None

# --- 7. Chat Function ---
def run_chatbot(user_text: str, image_path: str = None) -> str:
    if agent_executor is None:
        return "Chatbot is not ready. Check Gemini and API key setup."

    full_input_for_agent = user_text
    
    # If an image path is provided (from the main script)
    if image_path:
        # Instead of embedding base64, we tell the LLM about the file path
        # This is where the image_path is introduced to the LLM's context
        full_input_for_agent = f"{user_text} The image to analyze is located at: {image_path}"
        print(f"DEBUG: Instructing agent to analyze image at: {image_path}")

    try:
        result = agent_executor.invoke({"input": full_input_for_agent})
        return result.get("output", "No response from agent.")
    except Exception as e:
        return f"Error running chatbot: {e}"

# --- 8. Example Usage ---
'''
if __name__ == "__main__":
    if agent_executor:
        try:
            # Define the actual image path
            actual_image_path = "C:/Users/USER/Downloads/fyp project chatbot/76.jpg"

            # Create a temporary directory to copy the image to
            # This simulates a user "uploading" an image that the agent can then access.
            # Using a temp directory ensures the path is clean and avoids any
            # potential permission issues with the original Downloads folder path for the LLM.
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_image_name = os.path.basename(actual_image_path)
                # Create a simple, predictable temporary path that the LLM can see
                # We'll just use a direct copy, assuming `76.jpg` is a valid image.
                temp_image_full_path = os.path.join(temp_dir, temp_image_name)
                shutil.copyfile(actual_image_path, temp_image_full_path)
                
                print(f"DEBUG: Original image copied to temporary path: {temp_image_full_path}")

                print("\n--- Image Prediction ---")
                # Now pass the *temporary file path* to run_chatbot
                print(run_chatbot("Analyze this plant image.", image_path=temp_image_full_path))

            print("\n--- General Question ---")
            print(run_chatbot("What is powdery mildew?"))

            print("\n--- No Tool Needed ---")
            print(run_chatbot("Hello! How are you?"))

        except Exception as e:
            print(f"Error in test run: {e}")
    else:
        print("Agent not ready.")'''