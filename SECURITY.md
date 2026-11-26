# Security reporting

For a vulnerability, use [GitHub private vulnerability reporting](https://github.com/forensicxlab/scenari-mcp/security/advisories/new)
when enabled, or contact the ForensicXlab maintainer privately through the
[repository](https://github.com/forensicxlab/scenari-mcp). Do not post
credentials, real forensic evidence, access-bearing URLs or exploit details in
a public issue. A dedicated reporting address has not been configured yet.

Include the MCP version, Python version, Scenari/Dokiel versions, affected tool
and a minimal reproduction using synthetic data. Remove secrets from logs.

The MCP runs locally over stdio and uses the Scenari account supplied by the
operator. Writes default to disabled. Use a dedicated, appropriately restricted
account for regular authoring. The localhost Compose deployment is for evaluation;
shared deployments need HTTPS, suitable permissions and managed backups.
