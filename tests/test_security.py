"""Security controls (docs/security/threat-model.md): read-only SQL that cannot touch the filesystem, timeouts, …"""
import pandas as pd
import pytest


@pytest.fixture()
def wh(tmp_path):
    from vlkit.de.warehouse import Warehouse
    w = Warehouse(tmp_path / "wh.duckdb", lake=tmp_path / "lake")
    w.write("gold", "t", pd.DataFrame({"a": range(10), "b": list("abcdefghij")}))
    w.close()
    ro = Warehouse.readonly(tmp_path / "wh.duckdb", lake=tmp_path / "lake")
    yield ro
    ro.close()


@pytest.fixture()
def secret_file(tmp_path):
    p = tmp_path / "secret.csv"
    p.write_text("token\nTOP-SECRET-123\n")
    return p


ATTACKS = [
    "DROP TABLE gold.t", "SELECT 1; DROP TABLE gold.t", "INSERT INTO gold.t VALUES (1,'x')",
    "SELECT * FROM read_csv('{f}')", "SELECT * FROM sniff_csv('{f}')", "SELECT * FROM '{f}'", 'SELECT * FROM "{f}"',
    "SELECT * FROM parquet_scan('{f}')", "SELECT * FROM glob('/etc/*')", "SELECT current_setting('home_directory')",
    "SELECT * FROM query('SELECT 1')", "ATTACH '{f}' AS x", "COPY gold.t TO '{f}'", "SET enable_external_access=true",
    "WITH x AS (SELECT 1) SELECT * FROM x JOIN '{f}' ON true", "SELECT * FROM gold.t, '{f}'",
]


@pytest.mark.parametrize("q", ATTACKS)
def test_sql_attacks_refused(wh, secret_file, q):
    with pytest.raises(PermissionError):
        wh.sql(q.format(f=secret_file))


def test_readonly_connection_is_hardened(wh, secret_file):
    assert wh.hardened
    # even bypassing the regex layer, the engine refuses file access and writes
    import duckdb
    with pytest.raises(duckdb.Error):
        wh.con.execute(f"SELECT * FROM sniff_csv('{secret_file}')").fetchall()
    with pytest.raises(duckdb.Error):
        wh.con.execute("CREATE TABLE gold.x AS SELECT 1").fetchall()


def test_legit_queries_still_work(wh):
    assert wh.sql("SELECT count(*) n FROM gold.t")["n"][0] == 10
    assert len(wh.sql('SELECT * FROM gold."t" WHERE b IN (\'a\', \'b\')')) == 2
    assert wh.sql("SELECT 'dataset' AS s, a FROM gold.t ORDER BY a LIMIT 1")["s"][0] == "dataset"
    assert len(wh.sql("DESCRIBE gold.t")) == 2
    assert len(wh.sql("SELECT * FROM gold.t", limit=3)) == 3


def test_sql_timeout(wh):
    with pytest.raises(TimeoutError):
        wh.sql("SELECT count(*) FROM range(1000000000) a, range(1000) b", timeout_s=0.5)


def test_api_sql_rejects_file_read(tmp_path, monkeypatch, secret_file):
    from fastapi.testclient import TestClient
    from api.main import app
    c = TestClient(app)
    r = c.post("/api/sql", json={"query": f"SELECT * FROM sniff_csv('{secret_file}')"})
    assert r.status_code == 403 and "TOP-SECRET" not in r.text


# ------------------------------------------------------------------ T062/T063 SSRF + local path guards (API sources)
def _src(kind, uri, **opts):
    from vlkit.de.sources import Source
    return Source("s", kind, uri, opts)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000/api/health", "http://localhost/", "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/admin", "http://192.168.1.1/", "http://[::1]/", "http://0.0.0.0/", "http://100.64.0.1/",
    "file:///etc/passwd", "gopher://example.com/", "http://user:pw@example.com/",
])
def test_ssrf_urls_rejected(url, monkeypatch):
    from vlkit.de.netguard import SourceRejected, guard_source
    monkeypatch.delenv("KIT_ALLOW_PRIVATE_NET", raising=False)
    for kind in ("api", "scrape", "social"):
        with pytest.raises(SourceRejected):
            guard_source(_src(kind, url))


def test_public_url_and_trends_allowed(monkeypatch):
    from vlkit.de import netguard
    monkeypatch.setattr(netguard.socket, "getaddrinfo", lambda h, p, **k: [(2, 1, 6, "", ("93.184.216.34", p))])
    s = _src("api", "https://api.worldbank.org/v2/country/VN")
    netguard.guard_source(s)
    assert s.options["_net_guard"] is True
    netguard.guard_source(_src("social", "trends:lam phat|lai suat"))


def test_dns_rebinding_to_private_rejected(monkeypatch):
    from vlkit.de import netguard
    monkeypatch.setattr(netguard.socket, "getaddrinfo", lambda h, p, **k: [(2, 1, 6, "", ("10.1.2.3", p))])
    with pytest.raises(netguard.SourceRejected):
        netguard.guard_source(_src("scrape", "https://evil.example/"))


def test_redirect_to_private_blocked_by_hook():
    import httpx
    from vlkit.de.netguard import SourceRejected, httpx_hooks
    s = _src("api", "https://example.org", _net_guard=True)

    def handler(request):
        if request.url.host == "example.org":
            return httpx.Response(302, headers={"location": "http://127.0.0.1:8000/secret"})
        return httpx.Response(200, text="SECRET")
    from vlkit.de import netguard
    orig = netguard.check_host
    netguard.check_host = lambda h, p=None: orig(h, p) if h != "example.org" else None
    try:
        with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True, event_hooks=httpx_hooks(s)) as c:
            with pytest.raises(SourceRejected):
                c.get("https://example.org/")
    finally:
        netguard.check_host = orig


def test_option_abuse_rejected(monkeypatch):
    from vlkit.de import netguard
    monkeypatch.setattr(netguard.socket, "getaddrinfo", lambda h, p, **k: [(2, 1, 6, "", ("93.184.216.34", p))])
    with pytest.raises(netguard.SourceRejected):   # would send an LLM key to an attacker URL
        netguard.guard_source(_src("api", "https://evil.example/", auth_env="GROQ_API_KEY"))
    netguard.guard_source(_src("api", "https://ok.example/", auth_env="KIT_TOKEN_WB"))
    with pytest.raises(netguard.SourceRejected):
        netguard.guard_source(_src("scrape", "https://ok.example/", render_js=True))
    with pytest.raises(netguard.SourceRejected):
        netguard.guard_source(_src("scrape", "https://ok.example/", urls=["http://127.0.0.1/"]))


def test_local_paths_confined(kit_root, tmp_path):
    from vlkit.de.netguard import SourceRejected, guard_source
    ok = _src("file", "data/practice/synthetic_messy_bds.csv")
    guard_source(ok)
    assert ok.uri == str((kit_root / "data/practice/synthetic_messy_bds.csv").resolve())
    for bad in ("/etc/passwd", "../../etc/passwd", str(kit_root / ".env"), str(kit_root / "web" / ".env.local"),
                "data/../../../etc/hosts"):
        with pytest.raises(SourceRejected):
            guard_source(_src("file", bad))
    link = kit_root / "data" / "_tmp_link_test"
    try:
        link.symlink_to("/etc")
        with pytest.raises(SourceRejected):
            guard_source(_src("file", str(link / "hostname")))
    finally:
        link.unlink(missing_ok=True)
    with pytest.raises(SourceRejected):
        guard_source(_src("sql", "sqlite:////etc/some.db"))
    with pytest.raises(SourceRejected):
        guard_source(_src("sql", "postgresql://u:p@127.0.0.1:5432/db"))
    with pytest.raises(SourceRejected):
        guard_source(_src("cv", "scenarios/cv_counting/x.csv", out="/tmp/pwn.csv"))


def test_api_ingest_rejects_ssrf_and_paths(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("KIT_OUT_DIR", str(tmp_path / "out"))
    from api.main import app
    c = TestClient(app)
    for src in ({"name": "a", "kind": "api", "uri": "http://169.254.169.254/latest/meta-data/"},
                {"name": "b", "kind": "file", "uri": "/etc/passwd"}):
        r = c.post("/api/ingest", json={"dataset": "d", "sources": [src]})
        assert r.status_code == 422 and "blocked" in r.text


def test_zip_bomb_limit(tmp_path, monkeypatch):
    import zipfile
    from vlkit.de import connectors
    z = tmp_path / "b.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        f.writestr("a.csv", "x\n" + "0\n" * 200_000)
    monkeypatch.setattr(connectors, "MAX_UNZIPPED_BYTES", 1000)
    with pytest.raises(ValueError):
        connectors.ingest_file(_src("file", str(z)))
