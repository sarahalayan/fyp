# utils/chatbot_agents.py 

import os
import requests
import base64
from PIL import Image
from dotenv import load_dotenv
import tempfile
import shutil
from datetime import datetime, timedelta

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain.tools import BaseTool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_google_genai import ChatGoogleGenerativeAI

from typing import ClassVar, Any, Dict, List, Optional, Union

# Load environment variables
load_dotenv()

# --- 1. Define Custom Tool (MTL Image Prediction) ---
class MTLImagePredictionTool(BaseTool):
    name: str = "mtl_image_prediction"
    description: str = "Useful for predicting fruit type, ripeness, and disease from a plant image. Input should be the full path to the image file (e.g., 'C:/temp/image.jpg'). This tool will read the image from the path, convert it to base64, and send it for prediction."

    mtl_api_url: ClassVar[str] = 'http://localhost:5001/predict_image'

    def _run(self, image_path: str) -> str:
        """Use the tool."""
        try:
            if not os.path.exists(image_path):
                return f"Error: Image file not found at path: {image_path}"

            with open(image_path, "rb") as img_file:
                img_bytes = img_file.read()

            image_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            print(f"DEBUG (Tool): Full base64 string length being sent to MTL API: {len(image_base64)} characters")

            response = requests.post(
                self.mtl_api_url,
                json={"image_base64": image_base64},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
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

# --- Monitoring Status Tool ---
class MonitorStatusTool(BaseTool):
    name: str = "get_monitoring_status"
    description: str = "Useful for checking the current status of the automated video monitoring system. It tells you if monitoring is active and which video file is being processed. Input should always be 'none'."

    monitor_api_url: ClassVar[str] = 'http://localhost:5002/api/monitoring/status'

    def _run(self, query: str = "none") -> str:
        """Use the tool to get monitoring status."""
        try:
            response = requests.get(self.monitor_api_url)
            response.raise_for_status()
            status_data = response.json()
            
            is_active = status_data.get('is_active', False)
            video_file = status_data.get('current_video_file', 'N/A')
            status_message = "active" if is_active else "inactive"

            return f"Monitoring Status: {status_message}. Currently processing video: {video_file}."
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to the monitoring API. Is it running on port 5002?"
        except requests.exceptions.RequestException as e:
            return f"Error from monitoring status tool: {e} - {e.response.text if e.response else ''}"
        except Exception as e:
            return f"An unexpected error occurred in monitoring status tool: {e}"

    async def _arun(self, query: str = "none"):
        raise NotImplementedError("Async not supported.")

# --- Get Recent Detections Tool ---
class MonitorDetectionsTool(BaseTool):
    name: str = "get_recent_plant_detections"
    description: str = "Useful for retrieving a summary of recent plant, fruit, ripeness, and disease detections made by the automated video monitoring system. The detections include timestamps and confidence scores. Input should always be 'none'."

    monitor_api_url: ClassVar[str] = 'http://localhost:5002/api/monitoring/detections'

    def _run(self, query: str = "none") -> str:
        """Use the tool to get recent plant detections."""
        try:
            response = requests.get(self.monitor_api_url)
            response.raise_for_status()
            detections_data = response.json()

            if not detections_data:
                return "No recent plant detections found from the monitoring system."

            summary = []
            for det in detections_data:
                fruit = det.get('fruit_type', 'N/A')
                ripeness = det.get('ripeness', 'N/A')
                disease = det.get('disease', 'N/A')
                timestamp = det.get('timestamp', 'N/A')
                notes = det.get('notes', '')

                conf_fruit = f"({det.get('confidence_fruit'):.2f})" if det.get('confidence_fruit') is not None else ""
                conf_ripeness = f"({det.get('confidence_ripeness'):.2f})" if det.get('confidence_ripeness') is not None else ""
                conf_disease = f"({det.get('confidence_disease'):.2f})" if det.get('confidence_disease') is not None else ""

                summary.append(f"At {timestamp}: Fruit: {fruit}{conf_fruit}, Ripeness: {ripeness}{conf_ripeness}, Disease: {disease}{conf_disease}. Notes: {notes}")
            
            return "Recent Detections:\n" + "\n".join(summary)

        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to the monitoring API. Is it running on port 5002?"
        except requests.exceptions.RequestException as e:
            return f"Error from monitoring detections tool: {e} - {e.response.text if e.response else ''}"
        except Exception as e:
            return f"An unexpected error occurred in monitoring detections tool: {e}"

    async def _arun(self, query: str = "none"):
        raise NotImplementedError("Async not supported.")

# --- Get Total Detections Tool ---
class GetTotalDetectionsTool(BaseTool):
    name: str = "get_total_detections_count"
    description: str = "Useful for getting the total number of plant detections recorded in the monitoring database. Input should always be 'none'."

    monitor_api_url: ClassVar[str] = 'http://localhost:5002/api/monitoring/total_detections'

    def _run(self, query: str = "none") -> str:
        """Use the tool to get the total count of detections."""
        try:
            response = requests.get(self.monitor_api_url)
            response.raise_for_status()
            data = response.json()
            total_count = data.get('total_detections', 'N/A')
            return f"Total plant detections: {total_count}."
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to the monitoring API. Is it running on port 5002?"
        except requests.exceptions.RequestException as e:
            return f"Error from total detections tool: {e} - {e.response.text if e.response else ''}"
        except Exception as e:
            return f"An unexpected error occurred in total detections tool: {e}"

    async def _arun(self, query: str = "none"):
        raise NotImplementedError("Async not supported.")

# --- Get Detections Grouped by Fruit Tool ---
class GetDetectionsByFruitTool(BaseTool):
    name: str = "get_detections_grouped_by_fruit"
    description: str = "Useful for counting plant detections grouped by fruit type. For example, to see how many 'apple' or 'orange' detections there are. Input should always be 'none'."

    monitor_api_url: ClassVar[str] = 'http://localhost:5002/api/monitoring/detections_by_fruit'

    def _run(self, query: str = "none") -> str:
        """Use the tool to get detections grouped by fruit type."""
        try:
            response = requests.get(self.monitor_api_url)
            response.raise_for_status()
            data = response.json()

            if not data:
                return "No fruit detections found to group."
            
            fruit_counts = [f"{item['fruit_type']}: {item['count']}" for item in data]
            return "Detections by Fruit Type:\n" + "\n".join(fruit_counts)
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to the monitoring API. Is it running on port 5002?"
        except requests.exceptions.RequestException as e:
            return f"Error from detections by fruit tool: {e} - {e.response.text if e.response else ''}"
        except Exception as e:
            return f"An unexpected error occurred in detections by fruit tool: {e}"

    async def _arun(self, query: str = "none"):
        raise NotImplementedError("Async not supported.")

# --- Get Detections Grouped by Disease Tool ---
class GetDetectionsByDiseaseTool(BaseTool):
    name: str = "get_detections_grouped_by_disease"
    description: str = "Useful for counting plant detections grouped by disease type. For example, to see how many 'healthy' or 'Black_rot' detections there are. Input should always be 'none'."

    monitor_api_url: ClassVar[str] = 'http://localhost:5002/api/monitoring/detections_by_disease'

    def _run(self, query: str = "none") -> str:
        """Use the tool to get detections grouped by disease type."""
        try:
            response = requests.get(self.monitor_api_url)
            response.raise_for_status()
            data = response.json()

            if not data:
                return "No disease detections found to group."
            
            disease_counts = [f"{item['disease']}: {item['count']}" for item in data]
            return "Detections by Disease Type:\n" + "\n".join(disease_counts)
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to the monitoring API. Is it running on port 5002?"
        except requests.exceptions.RequestException as e:
            return f"Error from detections by disease tool: {e} - {e.response.text if e.response else ''}"
        except Exception as e:
            return f"An unexpected error occurred in detections by disease tool: {e}"

    async def _arun(self, query: str = "none"):
        raise NotImplementedError("Async not supported.")

# --- Get Detections In Time Range Tool ---
class GetDetectionsInTimeRangeTool(BaseTool):
    name: str = "get_detections_in_time_range"
    description: str = (
        "Useful for retrieving a detailed list of plant detections within a specific time range. "
        "The input MUST be a JSON object string (e.g., `{\"start_time\": \"YYYY-MM-DDTHH:MM:SS\", \"end_time\": \"YYYY-MM-DDTHH:MM:SS\"}`). "
        "Crucially, **DO NOT wrap the JSON object string in extra outer quotes when providing the input.** "
        "This tool is especially useful if the user asks for detections from a specific date, between two dates, or within a time period like 'yesterday' or 'last week'."
     )
    monitor_api_url: ClassVar[str] = 'http://localhost:5002/api/monitoring/detections_in_range'

    def _run(self, json_input: str) -> str:
        """
        Use the tool to get detections within a specified time range.
        Input should be a JSON string like '{"start_time": "...", "end_time": "..."}'
        """
        try:
            import json
            params = json.loads(json_input)
            start_time = params.get('start_time')
            end_time = params.get('end_time')

            if not start_time or not end_time:
                return "Error: Both 'start_time' and 'end_time' are required in the input JSON."

            # Construct the query URL
            url = f"{self.monitor_api_url}?start_time={start_time}&end_time={end_time}"
            response = requests.get(url)
            response.raise_for_status()
            detections_data = response.json()

            if not detections_data:
                return f"No plant detections found between {start_time} and {end_time}."

            summary = []
            for det in detections_data:
                fruit = det.get('fruit_type', 'N/A')
                ripeness = det.get('ripeness', 'N/A')
                disease = det.get('disease', 'N/A')
                timestamp = det.get('timestamp', 'N/A')
                notes = det.get('notes', '')

                conf_fruit = f"({det.get('confidence_fruit'):.2f})" if det.get('confidence_fruit') is not None else ""
                conf_ripeness = f"({det.get('confidence_ripeness'):.2f})" if det.get('confidence_ripeness') is not None else ""
                conf_disease = f"({det.get('confidence_disease'):.2f})" if det.get('confidence_disease') is not None else ""

                summary.append(f"At {timestamp}: Fruit: {fruit}{conf_fruit}, Ripeness: {ripeness}{conf_ripeness}, Disease: {disease}{conf_disease}. Notes: {notes}")
            
            return f"Detections between {start_time} and {end_time}:\n" + "\n".join(summary)

        except json.JSONDecodeError:
            return "Error: Invalid JSON input format. Please provide a valid JSON string for start_time and end_time."
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to the monitoring API. Is it running on port 5002?"
        except requests.exceptions.RequestException as e:
            return f"Error from time range detections tool: {e} - {e.response.text if e.response else ''}"
        except Exception as e:
            return f"An unexpected error occurred in time range detections tool: {e}"

    async def _arun(self, json_input: str):
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
tools = [
    MTLImagePredictionTool(), 
    wikipedia_tool,
    MonitorStatusTool(),
    MonitorDetectionsTool(),
    GetTotalDetectionsTool(),         
    GetDetectionsByFruitTool(),       
    GetDetectionsByDiseaseTool(),
    GetDetectionsInTimeRangeTool()    # NEW
]

# --- 5. Prompt Template ---
prompt_template = PromptTemplate(
    input_variables=["input", "tool_names", "tools", "agent_scratchpad"],
    template="""
You are a highly specialized plant care assistant. Your primary goal is to help users by identifying plant issues, determining ripeness, providing general plant information, or reporting on the automated video monitoring system.

Here are the tools you have access to:
{tool_names}

Tool Descriptions:
{tools}

**Crucial Instructions:**
1. When the user provides an image for analysis, it will be made available as a local file. You will be explicitly told the path to this image. **If the user asks for image analysis or prediction and provides an image path, you MUST use the `mtl_image_prediction` tool with the provided file path as its exact input.** Do NOT try to interpret the image yourself or ask for URLs.
2. If the user asks about the **status of the plant monitoring system** (e.g., "Is monitoring active?", "What video is being processed?"), you **MUST** use the `get_monitoring_status` tool.
3. If the user asks to **see a general summary of recent plant detections** or results from the monitoring system (e.g., "Show me the latest detections", "What fruits were detected?"), you **MUST** use the `get_recent_plant_detections` tool.
4. If the user asks for the **total count of all plant detections**, you **MUST** use the `get_total_detections_count` tool.
5. If the user asks for detections **grouped by fruit type** (e.g., "How many of each fruit have been detected?", "Group detections by fruit"), you **MUST** use the `get_detections_grouped_by_fruit` tool.
6. If the user asks for detections **grouped by disease type** (e.g., "What diseases were found and how many times?", "Group detections by disease"), you **MUST** use the `get_detections_grouped_by_disease` tool.
7. **If the user asks for detections within a specific time frame, for a particular date, or between two dates, you MUST use the `get_detections_in_time_range` tool.** You will need to parse the user's request to extract the `start_time` and `end_time` in ISO 8601 format (YYYY-MM-DDTHH:MM:SS or simpler YYYY-MM-DDTHH:MM:SS.ffffff) and provide it as a JSON string to the tool. For example, if the user asks for "detections from yesterday", you should calculate yesterday's start and end timestamps.
8. For general questions about plants or diseases not related to image analysis or monitoring detections, use the `wikipedia_query_run` tool.



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
'''def run_chatbot(user_text: str, image_path: str = None) -> str:
    if agent_executor is None:
        return "Chatbot is not ready. Check Gemini and API key setup."

    full_input_for_agent = user_text
    
    if image_path:
        full_input_for_agent = f"{user_text} The image to analyze is located at: {image_path}"
        print(f"DEBUG: Instructing agent to analyze image at: {image_path}")

    try:
        result = agent_executor.invoke({"input": full_input_for_agent})
        return result.get("output", "No response from agent.")
    except Exception as e:
        return f"Error running chatbot: {e}"
    '''
def run_chatbot(user_text: str, image_path: str = None) -> str:
    if agent_executor is None:
        return "Chatbot is not ready. Check Gemini and API key setup."

    full_input_for_agent = user_text
    
    # NEW LOGIC: Pre-process relative date queries
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    
    start_time_iso = None
    end_time_iso = None

    lower_user_text = user_text.lower()

    if "yesterday" in lower_user_text:
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_time_iso = start_time.isoformat()
        end_time_iso = end_time.isoformat()
        # Modify the user's input to explicitly include the calculated dates
        full_input_for_agent = f"detections between {start_time_iso} and {end_time_iso}"
        # Keep original query for analysis check later
        full_input_for_agent += f" (original query: '{user_text}')"
        print(f"DEBUG: Processed 'yesterday' to: {full_input_for_agent}")
    elif "today" in lower_user_text:
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_time_iso = start_time.isoformat()
        end_time_iso = end_time.isoformat()
        full_input_for_agent = f"detections between {start_time_iso} and {end_time_iso}"
        full_input_for_agent += f" (original query: '{user_text}')"
        print(f"DEBUG: Processed 'today' to: {full_input_for_agent}")
    elif "last week" in lower_user_text:
        # Assuming "last week" means the past 7 full days from today's start
        start_time = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_time_iso = start_time.isoformat()
        end_time_iso = end_time.isoformat()
        full_input_for_agent = f"detections between {start_time_iso} and {end_time_iso}"
        full_input_for_agent += f" (original query: '{user_text}')"
        print(f"DEBUG: Processed 'last week' to: {full_input_for_agent}")
    # Add more conditions for other relative time terms as needed (e.g., "this month", "last year")

    if image_path:
        full_input_for_agent = f"{full_input_for_agent}. The image to analyze is located at: {image_path}"
        print(f"DEBUG: Instructing agent to analyze image at: {image_path}")

    try:
        result = agent_executor.invoke({"input": full_input_for_agent})
        return result.get("output", "No response from agent.")
    except Exception as e:
        return f"Error running chatbot: {e}"

# --- 8. Testing example ---
'''
if __name__ == "__main__":
    if agent_executor:
        try:
            print("\n--- Monitoring Status Question ---")
            print(run_chatbot("Is the plant monitoring active?"))

            print("\n--- Recent Detections Question ---")
            print(run_chatbot("Show me the latest detections from the monitoring system."))

            print("\n--- Total Detections Question ---")
            print(run_chatbot("How many plants have been detected in total?"))

            print("\n--- Detections by Fruit Question ---")
            print(run_chatbot("Can you group the detections by fruit type?"))

            print("\n--- Detections by Disease Question ---")
            print(run_chatbot("What diseases have been detected and how many of each?"))
            
            # Test for detections in time range
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            yesterday_start = today_start - timedelta(days=1)
            yesterday_end = today_end - timedelta(days=1)

            print("\n--- Detections from yesterday ---")
            # LLM should parse this and format for the tool
            print(run_chatbot(f"Show me detections from yesterday ({yesterday_start.strftime('%Y-%m-%d')})."))

            print("\n--- Detections from last 7 days ---")
            seven_days_ago = now - timedelta(days=7)
            # LLM should parse this and format for the tool
            print(run_chatbot(f"Show detections between {seven_days_ago.strftime('%Y-%m-%d %H:%M:%S')} and {now.strftime('%Y-%m-%d %H:%M:%S')}"))

            print("\n--- General Question ---")
            print(run_chatbot("What is powdery mildew?"))

            print("\n--- No Tool Needed ---")
            print(run_chatbot("Hello! How are you?"))

        except Exception as e:
            print(f"Error in test run: {e}")
    else:
        print("Agent not ready.")
'''
