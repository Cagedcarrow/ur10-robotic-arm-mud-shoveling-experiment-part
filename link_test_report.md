# UR10 Link Test Report

## 1. Metadata

| Field | Value |
| --- | --- |
| Started at | `2026-05-08T09:54:05.025265+08:00` |
| Finished at | `2026-05-08T09:54:05.068574+08:00` |
| Robot IP | `10.160.9.21` |
| Host IP | `10.160.9.100` |
| External Control Port | `50002` |
| Safety Mode | `read_only_tcp_connect_no_rtde_recipe_no_motion_command` |

## 2. Check Results

| Check | Status | Message |
| --- | --- | --- |
| Ping | `PASS` | Robot replied to ICMP ping. |
| Local 50002 listener | `WARN` | Local system is not listening on External Control port 50002. |
| Current robot connections | `WARN` | Current TCP connections to the robot or RTDE port were found. |
| WSL check | `WARN` | WSL detected; WSL2 NAT may prevent the robot from connecting to a listener inside WSL. |
| TCP 29999 | `PASS` | TCP port accepted a connection. |
| TCP 30001 | `PASS` | TCP port accepted a connection. |
| TCP 30002 | `PASS` | TCP port accepted a connection. |
| TCP 30003 | `PASS` | TCP port accepted a connection. |
| TCP 30004 | `PASS` | TCP port accepted a connection. |

## 3. ss Matches

### Listening on External Control Port

No matches.

### Connections Containing Robot IP

```text
ESTAB      74521  0      172.17.201.231:41154  10.160.9.21:30002 users:(("urscript_interf",pid=145139,fd=18))
FIN-WAIT-2 0      0      172.17.201.231:50926  10.160.9.21:30001                                             
ESTAB      0      0      172.17.201.231:58560  10.160.9.21:29999 users:(("dashboard_clien",pid=145133,fd=18))
FIN-WAIT-2 0      0      172.17.201.231:35074  10.160.9.21:30004                                             
ESTAB      0      0      172.17.201.231:58360  10.160.9.21:30001 users:(("robot_state_hel",pid=145135,fd=18))
FIN-WAIT-2 0      0      172.17.201.231:38112  10.160.9.21:30002
```

### Connections Containing :30004

```text
FIN-WAIT-2 0      0      172.17.201.231:35074  10.160.9.21:30004                                             
```

## 4. Analysis

**Overall:** `WARN`

- `WARN` **External Control port 50002 is not listening locally**: The teach pendant refusal to 10.160.9.100:50002 is expected when ur_robot_driver/script sender is not listening.
- `WARN` **Network path is basically reachable, but RTDE writable resource is occupied**: 29999 and 30004 are connectable while speed_slider_mask is reported. Suspect another RTDE client, Fieldbus, URCap, another PC, or a stale robot-controller state.
- `WARN` **WSL2 networking risk**: WSL2 NAT may prevent the robot from connecting to WSL. Also, 50002 is not listening in this Linux environment.

## 5. Safety Note

This tool only performs ICMP ping, TCP connect probes, and local socket table inspection. It does not use RTDEControlInterface, does not write an RTDE input recipe, and does not send motion commands.
