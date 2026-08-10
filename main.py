"""
AutoBot — AI Automobile Assistant
Entry point: builds the Gradio UI and launches the server.

Architecture:
    main.py           ← you are here (launch only)
    ui/
        app.py        ← Gradio UI layout & event wiring
        formatters.py ← GFM markdown response formatters
    agents/
        car_agent.py        ← master orchestrator
        query_agent.py      ← intent detection + entity extraction
        recommend_agent.py  ← car recommendation (Pydantic AI)
        diagnostic_agent.py ← vehicle diagnostics (Pydantic AI)
        service_agent.py    ← service schedule (Pydantic AI)
        emi_agent.py        ← EMI calculator (pure math)
        general_agent.py    ← general Q&A (direct Gemini call)
    models/
        schemas.py    ← Pydantic response schemas
    tools/
        car_tools.py  ← PostgreSQL query helpers & EMI math
    db/
        connection.py ← PostgreSQL pool + TTL cache
        queries.py    ← DB query helpers
        fuzzy_queries.py ← fuzzy car/issue matching
"""

import sys
import io

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

from db.connection import validate_db_config
validate_db_config()

from ui.app import build_ui, PREMIUM_CSS


if __name__ == "__main__":
    demo = build_ui()
    for port in range(7860, 7870):
        try:
            print(f"Attempting to launch AutoBot on port {port}...")
            demo.launch(
                server_name="0.0.0.0",
                server_port=port,
                share=False,
                show_error=True,
                css=PREMIUM_CSS,
            )
            break
        except OSError:
            if port == 7869:
                raise
            print(f"Port {port} is occupied, trying next port...")
