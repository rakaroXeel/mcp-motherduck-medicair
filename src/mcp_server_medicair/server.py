import logging
from pathlib import Path
from pydantic import AnyUrl
from typing import Literal
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from .configs import SERVER_VERSION
from .database import DatabaseClient
from .prompt import PROMPT_TEMPLATE, MOTHERDUCK_PROMPT


logger = logging.getLogger("mcp_server_medicair")


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
        """
        logger.info(f"Reading resource: {uri}")
        if uri.scheme == "ui" and uri.path == "/widget/query-results.html":
            # Determina il percorso del file widget relativo alla root del progetto
            # Il file si trova in public/query-results-widget.html dalla root del progetto
            current_file = Path(__file__)
            # Risali fino alla root del progetto (src/mcp_server_medicair/server.py -> src -> root)
            project_root = current_file.parent.parent.parent
            widget_path = project_root / "public" / "query-results-widget.html"
            
            if widget_path.exists():
                logger.info(f"Loading widget from: {widget_path}")
                return widget_path.read_text(encoding="utf-8")
            else:
                logger.error(f"Widget file not found at: {widget_path}")
                raise ValueError(f"Widget file not found: {widget_path}")
        
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

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
                description="Use this to execute a query on the MotherDuck or DuckDB database",
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
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """
        Handle tool execution requests with structured content for Apps SDK.
        Tools can modify server state and notify clients of changes.
        """
        logger.info(f"Calling tool: {name}::{arguments}")
        try:
            if name == "query":
                if arguments is None:
                    return [
                        types.TextContent(type="text", text="Error: No query provided")
                    ]
                
                # Get both formatted string and structured data
                formatted_output, structured_data = db_client.query_with_data(arguments["query"])
                
                # Create TextContent with formatted output
                text_content = types.TextContent(type="text", text=formatted_output)
                
                # Add structured content as metadata for Apps SDK
                # The structured data will be available to the widget via window.openai.toolOutput.queryResults
                if hasattr(text_content, '_meta'):
                    text_content._meta = {"queryResults": structured_data}
                else:
                    # If _meta is not available, we'll include it in the response differently
                    # For now, return both text and try to include structured data
                    logger.info(f"Structured data prepared: {len(structured_data.get('rows', []))} rows")
                
                return [text_content]

            return [types.TextContent(type="text", text=f"Unsupported tool: {name}")]

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
