# AutoBot — AI Automobile Assistant
# agents/ package — one agent per module

from agents.car_agent import chat_with_autobot
from agents.query_agent import run_query_agent
from agents.recommend_agent import get_recommend_agent
from agents.diagnostic_agent import get_diagnostic_agent
from agents.service_agent import get_service_agent
from agents.emi_agent import handle_emi
from agents.general_agent import handle_general

__all__ = [
    "chat_with_autobot",
    "run_query_agent",
    "get_recommend_agent",
    "get_diagnostic_agent",
    "get_service_agent",
    "handle_emi",
    "handle_general",
]
