from sp_mcp_server.commands.system.server import QueryServerStatus
from sp_mcp_server.commands.operations.misc import QueryActivityLog
from sp_mcp_server.commands.servermon import RunServerMon

from tests.fixtures import (
    FakeAdmcCli,
    FakeServermonCli,
    SP_OUTPUT_STATUS_OK,
    SP_OUTPUT_SERVERMON_OK,
    CMD_QUERY_STATUS,
    CMD_QUERY_ACTLOG_SEARCH,
    CMD_QUERY_ACTLOG_FILTERED,
    ACTLOG_SEARCH_TERM,
    ACTLOG_BEGIN_DATE,
    ACTLOG_END_DATE,
    ACTLOG_BEGIN_TIME,
    ACTLOG_END_TIME,
    SERVERMON_ARGS_STANDARD_DBONLY,
)


def test_query_server_status():
    cli = FakeAdmcCli(stdout=SP_OUTPUT_STATUS_OK)
    cmd = QueryServerStatus(cli)  # type: ignore[arg-type]

    result = cmd.execute({})

    assert cli.calls == [CMD_QUERY_STATUS]
    assert result == SP_OUTPUT_STATUS_OK


def test_query_activity_log_with_search_only():
    cli = FakeAdmcCli()
    cmd = QueryActivityLog(cli)  # type: ignore[arg-type]

    cmd.execute({"search": "ANR2968E"})

    assert cli.calls == [CMD_QUERY_ACTLOG_SEARCH]


def test_query_activity_log_with_time_filters():
    cli = FakeAdmcCli()
    cmd = QueryActivityLog(cli)  # type: ignore[arg-type]

    cmd.execute(
        {
            "search": ACTLOG_SEARCH_TERM,
            "begindate": ACTLOG_BEGIN_DATE,
            "enddate": ACTLOG_END_DATE,
            "begintime": ACTLOG_BEGIN_TIME,
            "endtime": ACTLOG_END_TIME,
        }
    )

    assert cli.calls == [CMD_QUERY_ACTLOG_FILTERED]


def test_run_servermon_forwards_args():
    cli = FakeServermonCli(stdout=SP_OUTPUT_SERVERMON_OK)
    cmd = RunServerMon(cli)  # type: ignore[arg-type]

    result = cmd.execute({"args": SERVERMON_ARGS_STANDARD_DBONLY})

    assert cli.calls == [SERVERMON_ARGS_STANDARD_DBONLY]
    assert result == SP_OUTPUT_SERVERMON_OK
