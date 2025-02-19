import os
import requests
from sar_project.agents.base_agent import SARBaseAgent
import google.generativeai as genai
from sar_project.knowledge.knowledge_base_firstaid import KnowledgeBase
import json
import re
import folium
from folium.plugins import AntPath
from math import radians, cos, sin, sqrt, atan2
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

    def summarize_chat_history(self):
        """Summarize chat history to keep context without excessive length."""
        if len(base.chat_history) > 6:
            summary_prompt = (
                "Summarize the following chat history while keeping all relevant first-aid and rescue details:\n\n"
                f"{json.dumps(base.chat_history, indent=2)}"
                "\nReturn only a concise summary."
            )
            summary = self.query_gemini(summary_prompt)
            base.chat_history = [summary]

    def get_weather_conditions(self):
        """Fetch current weather from Open-Meteo API"""
        url = f"https://api.open-meteo.com/v1/forecast?latitude={base.lat}&longitude={base.lon}&current_weather=true"
        response = requests.get(url)
        data = response.json()

        if "current_weather" in data:
            weather = data["current_weather"]
            return f"Temperature: {weather['temperature']}°C, Wind Speed: {weather['windspeed']} km/h, Condition: {weather['weathercode']}"

        return "Weather data not available."

    def generate_prompt(self, message):
        """Generates a full prompt to send to Gemini"""
        return (self.system_message +
                message +
                "\n Below is expert guidance, use it at your discretion to formulate your response: \n" +
                base.retrieve_relevant_text(message) +
                "\n Below is current weather conditions: \n" +
                base.weather +
                "\n Below is the closest hospital: \n" +
                base.nearest_hospital +
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

    def update_user_data(self, message, lat, lon):
        prompt = (
        "Update the following JSON data based on the user message. If there is no new relevant data, leave JSON as is. Never delete data, only add on."
        "Return only valid JSON without any extra text.\n\n"
        "Current JSON Data:\n"
        f"{json.dumps(base.data, indent=2)}\n\n"
        "User Message:\n"
        f"{message}"
        )

        response = self.query_gemini(prompt)
        previous_data = base.data
        base.chat_history.append(message)
        base.lat = float(lat)
        base.lon = float(lon)

        try:
            base.data = json.loads(response)
        except json.JSONDecodeError:
            base.data = previous_data
            return
        except Exception as e:
            return f"Error: {e}"

    import requests

    def get_nearest_hospital(self):
        """Find the nearest hospital using OpenStreetMap's Overpass API"""
        query = f"""
            [out:json][timeout:25];
            nwr(around:10000,{base.lat},{base.lon})["amenity"="hospital"];
            out center;
            """

        url = "https://overpass-api.de/api/interpreter"
        response = requests.get(url, params={"data": query})
        if response.status_code != 200:
            return f"Error: Received status code {response.status_code}"

        data = response.json()

        # If no hospitals are found, return
        if "elements" not in data or not data["elements"]:
            return "No hospital found nearby."

        # Function to calculate haversine distance
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            return R * c  # Distance in km

        # List to store hospitals with distances
        hospitals = []

        for hospital in data["elements"]:
            if hospital["type"] == "node":
                h_lat = hospital.get("lat")
                h_lon = hospital.get("lon")
            elif hospital["type"] == "way" and "center" in hospital:
                h_lat = hospital["center"].get("lat")
                h_lon = hospital["center"].get("lon")
            else:
                continue

            if h_lat and h_lon:
                distance = haversine(float(base.lat), float(base.lon), float(h_lat), float(h_lon))
                name = hospital.get("tags", {}).get("name", "Unknown Hospital")
                hospitals.append((name, h_lat, h_lon, distance))

        # Sort hospitals by distance (ascending)
        hospitals.sort(key=lambda x: x[3])

        # Get the nearest hospital
        nearest_hospital = hospitals[0]
        name, lat, lon, distance = nearest_hospital

        return f"{name}, Location: {lat}, {lon} (Distance: {distance:.2f} km)"

    def extract_lat_lon(self):
        """Extract latitude and longitude from the hospital data string."""
        match = re.search(r"Location:\s*(-?\d+\.\d+),\s*(-?\d+\.\d+)", base.nearest_hospital)
        if match:
            lat, lon = map(float, match.groups())
            return lat, lon
        return None, None  # Return None if parsing fails

    def generate_map(self):
        """Generate a map with the nearest hospital and user's location marked, including a path between them."""
        hospital_lat, hospital_lon = self.extract_lat_lon()

        if hospital_lat is None or hospital_lon is None:
            print("Error: Could not extract coordinates from hospital data.")
            return None

        # Create a map centered at the midpoint between the user and the hospital
        midpoint_lat = (base.lat + hospital_lat) / 2
        midpoint_lon = (base.lon + hospital_lon) / 2
        hospital_map = folium.Map(location=[midpoint_lat, midpoint_lon], zoom_start=12)

        # Add a marker for the user's location
        folium.Marker(
            [base.lat, base.lon],
            popup="Your Location",
            tooltip="You are here",
            icon=folium.Icon(color="blue", icon="home")
        ).add_to(hospital_map)

        # Add a marker for the hospital's location
        folium.Marker(
            [hospital_lat, hospital_lon],
            popup="Nearest Hospital",
            tooltip="Click for details",
            icon=folium.Icon(color="red", icon="plus-sign")
        ).add_to(hospital_map)

        # Add a path (polyline) between the two points
        AntPath(
            locations=[[base.lat, base.lon], [hospital_lat, hospital_lon]],
            delay=1000, color="green", weight=4
        ).add_to(hospital_map)

        # Save the map to an HTML file and return it
        map_filename = "hospital_map.html"
        hospital_map.save(map_filename)
        print(f"Map generated: {map_filename}")

        return map_filename  # Return the filename to be used in the app


if __name__ == "__main__":
    agent = FirstAidAgent()
    base = KnowledgeBase()
    print("Enter lat and lon coordinates below for weather conditions and other features.")
    lat = input("Enter latitude (or leave blank): ")
    lon = input("Enter longitude (or leave blank): ")
    i=0
    while True:
        userInput = input("Enter a first-aid-related request: ")
        agent.update_user_data(userInput, lat, lon)
        if lat and lon and i==0:
            base.weather = agent.get_weather_conditions()
            base.nearest_hospital = agent.get_nearest_hospital()
            i+=1

        agent.summarize_chat_history()
        print(agent.process_request(userInput))
        agent.generate_map()
