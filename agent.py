"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import json
import re
from tools import _get_groq_client, search_listings, suggest_outfit, create_fit_card

# Global variables
_CLIENT = _get_groq_client()
LLM_MODEL = "llama-3.3-70b-versatile"
MAX_TOOL_ROUNDS = 5
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_listings",
            "description": "Search secondhand listings by description, optional size, and optional max price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "size": {"type": ["string", "null"]},
                    "max_price": {"type": ["number", "null"]},
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_outfit",
            "description": "Suggest an outfit using the selected item and the user's wardrobe.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_fit_card",
            "description": "Create a short social-media-style fit card from the outfit and selected item.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

SYSTEM_PROMPT = """
You are Fitfindr, a friendly secondhand fashion advisor who helps users find secondhand pieces and figure out how to wear them.
Help users find clothing pieces by looking up pieces that match the user's specifications.
Then create outfit suggestions using the selected clothing piece and short, shareable outfit captions for the thrifted find.
Be sure to only use the provided tools, not your general knowledge.
Tools must be called in this order: search_listings, suggest_outfit, create_fit_card"""


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }

# ── parsing helper ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    parsed = {
        "description": query,
        "size": None,
        "max_price": None,
    }

    # Find max price: "under $30", "$30", "under 30"
    price_match = re.search(r"(?:under|below|less than)?\s*\$?(\d+(?:\.\d+)?)", query.lower())
    if price_match:
        parsed["max_price"] = float(price_match.group(1))

    # Find size: "size M", "size XXS", etc.
    size_match = re.search(r"\bsize\s+([a-zA-Z0-9/]+)\b", query, re.IGNORECASE)
    if size_match:
        parsed["size"] = size_match.group(1)

    # Clean description by removing price and size phrases
    description = query
    description = re.sub(r"(?:under|below|less than)?\s*\$?\d+(?:\.\d+)?", "", description, flags=re.IGNORECASE)
    description = re.sub(r"\bsize\s+[a-zA-Z0-9/]+\b", "", description, flags=re.IGNORECASE)
    description = description.replace(",", " ").strip()

    parsed["description"] = description

    return parsed

# ── tool dispatcher ─────────────────────────────────────────────────────────────
def _dispatch_tool(tool_name: str, tool_args: dict, session: dict) -> dict:
    tool_args = tool_args or {}

    if tool_name == "search_listings":
        result = search_listings(
            tool_args.get("description") or session["parsed"].get("description"),
            size=tool_args.get("size", session["parsed"].get("size")),
            max_price=tool_args.get("max_price", session["parsed"].get("max_price")),
        )

        session["search_results"] = result

        if not result:
            session["error"] = "I couldn't find any matching listings for the item you described. Please try a different item."  # []
            return session

        session["selected_item"] = result[0]
        return session

    if tool_name == "suggest_outfit":
        if session["selected_item"] is None:
            session["error"] = (
                "Cannot suggest an outfit because no listing was selected. "
                "search_listings must return at least one item first."
                "Please try searching for a different item."
            )
            return session
        result = suggest_outfit(
            session["selected_item"],
            session["wardrobe"],
        )

        session["outfit_suggestion"] = result
        return session

    if tool_name == "create_fit_card":
        if not session["outfit_suggestion"] or session["selected_item"] is None:
            session["error"] = (
                "Cannot create a fit card because the outfit or selected item is missing."
            )
            return session
        result = create_fit_card(
            session["outfit_suggestion"],
            session["selected_item"],
        )

        session["fit_card"] = result
        if "error:" in result.lower():
            session["error"] = result

        return session

# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    session = _new_session(query, wardrobe)
    session["parsed"] = _parse_query(query)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"User query: {query}\n\n"
                f"Parsed search parameters: {json.dumps(session['parsed'])}\n\n"
                "Use the tools to complete the FitFindr workflow."
            ),
        },
    ]

    for _ in range(MAX_TOOL_ROUNDS):
        response = _CLIENT.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message

        # When no more tools are called, session is complete
        if not assistant_message.tool_calls:
            return session

        messages.append(assistant_message)

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments or "{}")

            tool_result = _dispatch_tool(tool_name, tool_args, session)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result),
            })

            if session["error"]:
                return session

            if session["fit_card"]:
                return session

    session["error"] = (
        "I'm sorry, I couldn't finish answering that within the tool-call limit. "
        "Please try asking again with a more detailed description of the item you're looking for."
    )
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
