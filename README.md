# FitFindr

## Tool Inventory
### Tool 1: search_listings

**What it does:**
Searches the listings located in data/listings.json and returns items that match the description, size, and max_price given to the function as inputs. Returns an empty list if nothing matches — does NOT raise an exception.

**Input parameters:**
- `description` (str): Keywords describing what the user is looking for (e.g., "vintage graphic tee").
- `size` (str): Size string to filter by, or None to skip size filtering. Matching is case-insensitive (e.g., "M" matches "S/M").
- `max_price` (float): Maximum price (inclusive), or None to skip price filtering.

**What it returns:**
A list of matching listing dicts, sorted by relevance (best match first).Returns an empty list if nothing matches — does NOT raise an exception.

Each listing dict has the following fields:
     id, title, description, category, style_tags (list), size, condition, price (float), colors (list), brand, platform

**What happens if it fails or returns nothing:**
If the function fails or a matching listing isn't found, returns an empty list — does NOT raise an exception.

---

### Tool 2: suggest_outfit

**What it does:**
Given a specific item (new_item) and the user's current wardrobe (wardrobe), suggests one or more complete outfit combinations. Must handle an empty or minimal wardrobe.

**Input parameters:**
- `new_item` (dict): A listing dict (the item the user is considering buying)
- `wardrobe` (dict): A wardrobe dict with an 'items' key containing a list of wardrobe item dicts. May be empty — handle this gracefully.

**What it returns:**
A non-empty string with outfit suggestions. If the wardrobe is empty, returns a string containing general styling advice for the item rather than raising an exception or returning an empty string.

**What happens if it fails or returns nothing:**
If the wardrobe is empty or no outfit can be suggested, offer general styling advice for the item rather than raising an exception or returning an empty string.

---

### Tool 3: create_fit_card

**What it does:**
Generates a short, shareable description of a complete outfit -- the kind of thing someone would caption an Instagram post with. Must produce something different each time for different inputs.

**Input parameters:**
- `outfit` (...): The outfit suggestion string from suggest_outfit().
- `new_item` (...): The listing dict for the thrifted item.

**What it returns:**
Returns a 2–4 sentence string usable as an Instagram/TikTok caption. If outfit is empty or missing, returns a descriptive error message string.

**What happens if it fails or returns nothing:**
If the function fails or if outfit is empty or missing, returns a descriptive error message string — does NOT raise an exception.

## Planning Loop Explanation
Global variables that the planning loop has access to:
     TOOL_DEFINITIONS - a list of dictionaries that describes what each tool does and its parameters.
     SYSTEM_PROMPT - a string to be provided to the LLM that describes its role and what it is meant to accomplish
Before entering the planning loop:
     System is given the prompt and the user's query:
     {"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": query}
     A new session is created by calling: session = _new_session(query, wardrobe)
     We set session["query"] to the query that was given to run_agent() as a parameter.
     We parse the query string for a description of the desired item, size, and max price of the item.
     The extracted items are saved to a dictionary pointed to by session["parsed"]:
          If a description was found, it is saved with the key "description".
          If a size was found, it is saved with the key "size".
          If a maximum price was found, the extracted value is saved with the key "max_value".  
Planning Loop:
     The planning loop runs a set number of times (indicated by the MAX_TOOL_ROUNDS variable in the configuration file) as a safeguard.
     If the loop runs the number of times indicated by MAX_TOOL_ROUNDS, then we set session["error"] to the following message then return session:
          ("I'm sorry, I couldn't finish answering that within the tool-call limit. "
          "Please try asking again with a more detailed description of the item you're looking for.")
     LLM is called and given the model, messages, TOOL_DEFINITIONS, and tool_choice is set to "auto".
     The LLM selects tools to be called and provides arguments to provide to each tool.
     The loop first gets the assistant_message located in: response.choices[0].message
     And inside the assistant_message, we access tool_calls: assistant_message.tool_calls
     If assistant_message.tool_calls is empty, then the LLM has reached its final answer, and we return assistant_message.content.
     Otherwise, for each tool_call provided by the LLM in assistant_message.tool_calls:
          We get the tool name from: tool_call.function.name
          We get the tool args from: tool_call.function.arguments
          We call the indicated tool with the indicated arguments
          We check what the tool returns for error conditions:
               search_listings(): Returns an empty list if nothing matches.
               suggest_outfit(): If wardobe isn't empty, returns a non-empty string with outfit suggestions. If the wardrobe is empty, returns general styling advice for the item.
               create_fit_card(): If outfit is empty or missing when called, returns a descriptive error message.
          If search_listings() or create_fit_card() return their designated error (an empty list or an error message), we immediately return an appropriate error message to the user:
               If search_listings() returns an empty list, we set session["error"] to the following message then return session:
                    ("I'm sorry, I couldn't find any listings that match the item you described. Please try again.")
               If create_fit_card() returns an error message, we set session["error"] to the following message then return session:
                    ("I'm sorry, I couldn't find an outfit to go with the item. Please try again.")
               suggest_outfit() should always return a usable outfit string. search_listings() must be called before suggest_outfit(). If search_listings() doesn't return a listing, the run_agent() function returns early, so suggest_outfit() isn't called. If wardrobe parameter is empty, suggest_outfit() asks the LLM for general styling advice for the item and returns this advice as a string. Either way, a useable recommendaiton string is returned.
          After error checking, if we received valid output from the tool, we update the session information:
               If search_listings() was called:
                    The list of matching search results returned from search_listings() is saved to session["search_results"]
                    The first item in the list returned by search_listings() is saved to session["selected_item"]
               If suggest_outfit() was called:
                    We save the return value into session["outfit_suggestion"]
               If create_fit_card() was called:
                    We save the return value into session["fit_card"]
          Then we update messages: 
               messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result, # content returned from the tool call 
                })
          We then return to the top of the loop.

# State Management Approach
The agent stores the state within a dictionary called session. It accesses the current state by accessing the session dictionary.  Here is the structure of the dictionary and the data being tracked:
     {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }

The results of each tool call are saved to the session dictonary:
     "search_results": [],        # result list returned from search_listings()
     "selected_item": None,       # first result in list returned from search_listings()
     "outfit_suggestion": None,   # string returned by suggest_outfit()
     "fit_card": None,            # string returned by create_fit_card()

The _dispatch_tool() function in agent.py calls the tool indicated by the LLM, then updates the session dictionary with the data returned by each tool.  The session dictionary is then used to pass data as input to other tool calls:
     search_listings(description: str, size: str | None = None, max_price: float | None = None,)
          At the beginning of the run_agent() loop, this information is parsed and saved to session["parsed"]. 
          The parameters are then passed to search_listings() thusly: search_listings(parsed["description"], parsed["size"], parsed["max_price"])
     suggest_outfit(new_item: dict, wardrobe: dict)
          The parameters are passed to suggest_outfit thusly: suggest_outfit(session["selected_item"], session["wardrobe"])
     create_fit_card(outfit: str, new_item: dict)
          The parameters are passed to create_fit_card() thusly: create_fit_card(session["outfit_suggestion"], session["selected_item"])

If any of the tool calls return an error, the error message is saved to session["error"] and session is returned immediately.

# Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Saves the error message returned from search_listings() to session["error"] and immediately returns the session dictionary.|
| suggest_outfit | Wardrobe is empty | Asks LLM to provide general styling advice for the item rather than raising an exception or returning an empty string. Returns general styling advice.|
| create_fit_card | Outfit input is missing or incomplete | Saves the error message returned from create_fit_card() to session["error"] and immediately returns the session dictionary.|

search_listings error example:
    Searched for "XL purple dinosaur tee under $2", which doesn't match any listings in listings.json. Fitfindr returned the following: "I couldn't find any matching listings for the item you described. Please try a different item." This is the appropriate behavior.

suggest_outfit error example:
    I used search_listings to return a valid result for a 'vintage graphic tee', then ran suggest_outfit() with the result and an empty wardrobe. The system returned the following: 
        "I'd be happy to help you style this adorable Y2K Baby Tee. Here are two complete outfit ideas:
        **Outfit 1: Casual Day Out**
        Pair the butterfly print tee with a pair of high-waisted jeans (bottoms) and white sneakers (shoes) for a relaxed, everyday look. Add a denim jacket (outerwear) to layer over the tee for a cooler evening. Finish with a pair of layered necklaces (accessories) featuring delicate chains and tiny charms to enhance the cottagecore vibe. This outfit exudes a laid-back, nostalgic feel perfect for running errands or meeting friends.

        **Outfit 2: Evening Hangout**
        Create a cute and playful outfit by pairing the baby tee with a flowy, pastel-colored skirt (bottoms) and a pair of ankle boots (shoes). Throw on a faux leather jacket (outerwear) to add an edgy touch. Accessorize with a floppy hat (accessories) and a cross-body bag to complete the look. This outfit has a fun, whimsical vibe ideal for a night out with friends or a casual date."
    This is the expected behavior.

create_fit_card error example:
    I used search_listings to return a valid result for a 'vintage graphic tee', then ran create_fit_card() with the result and an empty outfit_suggestion. The system returned the following: "I couldn't create a fit card because the outfit suggestion was empty. Please create an outfit first." This is the expected result.
    
# Spec Reflection
**One way the spec helped you during implementation:**
**One way your implementation diverged from the spec, and why:**

# AI Usage
**Instance 1**
- *What I gave the AI:*
I asked ChatGPT to implement suggest_outfit(). I will give it the Tools, Planning Loop, Error Handling, and Architecture sections of planning.md.
- *What it produced:*
- *What I changed or overrode:*

**Instance 2**
- *What I gave the AI:*
I had Chatgpt implement a draft of run_agent() and to implement to planning loop. I will give it the agent diagram, the Planning Loop, and the State Management sections of my spec. 
- *What it produced:*
- *What I changed or overrode:*
