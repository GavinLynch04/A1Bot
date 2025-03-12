# First Aid Specialist Agent - CSC 581

## Insights

Beck's recommendations proved to be very helpful, and made me wonder how I did not think of them previously. He suggested changing my location identification approach from coordinates to a city lookup, which I agreed is much more user-friendly. Making users find their current coordinates, especially in a SAR scenario, could be frustrating. To solve this, I added parsing to take in either a city name or coordinates (for more accurate maps and weather). Another great idea that Beck had was to include future weather, allowing the search and rescue personnel and the bot to take changes in weather into account when giving advice. 

## Modifications
As I stated above, the two big changes that I made to the bot were to improve the location entering experience, and also improve weather lookup to include future patterns. To implement the first change, I started by finding resources that could translate from city to location (lat and lon). I came accross geopy, which worked perfectly for my situation. It allows the look up of any city, and will quickly give coordinates to go with it. From there it was a matter of dealing with the parsing of user input, which took a bit of time to get right. 
For weather, the change was fairly simple. All I needed to do was change my api call to include future weather reports as well, and this allowed me to add this to the model. I did have to change the knowledge base slightly as to help the model store and access the new information, but other than that it was an easy change.

## Introduction

This agent is built to assist search and rescue personnel in a rescue or first aid situation. It contains a RAG database with expert first aid documents that it will pull from to generate recommendations. It also has the ability to locate the current weather and the nearest hospital to SAR personnel. It can be used to inform decisions in the field on what first aid best practices are.

## Prerequisites

- Python 3.10 or higher
- pyenv (recommended for Python version management)
- pip (for dependency management)

## Setup and Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd sar-project
```

2. Set up Python environment:
```bash
# Using pyenv (recommended)
pyenv install 3.10.0  # or your preferred version
pyenv local 3.10.0

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate     # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -e .
```

4. Configure environment variables:

#### Google Gemini:
- Obtain required API keys:
  1. ``` pip install google-generativeai ```
  2. ``` import google.generativeai as genai ```
  3. Google Gemini API Key: Obtain at https://aistudio.google.com/apikey
- Configure with the following:
  ```
  genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
  ```

5. Run the agent

The first aid agent file in the agent's folder needs to be run in order to converse with the chatbot. From there it will remember chat history and give recommendations.

## Project Structure

```
sar-project/
├── src/
│   └── sar_project/         # Main package directory
│       └── agents/          # Agent implementations
│       └── config/          # Configuration and settings
│       └── knowledge/       # Knowledge base implementations
├── tests/                   # Test directory
├── pyproject.toml           # Project metadata and build configuration
├── requirements.txt         # Project dependencies
└── .env                     # Environment configuration
```

## Development

This project follows modern Python development practices:

1. Source code is organized in the `src/sar_project` layout
2. Use `pip install -e .` for development installation
3. Run tests with `pytest`
