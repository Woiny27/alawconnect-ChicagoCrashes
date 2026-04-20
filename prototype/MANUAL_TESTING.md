# Manual Testing Seeds and Access Models

This file captures user-provided incident seeds and access models for validating
legacy portal automation and high-volume sequential scanners.

Important:
- Treat all entries as testing hints and verify against official portals.
- Use only authorized/public workflows and follow each portal's terms.
- Avoid storing or publishing private personal data from returned records.

## Recent Incident Seeds (User-Provided)

### Detroit, MI
- Incident seed: Rosa Parks Blvd fatal crash (Feb 22, 2026)
- Incident seed: Woodward Ave and E Adams Ave two-car crash (Apr 2026)
- Source note: Ratton Law Group accident news

### St. Louis / Missouri
- Report `250111396`: crash occurred Mar 15, 2026 (New Madrid, Troop E)
- Report `250201258`
- Sequential range hint: `2502xxxxx` currently active for high-volume lookup tests
- Source note: Missouri State Highway Patrol crash reports

## Automated Extraction Access Models

### Philadelphia (PA State)
- Modernization profile: Legacy portal
- Access method: Sequential search
- Endpoint note: PA State Police crash portal (name/date or Incident Number)
- Provider fit: `LegacyPortalProvider`

### Austin, TX
- Modernization profile: Modern API
- Access method: Request portal
- Endpoint note: Austin APD incident database (reported as last 18 months)
- Provider fit: API provider pattern (`aiohttp`/REST)

### Phoenix, AZ
- Modernization profile: Modern API
- Access method: Self-service portal
- Endpoint note: Phoenix Police public records system (reported as Mar 2026 rollout)
- Provider fit: API provider pattern plus status polling

### Missouri (St. Louis)
- Modernization profile: Legacy portal
- Access method: Sequential ID loop
- Endpoint note: MSHP crash reports list (reported 1,200+ persons in recent searches)
- Provider fit: `SequentialWorkerProvider` plus `LegacyPortalProvider`

## Suggested Test Flow

1. Validate one known seed ID manually in browser.
2. Confirm provider field mapping and parser output.
3. Run a narrow sequential range (for example, 100-500 IDs).
4. Enable distributed range scanning only after parser stability is confirmed.
5. Log successful patterns and rejection markers for each jurisdiction.
