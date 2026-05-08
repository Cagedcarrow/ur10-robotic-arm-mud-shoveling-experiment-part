import datetime
import json
import platform
import socket
import subprocess
from pathlib import Path

import rclpy
from rclpy.node import Node


PASS = 'PASS'
WARN = 'WARN'
FAIL = 'FAIL'


class UR10LinkTestNode(Node):
    def __init__(self):
        super().__init__('ur10_link_test_node')
        self.declare_parameter('robot_ip', '10.160.9.21')
        self.declare_parameter('host_ip', '10.160.9.100')
        self.declare_parameter('external_control_port', 50002)
        self.declare_parameter('robot_ports', [29999, 30001, 30002, 30003, 30004])
        self.declare_parameter('report_json', '/root/ur10_ws/link_test_report.json')
        self.declare_parameter('report_md', '/root/ur10_ws/link_test_report.md')
        self.declare_parameter('speed_slider_mask_observed', True)

        self.robot_ip = self.get_parameter('robot_ip').value
        self.host_ip = self.get_parameter('host_ip').value
        self.external_control_port = int(self.get_parameter('external_control_port').value)
        self.robot_ports = [int(port) for port in self.get_parameter('robot_ports').value]
        self.report_json = Path(str(self.get_parameter('report_json').value)).expanduser()
        self.report_md = Path(str(self.get_parameter('report_md').value)).expanduser()
        self.speed_slider_mask_observed = bool(self.get_parameter('speed_slider_mask_observed').value)

    def run(self):
        started_at = datetime.datetime.now(datetime.timezone.utc).astimezone()
        self._log_header(started_at)

        ping_result = self._check_ping(self.robot_ip)
        tcp_results = {str(port): self._check_tcp(self.robot_ip, port) for port in self.robot_ports}
        listen_result = self._check_listening_port(self.external_control_port)
        connections_result = self._check_robot_connections(self.robot_ip)
        wsl_result = self._check_wsl()
        analysis = self._analyze(ping_result, tcp_results, listen_result, connections_result, wsl_result)

        report = {
            'metadata': {
                'started_at': started_at.isoformat(),
                'finished_at': datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
                'platform': platform.platform(),
                'robot_ip': self.robot_ip,
                'host_ip': self.host_ip,
                'external_control_port': self.external_control_port,
                'robot_ports': self.robot_ports,
                'safe_mode': 'read_only_tcp_connect_no_rtde_recipe_no_motion_command',
            },
            'checks': {
                'ping': ping_result,
                'tcp_ports': tcp_results,
                'local_external_control_listener': listen_result,
                'current_robot_connections': connections_result,
                'wsl': wsl_result,
            },
            'analysis': analysis,
        }

        self._write_reports(report)
        self._log_summary(report)
        return report

    def _log_header(self, started_at):
        self.get_logger().info('UR10 link test started at %s' % started_at.isoformat())
        self.get_logger().info('Robot IP: %s, host IP: %s, External Control port: %d' % (
            self.robot_ip, self.host_ip, self.external_control_port))
        self.get_logger().info('Safety: TCP connect diagnostics only; no RTDE recipe, no RTDEControlInterface, no motion command.')

    def _run_command(self, command, timeout_sec):
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
            return {
                'command': command,
                'returncode': completed.returncode,
                'stdout': completed.stdout.strip(),
                'stderr': completed.stderr.strip(),
                'timed_out': False,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                'command': command,
                'returncode': None,
                'stdout': (exc.stdout or '').strip() if isinstance(exc.stdout, str) else '',
                'stderr': (exc.stderr or '').strip() if isinstance(exc.stderr, str) else '',
                'timed_out': True,
            }
        except OSError as exc:
            return {
                'command': command,
                'returncode': None,
                'stdout': '',
                'stderr': str(exc),
                'timed_out': False,
            }

    def _check_ping(self, robot_ip):
        command = ['ping', '-c', '1', '-W', '2', robot_ip]
        result = self._run_command(command, timeout_sec=4.0)
        if result['timed_out']:
            status = FAIL
            message = 'ping command timed out.'
        elif result['returncode'] == 0:
            status = PASS
            message = 'Robot replied to ICMP ping.'
        else:
            status = FAIL
            message = 'Robot did not reply to ICMP ping.'
        return {**result, 'status': status, 'message': message}

    def _check_tcp(self, host, port):
        timeout_sec = 2.0
        start = datetime.datetime.now(datetime.timezone.utc)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)
        try:
            connect_result = sock.connect_ex((host, port))
            elapsed_ms = (datetime.datetime.now(datetime.timezone.utc) - start).total_seconds() * 1000.0
            if connect_result == 0:
                return {
                    'status': PASS,
                    'host': host,
                    'port': port,
                    'timeout_sec': timeout_sec,
                    'elapsed_ms': round(elapsed_ms, 2),
                    'message': 'TCP port accepted a connection.',
                }
            return {
                'status': FAIL,
                'host': host,
                'port': port,
                'timeout_sec': timeout_sec,
                'elapsed_ms': round(elapsed_ms, 2),
                'errno': connect_result,
                'message': 'TCP port did not accept a connection.',
            }
        except socket.timeout:
            return {
                'status': FAIL,
                'host': host,
                'port': port,
                'timeout_sec': timeout_sec,
                'message': 'TCP connection attempt timed out.',
            }
        except OSError as exc:
            return {
                'status': FAIL,
                'host': host,
                'port': port,
                'timeout_sec': timeout_sec,
                'message': str(exc),
            }
        finally:
            sock.close()

    def _check_listening_port(self, port):
        result = self._run_command(['ss', '-lntp'], timeout_sec=3.0)
        stdout = result.get('stdout', '')
        matches = [line for line in stdout.splitlines() if self._line_has_port(line, port)]
        if result['timed_out']:
            status = FAIL
            message = 'ss -lntp timed out.'
        elif result['returncode'] not in (0, None):
            status = WARN
            message = 'ss -lntp returned a non-zero status.'
        elif matches:
            status = PASS
            message = 'Local system is listening on External Control port %d.' % port
        else:
            status = WARN
            message = 'Local system is not listening on External Control port %d.' % port
        return {**result, 'status': status, 'message': message, 'matches': matches}

    def _check_robot_connections(self, robot_ip):
        result = self._run_command(['ss', '-tnp'], timeout_sec=3.0)
        stdout = result.get('stdout', '')
        robot_matches = [line for line in stdout.splitlines() if robot_ip in line]
        rtde_matches = [line for line in stdout.splitlines() if ':30004' in line]
        if result['timed_out']:
            status = FAIL
            message = 'ss -tnp timed out.'
        elif result['returncode'] not in (0, None):
            status = WARN
            message = 'ss -tnp returned a non-zero status.'
        elif robot_matches or rtde_matches:
            status = WARN
            message = 'Current TCP connections to the robot or RTDE port were found.'
        else:
            status = PASS
            message = 'No current TCP connection to robot IP or :30004 was found on this host.'
        return {
            **result,
            'status': status,
            'message': message,
            'robot_ip_matches': robot_matches,
            'rtde_30004_matches': rtde_matches,
        }

    def _check_wsl(self):
        proc_version = ''
        try:
            proc_version = Path('/proc/version').read_text(encoding='utf-8', errors='replace').strip()
        except OSError as exc:
            return {
                'status': WARN,
                'is_wsl': False,
                'platform': platform.platform(),
                'proc_version': '',
                'message': 'Could not read /proc/version: %s' % exc,
            }

        is_wsl = 'microsoft' in proc_version.lower() or 'wsl' in proc_version.lower()
        if is_wsl:
            return {
                'status': WARN,
                'is_wsl': True,
                'platform': platform.platform(),
                'proc_version': proc_version,
                'message': 'WSL detected; WSL2 NAT may prevent the robot from connecting to a listener inside WSL.',
            }
        return {
            'status': PASS,
            'is_wsl': False,
            'platform': platform.platform(),
            'proc_version': proc_version,
            'message': 'WSL signature was not detected in /proc/version.',
        }

    def _line_has_port(self, line, port):
        needle = ':%d' % port
        return needle in line

    def _analyze(self, ping_result, tcp_results, listen_result, connections_result, wsl_result):
        findings = []

        dashboard_ok = tcp_results.get('29999', {}).get('status') == PASS
        rtde_ok = tcp_results.get('30004', {}).get('status') == PASS
        port_50002_listening = listen_result.get('status') == PASS
        local_rtde_connections = bool(connections_result.get('rtde_30004_matches'))

        if not dashboard_ok:
            findings.append({
                'status': FAIL,
                'title': 'Dashboard 29999 unreachable',
                'detail': '29999 is not connectable. First check robot IP, Ethernet cable, same subnet, and firewall.',
            })

        if not port_50002_listening:
            findings.append({
                'status': WARN,
                'title': 'External Control port 50002 is not listening locally',
                'detail': 'The teach pendant refusal to %s:%d is expected when ur_robot_driver/script sender is not listening.' % (
                    self.host_ip, self.external_control_port),
            })

        if dashboard_ok and rtde_ok and self.speed_slider_mask_observed:
            findings.append({
                'status': WARN,
                'title': 'Network path is basically reachable, but RTDE writable resource is occupied',
                'detail': "29999 and 30004 are connectable while speed_slider_mask is reported. Suspect another RTDE client, Fieldbus, URCap, another PC, or a stale robot-controller state.",
            })

        if self.speed_slider_mask_observed and not local_rtde_connections:
            findings.append({
                'status': WARN,
                'title': 'No local :30004 connection was found, but speed_slider_mask is still reported',
                'detail': 'Reboot the UR control cabinet, then check other PCs, URCaps, and Fieldbus/PLC features that may own RTDE input registers.',
            })

        if wsl_result.get('is_wsl'):
            if port_50002_listening:
                detail = '50002 is listening inside WSL, but that does not prove Windows is listening. Configure Windows portproxy/firewall or WSL2 mirrored networking.'
            else:
                detail = 'WSL2 NAT may prevent the robot from connecting to WSL. Also, 50002 is not listening in this Linux environment.'
            findings.append({
                'status': WARN,
                'title': 'WSL2 networking risk',
                'detail': detail,
            })

        if not findings:
            findings.append({
                'status': PASS,
                'title': 'No obvious local network blocker detected',
                'detail': 'Basic link checks passed. If the driver still fails, inspect driver logs, teach pendant External Control settings, and robot-side RTDE resource ownership.',
            })

        overall = PASS
        if any(item['status'] == FAIL for item in findings):
            overall = FAIL
        elif any(item['status'] == WARN for item in findings):
            overall = WARN

        return {'overall_status': overall, 'findings': findings}

    def _write_reports(self, report):
        self.report_json.parent.mkdir(parents=True, exist_ok=True)
        self.report_md.parent.mkdir(parents=True, exist_ok=True)
        self.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        self.report_md.write_text(self._render_markdown(report), encoding='utf-8')

    def _render_markdown(self, report):
        metadata = report['metadata']
        checks = report['checks']
        analysis = report['analysis']
        lines = [
            '# UR10 Link Test Report',
            '',
            '## 1. Metadata',
            '',
            '| Field | Value |',
            '| --- | --- |',
            '| Started at | `%s` |' % metadata['started_at'],
            '| Finished at | `%s` |' % metadata['finished_at'],
            '| Robot IP | `%s` |' % metadata['robot_ip'],
            '| Host IP | `%s` |' % metadata['host_ip'],
            '| External Control Port | `%s` |' % metadata['external_control_port'],
            '| Safety Mode | `%s` |' % metadata['safe_mode'],
            '',
            '## 2. Check Results',
            '',
            '| Check | Status | Message |',
            '| --- | --- | --- |',
            '| Ping | `%s` | %s |' % (checks['ping']['status'], checks['ping']['message']),
            '| Local 50002 listener | `%s` | %s |' % (
                checks['local_external_control_listener']['status'],
                checks['local_external_control_listener']['message'],
            ),
            '| Current robot connections | `%s` | %s |' % (
                checks['current_robot_connections']['status'],
                checks['current_robot_connections']['message'],
            ),
            '| WSL check | `%s` | %s |' % (checks['wsl']['status'], checks['wsl']['message']),
        ]
        for port, result in checks['tcp_ports'].items():
            lines.append('| TCP %s | `%s` | %s |' % (port, result['status'], result['message']))

        lines.extend([
            '',
            '## 3. ss Matches',
            '',
            '### Listening on External Control Port',
            '',
        ])
        lines.extend(self._render_code_lines(checks['local_external_control_listener'].get('matches', [])))
        lines.extend(['', '### Connections Containing Robot IP', ''])
        lines.extend(self._render_code_lines(checks['current_robot_connections'].get('robot_ip_matches', [])))
        lines.extend(['', '### Connections Containing :30004', ''])
        lines.extend(self._render_code_lines(checks['current_robot_connections'].get('rtde_30004_matches', [])))

        lines.extend(['', '## 4. Analysis', '', '**Overall:** `%s`' % analysis['overall_status'], ''])
        for item in analysis['findings']:
            lines.append('- `%s` **%s**: %s' % (item['status'], item['title'], item['detail']))

        lines.extend([
            '',
            '## 5. Safety Note',
            '',
            'This tool only performs ICMP ping, TCP connect probes, and local socket table inspection. It does not use RTDEControlInterface, does not write an RTDE input recipe, and does not send motion commands.',
            '',
        ])
        return '\n'.join(lines)

    def _render_code_lines(self, values):
        if not values:
            return ['No matches.']
        lines = ['```text']
        lines.extend(values)
        lines.append('```')
        return lines

    def _log_summary(self, report):
        checks = report['checks']
        self._log_status('Ping %s' % self.robot_ip, checks['ping'])
        for port in self.robot_ports:
            self._log_status('TCP %s:%d' % (self.robot_ip, port), checks['tcp_ports'][str(port)])
        self._log_status('Local listener :%d' % self.external_control_port, checks['local_external_control_listener'])
        self._log_status('Current robot connections', checks['current_robot_connections'])
        self._log_status('WSL check', checks['wsl'])
        for finding in report['analysis']['findings']:
            self.get_logger().info('[%s] %s: %s' % (finding['status'], finding['title'], finding['detail']))
        self.get_logger().info('JSON report: %s' % self.report_json)
        self.get_logger().info('Markdown report: %s' % self.report_md)

    def _log_status(self, label, result):
        status = result.get('status', WARN)
        message = result.get('message', '')
        self.get_logger().info('[%s] %s - %s' % (status, label, message))


def main(args=None):
    rclpy.init(args=args)
    node = UR10LinkTestNode()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
