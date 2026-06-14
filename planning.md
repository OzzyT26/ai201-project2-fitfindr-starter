# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the listings locate din data/listings.json and returns items that match the description, size, and max_price given to the function as inputs. Returns an empty list if nothing matches — does NOT raise an exception.

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
A non-empty string with outfit suggestions. If the wardrobe is empty, offer general styling advice for the item rather than raising an exception or returning an empty string.

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
Returns a 2–4 sentence string usable as an Instagram/TikTok caption. If outfit is empty or missing, return a descriptive error message string — do NOT raise an exception.

The caption should:
     - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

**What happens if it fails or returns nothing:**
If the function fails or if outfit is empty or missing, return a descriptive error message string — do NOT raise an exception.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
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

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
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

These are then be passed as input to other tool calls:
     search_listings(description: str, size: str | None = None, max_price: float | None = None,)
          At the beginning of the run_agent() loop, this information is parsed and saved to session["parsed"]. 
          The parameters are then passed to search_listings() thusly: search_listings(parsed["description"], parsed["size"], parsed["max_price"])
     suggest_outfit(new_item: dict, wardrobe: dict)
          The parameters are passed to suggest_outfit thusly: suggest_outfit(session["selected_item"], session["wardrobe"])
     create_fit_card(outfit: str, new_item: dict)
          The parameters are passed to create_fit_card() thusly: create_fit_card(session["outfit_suggestion"], session["selected_item"])

If any of the tool calls return an error, the error message is saved to session["error"] and session is returned immediately.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Saves the error message returned from search_listings() to session["error"] and immediately returns the session dictionary.|
| suggest_outfit | Wardrobe is empty | Asks LLM to provide general styling advice for the item rather than raising an exception or returning an empty string. Returns general styling advice.|
| create_fit_card | Outfit input is missing or incomplete | Saves the error message returned from create_fit_card() to session["error"] and immediately returns the session dictionary.|

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

     User query
    │
    ▼
Planning Loop ───────────────────────────────────────────────────────────────┐
    │                                                                       │
    ├─► Call LLM with messages + TOOL_DEFINITIONS + tool_choice="auto"      │
    │       │                                                               │
    │       │ assistant_message.tool_calls is empty                         │
    │       ├──► Return assistant_message.content                           │
    │       │                                                               │
    │       │ assistant_message.tool_calls present                          │
    │       ▼                                                               │
    │   For each tool_call: extract tool name + arguments                   │
    │       │                                                               │
    ├─► search_listings(description, size, max_price)                       │
    │       │ results=[]                                                    │
    │       ├──► [ERROR] session["error"] = "No listings found..." → return │
    │       │                                                               │
    │       │ results=[item, ...]                                           │
    │       ▼                                                               │
    │   Session: search_results = results                                   │
    │   Session: selected_item = results[0]                                 │
    │       │                                                               │
    ├─► suggest_outfit(selected_item, wardrobe)                             │
    │       │ wardrobe empty                                                │
    │       ├──► Return general styling advice                              │
    │       │                                                               │
    │       │ outfit_suggestion="..."                                       │
    │       ▼                                                               │
    │   Session: outfit_suggestion = "..."                                  │
    │       │                                                               │
    ├─► create_fit_card(outfit_suggestion, selected_item)                   │
    │       │ error message returned                                        │
    │       ├──► [ERROR] session["error"] = "Couldn't create fit card..."   │
    │       │        → return session                                       │
    │       │                                                               │
    │       │ fit_card="..."                                                │
    │       ▼                                                               │
    │   Session: fit_card = "..."                                           │
    │       │                                                               │
    ├─► Append tool result to messages                                      │
    │       messages.append({role: "tool", tool_call_id, content})          │
    │       │                                                               │
    │       └──► Repeat Planning Loop                                       │
    │                                                                       │
    └─► MAX_TOOL_ROUNDS reached                                             │
            │                                                               │
            ├──► [ERROR] session["error"] = "Tool-call limit reached..."    │
            │        → return session                                       │
            │                                                               │
            └───────────────────────────────────────────────────────────────┘

Return session

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
I ask ChatGPT to implement suggest_outfit(). I will give it the Tools, Planning Loop, Error Handling, and Architecture sections of planning.md. I will test it against a regular input, and also against an input where wardrobe is empty to make sure general recommendaitons are returned as specified by the spec.

**Milestone 4 — Planning loop and state management:**
I will ask ChatGPT to implement a draft of run_agent() and to implement to planning loop. I will give it the agent diagram, the Planning Loop, and the State Management sections of my spec. I will go over the draft to make sure it adheres to the spec. I will assure that it isn't calling all three tools unconditionally and that it is calling the tools according to the model's recommendations.
---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
The first thing run_agent() does is call _new_session(query: str, wardrobe: dict) to initialize a fresh session dict for one user interaction.
It passes the query from the user and an empty wardrobe by calling utils's get_empty_wardrobe().
It will save the returned section dictionary and with store the query in session["query"] and the empty wardrobe to session["wardrobe"].

Next, run_agent() will parse the user's query to extract a description, size, and max_price. I will ask the LLM to parse the query.
Note: For this first call to the LLM, since I don't need it to recommend tools, I'll call client.chat.completions.create() with the following parameters:
    model=LLM_MODEL
    messages=parse_messages
For this case, the LLM should return something like: {"description" : "vintage graphic tee", "size" : None, "max_price" : 29.99}
The result is stored in session["parsed"].

Next, the agent will build a messages list: system prompt + conversation history + new user message
At this point, there is no history to add, so it will skip this step.
Then it will append the user's query to messages
Then the LLM is called and given the following parameters:
     model - this will be the client returned by calling _get_groq_client() from tools.py
     messages - message list we just created
     tools - list of tool definitions that will be a global variable in agent.py
     tool_choice="auto"
The LLM will return a response, which at this stage, should include tool_calls.
We append the assistant message (with tool_calls) to messages.
For each tool call in the assistant message, we call each tool with the arguments given in the message.
For this case, first tool call will be search_listings(). The function's paramaters are description, size, and max_price. I will pass it the args give in the LLMs response.  For this example, they would likely look like:
    description: 'vintage graphic tee'
    size: None
    max_price: 29.99 # Because user indicated under 30 dollars


**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
search_listings() will return either a list of matching listing dicts or an empty list if nothing was found.
If there are results, I will store the top result in session["search_results"]
If there aren't results, I would set session["error"] to a helpful message and return the session early.
For this case, an example list of some listing dicts it could return are: 
[{
    "id": "lst_002",
    "title": "Y2K Baby Tee — Butterfly Print",
    "description": "Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.",
    "category": "tops",
    "style_tags": ["y2k", "vintage", "graphic tee", "cottagecore"],
    "size": "S/M",
    "condition": "excellent",
    "price": 18.00,
    "colors": ["white", "pink", "purple"],
    "brand": null,
    "platform": "depop"
  },
  {
    "id": "lst_003",
    "title": "Oversized Flannel Shirt — Plaid Red/Black",
    "description": "Classic oversized flannel. Great layering piece. A few tiny pulls in the fabric but nothing visible when worn.",
    "category": "tops",
    "style_tags": ["grunge", "vintage", "flannel", "streetwear", "layering"],
    "size": "XL (oversized)",
    "condition": "good",
    "price": 22.00,
    "colors": ["red", "black"],
    "brand": "Woolrich",
    "platform": "thredUp"
  },
]
Since the list of listing dicts returned from search_listings() are listed in order of relevance, I will store the first dictionary in session["selected_item"].
I will update the message history with what was received from the tool call.
Then we call the LLM again with the updated messages to get the next tool recommendation.
The next tool recommendation will likely be suggest_outfit().
I will call suggest_outfit() with the selected_item: session["selected_item"] and the current wardrobe: session["wardrobe"]

**Step 3:**
<!-- What happens next? What was returned from step 2? What tool is called now? -->
In step 2, we called suggest_outfit(). 
suggest_outfit() returns a non-empty string with outfit suggestions. If the wardrobe passed to the function is empty, it returns general styling advice.
An example of what suggest_outfit could return for this query is: "Pair this Butterfly Print Y2K Baby Tee with your baggy jeans and chunky sneakers for a vintage look."
I will store the result in session["outfit_suggestion"].
I will update the message history with what was received from the tool call.
Then we call the LLM again with the updated messages to get the next tool recommendation.
The next tool recommendation will likely be create_fit_card().
We call create_fit_card() with parameters: outfit: session["outfit_suggestion"] and new_item: session["selected_item"]
create_fit_card() returns a either an error message string or 2–4 sentence string usable as an Instagram/TikTok caption.
If we received an error message string from create_fit_card(), we set session["error"] to a helpful message and return the session early.
In this case, it would return something like this: "Thrifted this cute butterfly print Y2K baby tee from depop for only $18! Perfect for my vintage syle era 🖤!"
In this case, we will store the result in session["fit_card"], then return the session.

**Final output to user:**
<!-- What does the user actually see at the end? -->
If session["error"] was set, we will show an error message to the user. Otherwise, the user will see the item that was selected, price, shop the item comes from, and styling suggestions. It will also show them a recommended caption for social media.
For our example query, here is a possible response: "I recommend this butterfly print Y2K Baby Tee that I found on depop for $18. Crop it and wear it with your baggy jeans and chunky sneakers for a perfect vintage look. Here's a great caption that you can use for your socials: Thrifted this cute butterfly print Y2K baby tee from depop for only $18! Perfect for my vintage syle era 🖤!"