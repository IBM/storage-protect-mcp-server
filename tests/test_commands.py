from sp_mcp_server.commands.system.server import QueryServerStatus
from sp_mcp_server.commands.operations.misc import QueryActivityLog
from sp_mcp_server.commands.servermon import RunServerMon


class DummyCli:
    def __init__(self, stdout="Output", stderr="", code=0):
        self.stdout = stdout
        self.stderr = stderr
        self.code = code
        self.calls = []

    def execute(self, command):
        self.calls.append(command)
        return self.stdout, self.stderr, self.code


def test_query_server_status():
    cli = DummyCli(stdout="STATUS OK")
    cmd = QueryServerStatus(cli)

    result = cmd.execute({})

    assert cli.calls == ["QUERY STATUS"]
    assert result == "STATUS OK"


def test_query_activity_log_with_search_only():
    cli = DummyCli()
    cmd = QueryActivityLog(cli)

    cmd.execute({"search": "ANR2968E"})

    assert cli.calls == ["QUERY ACTLOG SEARCH=ANR2968E"]


def test_query_activity_log_with_time_filters():
    cli = DummyCli()
    cmd = QueryActivityLog(cli)

    cmd.execute(
        {
            "search": "ERROR",
            "begindate": "2026-07-15",
            "enddate": "2026-07-16",
            "begintime": "08:00",
            "endtime": "09:00",
        }
    )

    assert cli.calls == [
        "QUERY ACTLOG SEARCH=ERROR BEGINDATE=2026-07-15 ENDDATE=2026-07-16 BEGINTIME=08:00 ENDTIME=09:00"
    ]


def test_run_servermon_forwards_args():
    cli = DummyCli(stdout="SERVERMON OK")
    cmd = RunServerMon(cli)

    result = cmd.execute({"args": ["-standard", "-dbonly"]})

    assert cli.calls == [["-standard", "-dbonly"]]
    assert result == "SERVERMON OK"
