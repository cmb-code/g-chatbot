"""
AutoBot — AI Automobile Assistant
Entry point: builds the Gradio UI and launches the server.

Architecture:
    main.py           ← launch entry point
    ui/
        app.py        ← Gradio UI layout & event wiring
        formatters.py ← GFM markdown response formatters
    agents/
        automotive_agent.py ← Single LLM-Led Pydantic AI Automotive Agent
    models/
        schemas.py    ← Pydantic response schemas
    tools/
        car_tools.py  ← Database query helpers & EMI math
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

from ui.app import PREMIUM_CSS, build_ui


if __name__ == "__main__":
    demo = build_ui()
    for port in range(7860, 7870):
        try:
            print(f"[AUTOBOT] [STARTUP] Launching server on port {port}...", flush=True)
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
            print(f"[AUTOBOT] [STARTUP] Port {port} is occupied; trying the next port...", flush=True)
