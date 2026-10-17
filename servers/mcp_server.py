"""Official MCP Python SDK v2 server for InfraAgentKit reference tools."""
from __future__ import annotations
import argparse
from mcp.server import MCPServer
from infraagentkit.tools import knowledge_search,risk_assess

mcp=MCPServer('InfraAgentKit')

@mcp.tool()
def knowledge_search_tool(query:str)->dict:
    """Search governed synthetic transport-infrastructure reference knowledge."""
    return knowledge_search(query)

@mcp.tool()
def risk_assess_tool(text:str)->dict:
    """Assess a transport-infrastructure event using deterministic demo rules."""
    return risk_assess(text)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--transport',choices=['stdio','streamable-http'],default='stdio');p.add_argument('--port',type=int,default=8113);a=p.parse_args()
    if a.transport=='streamable-http':mcp.run(transport='streamable-http',port=a.port)
    else:mcp.run()
