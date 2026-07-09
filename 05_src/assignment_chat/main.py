from langgraph.graph import StateGraph, MessagesState, START
from langchain.chat_models import init_chat_model
from langgraph.prebuilt.tool_node import ToolNode, tools_condition
from langchain_core.messages import SystemMessage,  HumanMessage

from dotenv import load_dotenv

from assignment_chat.prompts import return_instructions
from assignment_chat.tools_weather_check import get_current_weather
from assignment_chat.tools_weather_knowledge import search_weather_knowledge

import os
from dotenv import load_dotenv

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_DIR = os.path.dirname(_THIS_DIR)  # 05_src

load_dotenv(os.path.join(_ENV_DIR, ".env"))
load_dotenv(os.path.join(_ENV_DIR, ".secrets"))
os.environ["LANGSMITH_TRACING"] = "false"


chat_agent = init_chat_model(
    model="gpt-4o-mini",
    base_url='https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1',
    api_key='any value',
    default_headers={"x-api-key": os.getenv('API_GATEWAY_KEY')}
)

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

mcp_client = MultiServerMCPClient({
    "weather_advice": {
        "command": "python",
        "args": [os.path.join(_THIS_DIR, "advice_mcp_server.py")],
        "transport": "stdio",
    }
})

mcp_tools = asyncio.run(mcp_client.get_tools())

tools = [search_weather_knowledge, get_current_weather] + mcp_tools

instructions = return_instructions()



# @traceable(run_type="llm")
def call_model(state: MessagesState):
    """LLM decides whether to call a tool or not"""
    response = chat_agent.bind_tools(tools).invoke( [SystemMessage(content=instructions)] + state["messages"])
    return {
        "messages": [response]
    }

def get_graph():
    
    builder = StateGraph(MessagesState)
    builder.add_node(call_model)
    builder.add_node(ToolNode(tools))
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges(
        "call_model",
        tools_condition,
    )
    builder.add_edge("tools", "call_model")
    graph = builder.compile()
    return graph

async def main():
    graph = get_graph()
    result = await graph.ainvoke({"messages": [HumanMessage(content="What's the weather like in Newmarket? what should I wear in Newmarket today? And tell me a weather history fact")]})
    for msg in result["messages"]:
        print(type(msg).__name__, getattr(msg, "tool_calls", None) or getattr(msg, "content", None))

if __name__ == "__main__":
    asyncio.run(main())