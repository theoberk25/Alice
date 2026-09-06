# Enterprise readiness for backend integration

Observed from Jared's Mac on the existing first-light LAN. No permission release,
Wazuh user or role was modified. User clarified that the intended identity is a
simulated Sentinel AFB operator, not a Wazuh administrative login.

## Running services

Docker engine 28.3.2; Wazuh manager, indexer and dashboard containers use 4.14.7.
They were already running when inspected; indexer cluster health was green.
Started the enterprise console with `.venv/bin/python -u -m lab.enterprise_sim.console`.
It listens on 127.0.0.1:8787 and reports LIVE_INDEXER. Its /, /api/state and
/api/edge returned 200. Wazuh dashboard https://127.0.0.1/ returned 302 to login.

Live data: alice-permissions has 3 releases (42/43 superseded, 44 current);
alice-audit-* has 48 authored simulation records; wazuh-alerts-* had 259 records
at inspection. These 48 records are not the live Pi ledger: reading the console's
Live edge tab directly polls the Pi and does not prove ingestion into Wazuh.

## Existing operator

Use simulated SSgt A. Okafor (ssgt.a.okafor), electrician, 899-CES/POWER-PRO,
through elec-agent-01. Live release 44 binds that agent to the responsible user
and delegates from msgt.d.reyes. It grants read_meter/query_status/read_logs for
FEEDER-A-RTU, FEEDER-B-RTU and METER-GW-01, and conditional voltage-setpoint
changes for the two feeders. Published voltage limits remain synthetic demo
placeholders, not electrical approval. No new Wazuh login is necessary for this
simulated identity. Agent authentication remains the signed terminal request.

## Backend network settings and gaps

- Mac LAN address 192.168.50.50. Indexer endpoint port 9200; manager API 55000;
  dashboard HTTPS 443. Pi 192.168.50.20:8080. Theo keeps his own technician UI.
- From the Pi: dashboard 302, indexer 401, manager 401 without credentials.
  This proves network/service reachability only. Probes disabled certificate
  checks; authenticated backend TLS is NOT established by those results.
- Indexer certificate SAN is DNS:wazuh.indexer, not the Mac's LAN IP. Backend
  must trust the existing CA and resolve that name to the Mac, or use a properly
  issued certificate with the chosen endpoint name. Do not adopt skip-verification
  as the backend configuration.
- Existing alice_pi account and indexer role are present. Credentials were not
  retrieved or distributed in this session. Its current audit write grant is
  broader than append-only; immutable ingestion needs its own enforcement.
- Pi runs first-light-jared-2 with set_light_state/ESP-LIGHT-01 grants. Enterprise
  release 44 has no matching light grant, and its broader schemas differ. Define
  the signed release/adapter contract before activating SIEM data on the Pi.
- Preserve local Pi ledger/evidence and client signing keys through deployment.
  Backend should fetch trusted inputs and publish bound audit; Theo's dashboard
  observes Pi state. The two dashboards do not independently authorize sync.

Next integration proof: same operator/request identity on both surfaces, actual
accepted release generation/digest on Pi, one correlated Pi audit record indexed
upstream, receipt verified, no duplicate on retry, and continued OFFLINE operation
with explicitly cached state. Current first-light scoring remains a fixture.
