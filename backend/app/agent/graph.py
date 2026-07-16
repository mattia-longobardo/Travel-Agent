# backend/app/agent/graph.py
from langgraph.graph import StateGraph, END
from app.agent.state import TravelState
from app.agent.nodes.intake import intake_node
from app.agent.nodes.scout import scout_node
from app.agent.nodes.flight import flight_node
from app.agent.nodes.hotel import hotel_node
from app.agent.nodes.package import package_node
from app.agent.nodes.optimizer import optimizer_node
from app.agent.nodes.presenter import presenter_node


# Scout proposes destinations and stops for the user to choose; only once a destination is
# selected does it fan out to the searchers (then join on the optimizer). The fan-out follows
# the requested search_mode: hotel-only (incl. overland/no_flight trips) skips flight+package,
# flight-only skips hotel+package, the default compares flight+hotel+package. A scout turn with
# no destinations and no question (conversational reply / empty proposal) ends the turn.
def after_scout(state):
    if state.get("pending_question"):
        return END
    if not state.get("destinations"):
        return END
    mode = state.get("search_mode") or "flight_hotel"
    if state.get("no_flight") or mode == "hotel_only":
        return ["hotel"]
    if mode == "flight_only":
        return ["flight"]
    return ["flight", "hotel", "package"]


def build_graph(llm, mcp, web_search=None, checkpointer=None):
    async def _intake(s): return await intake_node(s, llm)
    async def _scout(s): return await scout_node(s, llm, web_search)
    async def _flight(s): return await flight_node(s, llm, mcp)
    async def _hotel(s): return await hotel_node(s, llm, mcp)
    async def _package(s): return await package_node(s, llm, mcp)
    async def _optimizer(s): return await optimizer_node(s)
    async def _presenter(s): return await presenter_node(s, llm, mcp)

    g = StateGraph(TravelState)
    g.add_node("intake", _intake)
    g.add_node("scout", _scout)
    g.add_node("flight", _flight)
    g.add_node("hotel", _hotel)
    g.add_node("package", _package)
    g.add_node("optimizer", _optimizer)
    g.add_node("presenter", _presenter)

    g.set_entry_point("intake")

    def after_intake(state):
        return END if state.get("pending_question") else "scout"
    g.add_conditional_edges("intake", after_intake, {END: END, "scout": "scout"})

    g.add_conditional_edges("scout", after_scout,
                            {END: END, "flight": "flight", "hotel": "hotel", "package": "package"})
    g.add_edge("flight", "optimizer")
    g.add_edge("hotel", "optimizer")
    g.add_edge("package", "optimizer")
    g.add_edge("optimizer", "presenter")
    g.add_edge("presenter", END)
    return g.compile(checkpointer=checkpointer)
