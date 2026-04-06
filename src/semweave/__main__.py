"""Entry point for running SemWeave as a module: python -m semweave"""

from semweave.mcp_server.server import mcp


def main():
    mcp.run()


if __name__ == "__main__":
    main()
