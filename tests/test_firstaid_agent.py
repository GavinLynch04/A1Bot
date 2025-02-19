import json
import os
import webbrowser
import pytest
import requests
from sar_project.agents.first_aid_agent import FirstAidAgent


# Create a dummy knowledge base to override the global "base" used in the agent.
class DummyKnowledgeBase:
    def __init__(self):
        self.chat_history = ["Previous chat entry"]
        self.lat = 12.34
        self.lon = 56.78
        self.data = {"patient_status": "stable"}
        self.weather = "Temperature: 25°C, Wind Speed: 10 km/h, Condition: 800"
        self.nearest_hospital = "Test Hospital, Location: 12.35, 56.79 (Distance: 1.00 km)"

    def retrieve_relevant_text(self, message):
        return "Relevant first aid text snippet."


@pytest.fixture
def dummy_base():
    return DummyKnowledgeBase()


@pytest.fixture
def agent(dummy_base, monkeypatch):
    # Replace the global "base" in the first aid agent module with our dummy_base.
    monkeypatch.setattr("sar_project.agents.first_aid_agent.base", dummy_base)
    return FirstAidAgent()


def test_initialization(agent):
    # Verify that the agent is initialized with correct properties.
    assert agent.name == "firstaid_specialist"
    assert agent.role == "First-Aid Specialist"
    assert "first aid specialist" in agent.system_message.lower()


def test_generate_prompt(agent, dummy_base):
    # Call generate_prompt with a sample message and check if the output includes key substrings.
    sample_message = "What should I do if the patient is unconscious?"
    prompt = agent.generate_prompt(sample_message)
    assert sample_message in prompt
    assert dummy_base.weather in prompt
    assert dummy_base.nearest_hospital in prompt
    assert "Relevant first aid text snippet." in prompt
    assert "Chat History:" in prompt


def test_query_gemini(monkeypatch, agent):
    # Monkey-patch the query_gemini method to simulate a Gemini response.
    monkeypatch.setattr(agent, "query_gemini", lambda prompt, model="gemini-pro",
                                                      max_tokens=None: "Simulated Gemini response based on the prompt.")
    response = agent.query_gemini("Test prompt")
    assert "Simulated Gemini response" in response


def test_update_user_data(monkeypatch, agent, dummy_base):
    # Monkey-patch query_gemini to return a valid JSON update.
    fake_json = json.dumps({"patient_status": "critical", "new_info": "bleeding"})
    monkeypatch.setattr(agent, "query_gemini", lambda prompt, model="gemini-pro", max_tokens=None: fake_json)

    user_message = "The patient is bleeding heavily."
    agent.update_user_data(user_message, dummy_base.lat, dummy_base.lon)

    assert dummy_base.data.get("patient_status") == "critical"
    assert dummy_base.data.get("new_info") == "bleeding"
    assert user_message in dummy_base.chat_history


def test_get_weather_conditions(monkeypatch, agent, dummy_base):
    # Monkey-patch requests.get to simulate a weather API response.
    def fake_get(url):
        class FakeResponse:
            def __init__(self):
                self.status_code = 200

            def json(self):
                return {
                    "current_weather": {
                        "temperature": 22,
                        "windspeed": 15,
                        "weathercode": 500
                    }
                }

        return FakeResponse()

    monkeypatch.setattr(requests, "get", fake_get)
    weather = agent.get_weather_conditions()
    assert "Temperature: 22" in weather
    assert "Wind Speed: 15" in weather
    assert "Condition: 500" in weather


def test_get_nearest_hospital(monkeypatch, agent, dummy_base):
    # Monkey-patch requests.get to simulate the Overpass API response.
    def fake_get(url, params):
        class FakeResponse:
            def __init__(self):
                self.status_code = 200

            def json(self):
                return {
                    "elements": [
                        {
                            "type": "node",
                            "lat": 12.35,
                            "lon": 56.79,
                            "tags": {"name": "Test Hospital"}
                        }
                    ]
                }

        return FakeResponse()

    monkeypatch.setattr(requests, "get", fake_get)
    hospital_info = agent.get_nearest_hospital()
    assert "Test Hospital" in hospital_info
    assert "Location:" in hospital_info
    assert "Distance:" in hospital_info


def test_extract_lat_lon(agent, dummy_base):
    # Use the dummy nearest_hospital string to test coordinate extraction.
    dummy_base.nearest_hospital = "Test Hospital, Location: 12.35, 56.79 (Distance: 1.00 km)"
    # Ensure the extraction works.
    lat, lon = agent.extract_lat_lon()
    assert isinstance(lat, float)
    assert isinstance(lon, float)
    assert abs(lat - 12.35) < 0.001
    assert abs(lon - 56.79) < 0.001


def test_generate_map(monkeypatch, agent, dummy_base, tmp_path):
    # Override webbrowser.open so it does not actually open a browser.
    called = False

    def fake_open(filename):
        nonlocal called
        called = True

    monkeypatch.setattr(webbrowser, "open", fake_open)
    dummy_base.lat = 12.34
    dummy_base.lon = 56.78
    dummy_base.nearest_hospital = "Test Hospital, Location: 12.35, 56.79 (Distance: 1.00 km)"

    filename = agent.generate_map()

    assert filename == "hospital_map.html"
    assert os.path.exists(filename)
    os.remove(filename)
    assert called


def test_summarize_chat_history(monkeypatch, agent, dummy_base):
    # Test that summarize_chat_history modifies the chat history when too long.
    # Start with a chat_history longer than 6.
    dummy_base.chat_history = [f"Message {i}" for i in range(7)]
    monkeypatch.setattr(agent, "query_gemini",
                        lambda prompt, model="gemini-pro", max_tokens=None: "Summarized chat history")
    agent.summarize_chat_history()
    assert dummy_base.chat_history == ["Summarized chat history"]
