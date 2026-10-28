"""Local stdio MCP service for synthetic evidence review; no actuator tools."""
from mcp.server.fastmcp import FastMCP
from .fruit import CASES, run_fruit_fixture
from .lineage import verify
from .sprint import explain_belief as _explain, review_episode as _episode, review_simulation_episode as _simulation

mcp = FastMCP('CoreXense-N')


@mcp.tool()
def list_scenarios() -> dict:
    """List supported synthetic fruit decision scenarios and explicit limits."""
    return {'scenarios':list(CASES), 'physical_execution':False, 'cloud_inference':False}


@mcp.tool()
def review_scenario(case: str) -> dict:
    """Run bounded local evidence qualification, returning a decision and trace."""
    report, ledger = run_fruit_fixture(case)
    verify(ledger.records, report['terminal_hash'])
    return {'report':report, 'trace':ledger.records}


@mcp.tool()
def explain_belief(case: str) -> dict:
    """Explain delayed or conflicting synthetic evidence with TWS-Belief."""
    return _explain(case)


@mcp.tool()
def review_episode(case: str) -> dict:
    """Review a synthetic fruit episode; cloud use is controlled by the host configuration."""
    return _episode(case)


@mcp.tool()
def review_simulation_episode(report: dict, trace: list[dict]) -> dict:
    """Audit an explicit FIRA simulation replay bundle; never authorize execution."""
    return _simulation(report, trace)


def main():
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
