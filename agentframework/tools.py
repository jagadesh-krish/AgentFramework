from agent_framework import ai_function
from typing import Dict, List, Optional, Annotated
from RAG.poi_in_india import query_places

from agentframework.agent_middewares import log

@ai_function(name="get_places_of_interest", description="Gets places of interest in a location")
async def get_places_of_interest(query: Annotated[str, "query to get POI for a given location from KB"]) -> List[Dict]:
    log.msg("tool invoked with parameters", poi_query=query)
    result = query_places(query, top_k=5)
    log.msg("len of places found", length=len(result))
    log.msg("places query result", poi_result=result)
    if len(result) == 0:
        return [{"message": "No places of interest found for the given query."}]
    return result
