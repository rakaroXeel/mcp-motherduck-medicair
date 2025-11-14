import logging
from pathlib import Path
from pydantic import AnyUrl
from typing import Literal
import mcp.types as types
from mcp.types import CallToolResult
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from .configs import SERVER_VERSION
from .database import DatabaseClient
from .prompt import PROMPT_TEMPLATE, MOTHERDUCK_PROMPT


logger = logging.getLogger("mcp_server_medicair")


def parse_ui_uri(uri: AnyUrl) -> tuple[bool, str | None]:
    """
    Parse a UI URI for Apps SDK widgets.
    
    Args:
        uri: The URI to parse (AnyUrl from Pydantic)
        
    Returns:
        Tuple of (is_ui_uri, path_part) where:
        - is_ui_uri: True if this is a ui:// URI
        - path_part: The parsed path part of the URI, or None if not a UI URI
    """
    # Convert URI to string for easier parsing
    uri_str = str(uri)
    logger.debug(f"Parsing URI: {uri_str} (type: {type(uri)}, scheme attr: {getattr(uri, 'scheme', 'N/A')})")
    
    # Try multiple ways to detect ui:// URI
    is_ui_uri = False
    path_part = None
    
    # Method 1: Check if string starts with ui://
    if uri_str.startswith("ui://"):
        is_ui_uri = True
        path_part = uri_str.replace("ui://", "")
    
    # Method 2: Check scheme attribute
    elif hasattr(uri, 'scheme') and str(uri.scheme) == "ui":
        is_ui_uri = True
        # Try to get path from URI object
        if hasattr(uri, 'path'):
            path_part = str(uri.path)
        elif hasattr(uri, 'host'):
            # Sometimes widget is in host part
            path_part = str(uri.host) if uri.host else None
        else:
            path_part = uri_str.replace("ui://", "")
    
    # Method 3: Check if URI contains widget/query-results.html
    elif "widget/query-results.html" in uri_str or "query-results.html" in uri_str:
        is_ui_uri = True
        # Extract path from URI string
        if "ui://" in uri_str:
            path_part = uri_str.split("ui://", 1)[1]
        else:
            # Try to extract from any format
            path_part = uri_str.split("://", 1)[1] if "://" in uri_str else uri_str
    
    if is_ui_uri and path_part:
        # Normalize the path - remove leading slash if present
        if path_part.startswith("/"):
            path_part = path_part[1:]
        logger.debug(f"Parsed UI URI path: {path_part}")
    
    return is_ui_uri, path_part


def build_application(
    db_path: str,
    motherduck_token: str | None = None,
    home_dir: str | None = None,
    saas_mode: bool = False,
    read_only: bool = False,
):
    logger.info("Starting Medicair MCP Server")
    server = Server("mcp-server-medicair")
    db_client = DatabaseClient(
        db_path=db_path,
        motherduck_token=motherduck_token,
        home_dir=home_dir,
        saas_mode=saas_mode,
        read_only=read_only,
    )

    logger.info("Registering handlers")

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        """
        List available resources including the query results widget.
        """
        logger.info("Listing resources")
        return [
            types.Resource(
                uri="ui://widget/query-results.html",
                name="Query Results Widget",
                description="Widget HTML per visualizzare i risultati delle query SQL",
                mimeType="text/html+skybridge",
            )
        ]

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> str:
        """
        Read the query results widget HTML.
        Supports ui:// URIs for Apps SDK widgets.
        """
        uri_str = str(uri)
        logger.info(f"Reading resource: {uri_str}")
        
        # Parse the URI using dedicated method
        is_ui_uri, path_part = parse_ui_uri(uri)
        
        if is_ui_uri and path_part:
            logger.info(f"Detected UI resource, parsed path: {path_part}")
            
            # Check if it's our widget (handle both exact match and partial match)
            if path_part == "widget/query-results.html" or path_part.endswith("query-results.html") or "query-results" in path_part:
                # Determina il percorso del file widget relativo alla root del progetto
                # Il file si trova in public/query-results-widget.html dalla root del progetto
                current_file = Path(__file__)
                # Risali fino alla root del progetto (src/mcp_server_medicair/server.py -> src -> root)
                project_root = current_file.parent.parent.parent
                widget_path = project_root / "public" / "query-results-widget.html"
                
                logger.info(f"Looking for widget at: {widget_path} (exists: {widget_path.exists()})")
                
                if widget_path.exists():
                    logger.info(f"Successfully loading widget from: {widget_path}")
                    return widget_path.read_text(encoding="utf-8")
                else:
                    logger.error(f"Widget file not found at: {widget_path}")
                    raise ValueError(f"Widget file not found: {widget_path}")
            else:
                logger.warning(f"Unknown UI resource path: {path_part}")
                raise ValueError(f"Unknown UI resource path: {path_part}")
        
        logger.error(f"Unsupported URI scheme. URI: {uri_str}, Scheme: {getattr(uri, 'scheme', 'N/A')}, Path: {getattr(uri, 'path', 'N/A')}")
        raise ValueError(f"Unsupported URI scheme: {getattr(uri, 'scheme', 'unknown')}. Expected 'ui://' scheme for Apps SDK widgets.")

    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        """
        List available prompts.
        Each prompt can have optional arguments to customize its behavior.
        """
        logger.info("Listing prompts")
        # TODO: Check where and how this is used, and how to optimize this.
        # Check postgres and sqlite servers.
        return [
            types.Prompt(
                name="duckdb-motherduck-initial-prompt",
                description="A prompt to initialize a connection to duckdb or motherduck and start working with it",
            ),
            types.Prompt(
                name="medicair-starting-prompt",
                description="A second prompt template for DuckDB/MotherDuck interactions",
            )
        ]

    @server.get_prompt()
    async def handle_get_prompt(
        name: str, arguments: dict[str, str] | None
    ) -> types.GetPromptResult:
        """
        Generate a prompt by combining arguments with server state.
        The prompt includes all current notes and can be customized via arguments.
        """
        logger.info(f"Getting prompt: {name}::{arguments}")
        # TODO: Check where and how this is used, and how to optimize this.
        # Check postgres and sqlite servers.
        if name == "duckdb-motherduck-initial-prompt":
            return types.GetPromptResult(
                description="Initial prompt for interacting with DuckDB/MotherDuck",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(type="text", text=PROMPT_TEMPLATE),
                    )
                ],
            )
        elif name == "medicair-starting-prompt":
            return types.GetPromptResult(
                description="A second prompt template for DuckDB/MotherDuck interactions",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(type="text", text=MOTHERDUCK_PROMPT),
                    )
                ],
            )
        else:
            raise ValueError(f"Unknown prompt: {name}")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        List available tools with OpenAI metadata for Apps SDK integration.
        Each tool specifies its arguments using JSON Schema validation.
        """
        logger.info("Listing tools")
        return [
            types.Tool(
                name="query",
                description=MOTHERDUCK_PROMPT + "\n\nUse this tool to execute SQL queries on the MedicAir database. The results will be displayed in a formatted widget.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SQL query to execute that is a dialect of DuckDB SQL",
                        },
                    },
                    "required": ["query"],
                },
                _meta={
                    "openai/outputTemplate": "ui://widget/query-results.html",
                    "openai/toolInvocation/invoking": "Eseguendo query SQL...",
                    "openai/toolInvocation/invoked": "Query eseguita con successo",
                },
            ),
        ]

    @server.call_tool()
    async def handle_tool_call(
        name: str, arguments: dict | None
    ) -> CallToolResult:
        """
        Handle tool execution requests with structured content for Apps SDK.
        Returns CallToolResult with both content (human-readable) and structuredContent (machine-readable).
        When outputTemplate is specified in tool metadata, OpenAI Apps SDK automatically passes
        structuredContent to the widget via window.openai.toolOutput.
        """
        logger.info(f"Calling tool: {name}::{arguments}")
        try:
            if name == "query":
                if arguments is None:
                    return CallToolResult(
                        content=[
                            types.TextContent(type="text", text="Error: No query provided")
                        ]
                    )
                
                # Get both formatted string and structured data
                formatted_output, structured_data = db_client.query_with_data(arguments["query"])
                
                # Create TextContent with formatted output
                text_content = types.TextContent(type="text", text=formatted_output)
                
                # Return CallToolResult with both content and structuredContent
                # Following the MCP SDK Python format for Apps SDK integration
                logger.info(f"Returning structured content with {len(structured_data.get('rows', []))} rows")
                return CallToolResult(
                    content=[text_content],
                    structuredContent={"queryResults": structured_data}
                )

            return CallToolResult(
                content=[
                    types.TextContent(type="text", text=f"Unsupported tool: {name}")
                ]
            )

        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            raise ValueError(f"Error executing tool {name}: {str(e)}")

    initialization_options = InitializationOptions(
        server_name="medicair",
        server_version=SERVER_VERSION,
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )

    return server, initialization_options
