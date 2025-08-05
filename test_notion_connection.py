from pathlib import Path
from dotenv import load_dotenv
import barndoor.sdk as bd

async def main():
    load_dotenv(Path(__file__).parent / ".env")
    sdk = await bd.BarndoorSDK.login_interactive()
    print("Initiating Notion connection..., ", sdk)
    oauth_url = await bd.BarndoorSDK.initiate_connection(sdk, "10d35278-4608-4e15-9db6-015220b59349")
    print(f"Please visit to authorize Notion: {oauth_url}")
    print("Ensuring Notion connection...")
    await bd.ensure_server_connected(sdk, "notion")
    print("Notion connection ensured")
    servers = await sdk.list_servers()
    print("\nAvailable MCP servers:")
    for s in servers:
        print(f"  • {s.slug:<12} status={s.connection_status}")
    await sdk.aclose()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())