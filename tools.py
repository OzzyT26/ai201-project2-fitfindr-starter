"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings, get_example_wardrobe, get_empty_wardrobe

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)

# Global Variables
_CLIENT = _get_groq_client()
LLM_MODEL = "llama-3.3-70b-versatile"

# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    if not description or not description.strip():
        return []

    keywords = description.lower().split()
    matches = []

    for listing in listings:
        # 1. Filter by max_price
        if max_price is not None and listing["price"] > max_price:
            continue

        # 2. Filter by size
        if size is not None:
            requested_size = size.lower()
            listing_size = listing.get("size", "").lower()

            if requested_size not in listing_size:
                continue

        # 3. Build searchable text
        searchable_parts = [
            listing.get("title") or "",
            listing.get("description") or "",
            listing.get("category") or "",
            listing.get("brand") or "",
            listing.get("platform") or "",
            " ".join(listing.get("style_tags") or []),
            " ".join(listing.get("colors") or []),
        ]

        searchable_text = " ".join(searchable_parts).lower()

        # 4. Score by keyword overlap
        score = sum(1 for keyword in keywords if keyword in searchable_text)

        # 5. Drop listings with score 0
        if score > 0:
            matches.append((score, listing))

    # 6. Sort by relevance, highest score first
    matches.sort(key=lambda pair: pair[0], reverse=True)

    return [listing for score, listing in matches]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """

    wardrobe_items = wardrobe.get("items", []) if wardrobe else []

    item_summary = {
        "title": new_item.get("title"),
        "description": new_item.get("description"),
        "category": new_item.get("category"),
        "style_tags": new_item.get("style_tags") or [],
        "size": new_item.get("size"),
        "condition": new_item.get("condition"),
        "price": new_item.get("price"),
        "colors": new_item.get("colors") or [],
        "brand": new_item.get("brand"),
        "platform": new_item.get("platform"),
    }

    if wardrobe_items:
        wardrobe_lines = []
        for item in wardrobe_items:
            colors = ", ".join(item.get("colors") or [])
            tags = ", ".join(item.get("style_tags") or [])
            notes = item.get("notes") or "No notes"

            wardrobe_lines.append(
                f"- {item.get('name', 'Unnamed item')} "
                f"({item.get('category', 'unknown category')}; "
                f"colors: {colors or 'unknown'}; "
                f"style tags: {tags or 'none'}; "
                f"notes: {notes})"
            )

        wardrobe_text = "\n".join(wardrobe_lines)

        prompt = f"""You are a practical fashion stylist. The user is considering buying this thrifted item: {item_summary}. The user's wardrobe contains: {wardrobe_text}.
        Suggest 1–2 complete outfit combinations using the thrifted item and specific named pieces from the user's wardrobe.
        Requirements:
            - Use the thrifted item in every outfit.
            - Refer to wardrobe pieces by their names when possible.
            - Include tops, bottoms, shoes, and accessories when relevant.
            - Explain why the pieces work together.
            - Keep the advice practical, stylish, and concise."""
    else:
        prompt = f"""You are a practical fashion stylist. The user is considering buying this thrifted item: {item_summary}. The user's wardrobe is empty or unavailable.
        Suggest 1–2 complete outfit ideas using this item. Since there are no wardrobe pieces available, recommend general types of pieces that would pair well with it.
        Requirements:
            - Use the thrifted item in every outfit.
            - Suggest specific categories of pieces, such as bottoms, shoes, outerwear, or accessories.
            - Explain the overall vibe.
            - Keep the advice practical, stylish, and concise."""

    response = _CLIENT.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful fashion stylist for secondhand clothing.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.7,
    )

    outfit = response.choices[0].message.content

    # Failsafe - if nothing is returned from LLM
    if not outfit or not outfit.strip():
        return (
            "I couldn't generate a specific outfit, but this item would pair well "
            "with simple wardrobe basics in complementary or neutral colors."
        )

    return outfit.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return (
            "Error: I couldn't create a fit card because the outfit suggestion was empty. "
            "Please generate an outfit first."
        )

    item_title = new_item.get("title", "this thrifted piece")
    price = new_item.get("price", "unknown price")
    platform = new_item.get("platform", "the thrift platform")
    brand = new_item.get("brand") or "unbranded"
    colors = ", ".join(new_item.get("colors") or [])
    style_tags = ", ".join(new_item.get("style_tags") or [])

    prompt = f"""You are writing a short, shareable outfit caption for a secondhand fashion app.
    Thrifted item:
        - Title: {item_title}
        - Price: ${price}
        - Platform: {platform}
        - Brand: {brand}
        - Colors: {colors or "unknown"}
        - Style tags: {style_tags or "none"}
    Outfit suggestion:
        {outfit}
    Write a 2–4 sentence Instagram/TikTok-style caption.
    Requirements:
        - Sound casual and authentic, like a real OOTD post.
        - Mention the item name naturally.
        - Mention the price naturally.
        - Mention the platform naturally.
        - Capture the outfit vibe in specific terms.
        - Do not sound like a product description.
        - Do not use bullet points."""

    response = _CLIENT.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You write casual, stylish outfit captions for thrifted finds.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.9,
    )

    fit_card = response.choices[0].message.content

    if not fit_card or not fit_card.strip():
        return (
            "Error: I couldn't create a fit card because the caption generator returned an empty response."
        )

    return fit_card.strip()
