import logging
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
        List available resources. Currently no resources are exposed.
        """
        logger.info("Listing resources")
        return []

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
        List available tools.
        Each tool specifies its arguments using JSON Schema validation.
        """
        logger.info("Listing tools")
        return [
            types.Tool(
                name="query",
                description=MOTHERDUCK_PROMPT + "\n\nUse this tool to execute SQL queries on the MedicAir database.",
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
            ),
        ]

    @server.call_tool()
    async def handle_tool_call(
        name: str, arguments: dict | None
    ):
        """
        Handle tool execution requests.
        Returns text content with query results.
        """
        logger.info(f"Calling tool: {name}::{arguments}")
        try:
            if name == "query":
                if arguments is None:
                    return [
                        types.TextContent(type="text", text="Error: No query provided")
                    ]
                
                query_sql = arguments["query"]
                formatted_output, structured_data = db_client.query_with_data(query_sql)
                
                row_count = len(structured_data.get("rows", []))
                
                logger.info(f"Query executed: {row_count} rows found")
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"Risultati della query: {row_count} righe trovate.\n\n{formatted_output}"
                    )
                ]

            return [
                types.TextContent(type="text", text=f"Unsupported tool: {name}")
            ]

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
