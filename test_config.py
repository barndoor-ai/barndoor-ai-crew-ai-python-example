from pathlib import Path
from dotenv import load_dotenv
import barndoor.sdk as bd
from barndoor.sdk.config import BarndoorConfig, get_config

load_dotenv(Path(__file__).parent / ".env")
async def main():
    sdk = await bd.login_interactive()
    config = get_config()
    print(f"API Base URL: {config.api_base_url}")
    print(f"MCP Base URL: {config.mcp_base_url}")
    print(f"Config: {config.__dict__}")
    await sdk.aclose()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())