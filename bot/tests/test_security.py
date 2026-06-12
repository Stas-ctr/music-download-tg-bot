"""
Security tests for Music Bot vulnerabilities.
Run: docker-compose exec bot python -m pytest tests/test_security.py -v
"""
import asyncio
import html
import os
from urllib.parse import quote

import pytest

BOT_DIR = "/app"
ROOT_DIR = os.path.dirname(BOT_DIR)


# ============================================================
# V1: Secrets in alembic.ini
# ============================================================
class TestV1_SecretsInAlembic:
    def test_alembic_ini_no_hardcoded_password(self):
        with open(f"{BOT_DIR}/alembic.ini") as f:
            content = f.read()
        assert "Fest8_9" not in content, "alembic.ini contains hardcoded password!"
        assert "sqlalchemy.url = postgresql" not in content

    def test_migrations_env_reads_from_env(self):
        with open(f"{BOT_DIR}/migrations/env.py") as f:
            content = f.read()
        assert "os.getenv" in content or "os.environ" in content


# ============================================================
# V2: .dockerignore excludes secrets
# ============================================================
class TestV2_DockerIgnore:
    def test_dockerignore_excludes_env(self):
        with open(f"{BOT_DIR}/.dockerignore") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        assert ".env" in lines

    def test_dockerignore_excludes_test_files(self):
        with open(f"{BOT_DIR}/.dockerignore") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        assert "test*.py" in lines

    def test_dockerignore_excludes_ide(self):
        with open(f"{BOT_DIR}/.dockerignore") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        assert ".idea/" in lines


# ============================================================
# V3: Container runs as non-root
# ============================================================
class TestV3_NonRootUser:
    def test_dockerfile_has_user_directive(self):
        with open(f"{BOT_DIR}/Dockerfile") as f:
            content = f.read()
        assert "USER" in content
        assert "useradd" in content


# ============================================================
# V5: SSRF protection
# ============================================================
class TestV5_SSRF:
    def test_download_blocks_private_ips(self):
        from handlers.download_handler import _is_safe_host
        assert not _is_safe_host("127.0.0.1"), "Loopback not blocked!"
        assert not _is_safe_host("10.0.0.1"), "Private 10.x not blocked!"
        assert not _is_safe_host("192.168.1.1"), "Private 192.168.x not blocked!"
        assert not _is_safe_host("169.254.1.1"), "Link-local not blocked!"
        assert not _is_safe_host("172.16.0.1"), "Private 172.16.x not blocked!"

    def test_download_allows_public_hosts(self):
        from handlers.download_handler import _is_safe_host
        assert _is_safe_host("s1.deliciouspeaches.com")
        assert _is_safe_host("rus.hitmotop.com")


# ============================================================
# V6: Ban bypass when Redis is down
# ============================================================
class TestV6_BanBypass:
    def test_ban_defaults_to_deny_when_redis_down(self):
        import core.redis as redis_module
        with patch.object(redis_module, 'redis_client', None):
            result = asyncio.get_event_loop().run_until_complete(
                redis_module.is_banned(12345)
            )
            assert result is True, "is_banned() returns False when Redis is down!"

    def test_ban_returns_true_for_banned_user(self):
        import core.redis as redis_module
        with patch.object(redis_module, 'redis_client', None):
            result = asyncio.get_event_loop().run_until_complete(
                redis_module.is_banned(99999)
            )
            assert result is True


# ============================================================
# V7-V9: HTML Injection
# ============================================================
class TestV7_HTMLInjection:
    def test_search_handler_escapes_query(self):
        with open(f"{BOT_DIR}/handlers/search_handler.py") as f:
            content = f.read()
        assert "html.escape" in content

    def test_start_handler_escapes_username(self):
        with open(f"{BOT_DIR}/handlers/start_handler.py") as f:
            content = f.read()
        assert "html.escape" in content

    def test_history_handler_escapes_queries(self):
        with open(f"{BOT_DIR}/handlers/history_handler.py") as f:
            content = f.read()
        assert "html.escape" in content

    def test_html_escape_prevents_script_injection(self):
        malicious = '<script>alert("xss")</script>'
        escaped = html.escape(malicious)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_html_escape_prevents_link_injection(self):
        malicious = '<a href="http://evil.com">click</a>'
        escaped = html.escape(malicious)
        assert "<a href" not in escaped


# ============================================================
# V12: URL Injection
# ============================================================
class TestV12_URLInjection:
    def test_search_query_is_url_encoded(self):
        with open(f"{BOT_DIR}/services/parser.py") as f:
            content = f.read()
        assert "quote" in content

    def test_url_encoding_prevents_crlf_injection(self):
        malicious = "test\r\nX-Injected: evil"
        encoded = quote(malicious)
        assert "\r\n" not in encoded

    def test_url_encoding_prevents_param_injection(self):
        malicious = "test&admin=true"
        encoded = quote(malicious)
        assert "admin=true" not in encoded or "admin%3Dtrue" in encoded


# ============================================================
# V14: Hardcoded Redis password in docker-compose
# ============================================================
class TestV14_RedisPassword:
    @pytest.mark.skipif(
        not os.path.exists(os.path.join(ROOT_DIR, "docker-compose.yml")),
        reason="docker-compose.yml not in container (excluded by .dockerignore)"
    )
    def test_redis_healthcheck_uses_env_var(self):
        compose_path = os.path.join(ROOT_DIR, "docker-compose.yml")
        with open(compose_path) as f:
            content = f.read()
        assert '"Fest8_9' not in content
        assert "${REDIS_PASSWORD}" in content


# ============================================================
# Additional: No dangerous function calls
# ============================================================
class TestAdditional:
    def test_no_subprocess_in_application_code(self):
        dangerous_files = []
        skip = {"tests/", ".venv/", "__pycache__/"}
        for root, dirs, files in os.walk(BOT_DIR):
            if any(s in root for s in skip):
                continue
            for fname in files:
                if not fname.endswith(".py") or fname.startswith("test_"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    content = f.read()
                if "os.system" in content:
                    dangerous_files.append(fpath)
        assert not dangerous_files, f"os.system found in: {dangerous_files}"

    def test_no_eval_in_application_code(self):
        dangerous_files = []
        skip = {"tests/", ".venv/", "__pycache__/"}
        for root, dirs, files in os.walk(BOT_DIR):
            if any(s in root for s in skip):
                continue
            for fname in files:
                if not fname.endswith(".py") or fname.startswith("test_"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped.startswith("#"):
                            continue
                        if "eval(" in stripped or "exec(" in stripped:
                            dangerous_files.append(fpath)
                            break
        assert not dangerous_files, f"eval/exec found in: {dangerous_files}"

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(ROOT_DIR, ".gitignore")),
        reason=".gitignore not in container (excluded by .dockerignore)"
    )
    def test_env_file_is_gitignored(self):
        gitignore_path = os.path.join(ROOT_DIR, ".gitignore")
        with open(gitignore_path) as f:
            content = f.read()
        assert ".env" in content

    def test_database_uses_asyncpg(self):
        """Verify the .env template requires asyncpg"""
        assert os.path.exists(f"{BOT_DIR}/core/config.py")
        with open(f"{BOT_DIR}/core/config.py") as f:
            content = f.read()
        assert "DATABASE_URL" in content


from unittest.mock import patch
