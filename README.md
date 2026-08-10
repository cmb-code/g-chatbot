# 🚗 AutoBot — AI Automobile Assistant

An intelligent chatbot for the Indian automobile industry, built with **Pydantic AI**, **Gradio**, and **Gemini API**.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🚗 **Car Recommendations** | Get personalized car suggestions based on budget, needs & preferences |
| 🔧 **Diagnostics** | Describe symptoms → get structured diagnostic reports |
| 📅 **Service Schedule** | Track maintenance based on mileage |
| 💰 **EMI Calculator** | Calculate loan EMI and affordability |
| 🔩 **Parts Lookup** | Find spare parts info and pricing |
| 💬 **General Q&A** | Ask anything about cars, EV, traffic laws, etc. |

---

## 🛠️ Tech Stack

- **LLM**: Google Gemini 2.0 Flash
- **AI Framework**: Pydantic AI (structured outputs)
- **Frontend**: Gradio
- **Data Models**: Pydantic v2
- **Data**: Local JSON car database

---

## 🚀 Quick Start

### 1. Clone / Open the Project
```bash
cd autobot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up API Key
```bash
# Copy the example env file
copy .env.example .env

# Edit .env and add your Gemini API key
# Get your key from: https://aistudio.google.com/app/apikey
```

Your `.env` file should look like:
```
GEMINI_API_KEY=AIza...your_key_here
```

### 4. Run the App
```bash
python main.py
```

### 5. Open in Browser
```
http://localhost:7860
```

---

## 📁 Project Structure

```
autobot/
├── main.py                  # Gradio UI + chat handlers
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── .env                     # Your API keys (create this)
│
├── agents/
│   └── car_agent.py         # Pydantic AI agents (6 specialized agents)
│
├── models/
│   └── schemas.py           # Pydantic v2 data models
│
├── tools/
│   └── car_tools.py         # Tool functions (EMI calc, DB queries)
│
└── data/
    └── cars_db.json         # Car database (8 cars + service data)
```

---

## 💬 Example Questions

```
🚗 "Best SUV under ₹15 lakhs for a family of 5"
🔧 "My car vibrates at high speed, what's wrong?"
📅 "What service is due for my Hyundai Creta at 45,000 km?"
💰 "EMI for Honda City with ₹2L down payment at 8.5% interest"
🔩 "Where to buy OEM brake pads for Maruti Swift?"
⚡ "Compare Tata Nexon EV vs Maruti Brezza petrol"
```

---

## 🏗️ Architecture

```
User (Gradio UI)
      ↓ message
Intent Detection (keyword-based)
      ↓
Pydantic AI Agent (routed by intent)
      ↓ structured prompt + DB context
Gemini 2.0 Flash API
      ↓ structured JSON response
Pydantic Model (validated)
      ↓ formatted markdown
Gradio Chat UI
```

---

## 📊 Pydantic Models

All responses are **structured** using Pydantic v2 models:

- `CarRecommendationResponse` — Car buying recommendations
- `DiagnosticReport` — Vehicle symptom analysis
- `ServiceScheduleResponse` — Maintenance schedule
- `EMICalculationResponse` — Loan EMI breakdown
- `PartsLookupResponse` — Spare parts information
- `GeneralAutoResponse` — General Q&A

---

## 🔑 Getting Your Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key and paste it in your `.env` file

---

## 🤝 Contributing

Feel free to extend the car database in `data/cars_db.json` or add new agents in `agents/car_agent.py`!

---

*Built with ❤️ for the Indian automobile market*
