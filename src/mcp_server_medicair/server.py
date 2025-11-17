import json
import logging
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from pydantic import AnyUrl
from typing import Literal
import mcp.types as types
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
    ):
        """
        Handle tool execution requests with structured content for Apps SDK.
        Returns a dict with content array containing text and embedded_resource.
        This format matches what ChatGPT/OpenAI Apps SDK expects for widget data.
        """
        logger.info(f"Calling tool: {name}::{arguments}")
        try:
            if name == "query":
                if arguments is None:
                    return [
                        types.TextContent(type="text", text="Error: No query provided")
                    ]
                
                # Get both formatted string and structured data
                query_sql = arguments["query"]
                formatted_output, structured_data = db_client.query_with_data(query_sql)
                
                # Extract data
                columns = structured_data.get("columns", [])
                rows = structured_data.get("rows", [])
                row_count = len(rows)
                
                # Log the parsed content that will be passed to the widget
                logger.info(f"📤 Preparing content for widget component")
                logger.info(f"📤 Data structure: columns={len(columns)}, rows={len(rows)}, rowCount={row_count}")
                logger.info(f"📤 Columns: {columns}")
                logger.info(f"📤 Rows sample (first 2): {rows[:2] if len(rows) > 0 else 'No rows'}")
                
                # Ensure rows are properly formatted as array of arrays
                # Convert each row to a list and handle JSON-serializable values
                def json_serialize_value(value):
                    """Convert value to JSON-serializable format.
                    Preserves original types (int, float, bool, str) and only converts
                    non-JSON-serializable types (datetime, Decimal, bytes, complex types).
                    """
                    # Handle None
                    if value is None:
                        return None
                    
                    # Handle datetime/date types
                    if isinstance(value, (datetime, date)):
                        return value.isoformat()
                    
                    # Handle Decimal
                    if isinstance(value, Decimal):
                        return float(value)
                    
                    # Handle bytes
                    if isinstance(value, (bytes, bytearray)):
                        return value.hex()
                    
                    # Handle DuckDB LIST/ARRAY types - recursively serialize
                    if isinstance(value, (list, tuple)):
                        return [json_serialize_value(item) for item in value]
                    
                    # Handle DuckDB STRUCT/MAP types - recursively serialize
                    if isinstance(value, dict):
                        return {str(k): json_serialize_value(v) for k, v in value.items()}
                    
                    # Preserve original types - DO NOT convert to string
                    if isinstance(value, (int, float, bool, str)):
                        return value
                    
                    # For any other type, convert to string as fallback
                    logger.info(f"Converting unknown type {type(value)} to string: {value}")
                    return str(value)
                
                # Convert rows to ensure they're arrays of arrays with JSON-serializable values
                formatted_rows = [
                    [json_serialize_value(cell) for cell in row]
                    for row in rows
                ]
                
                # Build MCP format response - return list of content objects
                # MCP expects a list of TextContent and EmbeddedResource objects, not a dict
                # OpenAI Apps SDK expects data wrapped in {"queryResults": {...}} for the widget
                widget_data = {
                    "columns": columns,
                    "rows": formatted_rows
                }
                
                # Wrap data in queryResults key as expected by OpenAI Apps SDK
                embedded_data = {
                    "queryResults": widget_data
                }
                
                logger.info(f"📤 Sending EmbeddedResource with data: queryResults={{columns: {len(columns)}, rows: {len(formatted_rows)}}}")
                logger.debug(f"📤 EmbeddedResource JSON preview: {json.dumps(embedded_data)[:200]}...")
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"Risultati della query: {row_count} righe trovate.\n\n{formatted_output}"
                    ),
                    types.EmbeddedResource(
                        type="resource",
                        resource={
                            "uri": "ui://widget/query-results.html",
                            "mimeType": "application/json",
                            "text": json.dumps(embedded_data)
                        }
                    )
                ]

            return [
                types.TextContent(type="text", text=f"Unsupported tool: {name}")
            ]

        except Exception as e:
            logger.info(f"❌ Widget Error: {e}")
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
