# tests/test_tools.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

# Tests search_listings() 
def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

# Tests suggest_outfit()
def test_suggest_outfit():
    new_item = {
    "id": "lst_004",
    "title": "90s Track Jacket — Navy/White Stripe",
    "description": "Authentic 90s track jacket with stripe detail down the sleeves. Full zip. Lightweight — great for layering.",
    "category": "outerwear",
    "style_tags": ["90s", "vintage", "athletic", "streetwear"],
    "size": "M",
    "condition": "excellent",
    "price": 45.00,
    "colors": ["navy", "white"],
    "brand": "Champion",
    "platform": "poshmark"
  }
    results = suggest_outfit(new_item, get_example_wardrobe())
    assert isinstance(results, str)
    assert len(results) > 0

def test_suggest_empty_wardrobe():
    new_item = {
    "id": "lst_001",
    "title": "Vintage Levi's 501 Jeans — Medium Wash",
    "description": "Classic 501s in a perfect medium wash. Some light fading at the knees which adds to the vintage look. No rips or stains.",
    "category": "bottoms",
    "style_tags": ["vintage", "classic", "denim", "streetwear"],
    "size": "W30 L30",
    "condition": "good",
    "price": 38.00,
    "colors": ["blue", "indigo"],
    "brand": "Levi's",
    "platform": "depop"
  }
    results = suggest_outfit(new_item, get_empty_wardrobe())
    assert isinstance(results, str)
    assert len(results) > 0

# Tests create_fit_card()
def test_create_fit_card():
    new_item = {
    "id": "lst_004",
    "title": "90s Track Jacket — Navy/White Stripe",
    "description": "Authentic 90s track jacket with stripe detail down the sleeves. Full zip. Lightweight — great for layering.",
    "category": "outerwear",
    "style_tags": ["90s", "vintage", "athletic", "streetwear"],
    "size": "M",
    "condition": "excellent",
    "price": 45.00,
    "colors": ["navy", "white"],
    "brand": "Champion",
    "platform": "poshmark"
    }
    outfit = """I'd be happy to help you style the 90s Track Jacket. Here are two complete outfit combinations:
    **Outfit 1: Casual Streetwear**
        Pair the 90s Track Jacket with the Baggy straight-leg jeans, White ribbed tank top, and Chunky white sneakers.
        The navy and white stripes on the jacket complement the dark blue jeans, while the white tank top adds a clean and minimalist touch.
        The chunky sneakers tie in with the athletic vibe of the track jacket, creating a cohesive streetwear look.
        Finish the outfit with the Brown leather belt to add a touch of earthy tones.
    **Outfit 2: Layered Chic**
        Layer the 90s Track Jacket over the Oversized grey crewneck sweatshirt, and pair it with the Wide-leg khaki trousers and Black combat boots.
        The lightweight track jacket adds a sporty touch to the oversized sweatshirt, while the khaki trousers bring in a neutral earthy tone.
        The black combat boots ground the outfit and add a grunge-inspired edge.
        You can also add the Black crossbody bag to complete the look, keeping your hands free and adding a minimalist touch.
    In both outfits, the 90s Track Jacket is the statement piece, and the other items in your wardrobe complement its vintage athletic vibe.
    These combinations showcase the versatility of the thrifted item and how it can be styled for different occasions."""
    results = create_fit_card(outfit, new_item)
    assert isinstance(results, str)
    assert len(results) > 0
    assert results[0:6] != 'Error:'

def test_create_fit_card_empty_outfit():
    new_item = {
    "id": "lst_004",
    "title": "90s Track Jacket — Navy/White Stripe",
    "description": "Authentic 90s track jacket with stripe detail down the sleeves. Full zip. Lightweight — great for layering.",
    "category": "outerwear",
    "style_tags": ["90s", "vintage", "athletic", "streetwear"],
    "size": "M",
    "condition": "excellent",
    "price": 45.00,
    "colors": ["navy", "white"],
    "brand": "Champion",
    "platform": "poshmark"
    }
    results = create_fit_card("", new_item)
    assert isinstance(results, str)
    assert len(results) > 0
    assert results[0:6] == 'Error:'