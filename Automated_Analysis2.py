import os
import re
import csv
import time
import subprocess
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from Topology import Mytopo

PAIRS_TO_TEST = [
    ('h1', 'h5'), ('h1', 'h6'),
    ('h2', 'h5'), ('h2', 'h6'),
    ('h3', 'h7'), ('h3', 'h8'),
    ('h4', 'h7'), ('h4', 'h8')
]

def clean_environment():
    subprocess.call(['sudo', 'mn', '-c'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.call(['sudo', 'pkill', '-f', 'floodlight.jar'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.call(['sudo', 'pkill', '-f', 'ryu-manager'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

def run_network_tests(net, method_name):
    print(f"\n[===== Testing Phase: {method_name} =====]")
    results = []
    for src_name, dst_name in PAIRS_TO_TEST:
        src = net.get(src_name)
        dst = net.get(dst_name)
        dst_ip = dst.IP()

        print(f"[*] Extracting metrics: {src_name} -> {dst_name} ({dst_ip})")

        # Latency
        ping_out = src.cmd(f'ping -c 3 {dst_ip}')
        latency = 0.0
        rtt_match = re.search(r'rtt min/avg/max/mdev = [\d\.]+/(.*?)/[\d\.]+/', ping_out)
        if rtt_match:
            latency = float(rtt_match.group(1))

        # Bandwidth
        dst.cmd('iperf -s &')
        time.sleep(1)
        iperf_out = src.cmd(f'iperf -c {dst_ip} -t 5')
        bandwidth = 0.0
        bw_match = re.search(r'(\d+(\.\d+)?) (Gbits/sec|Mbits/sec)', iperf_out)
        if bw_match:
            val = float(bw_match.group(1))
            unit = bw_match.group(3)
            bandwidth = val if unit == 'Gbits/sec' else val / 1000.0

        dst.cmd('kill %iperf')

        results.append({
            'Method': method_name,
            'Source': src_name,
            'Destination': dst_name,
            'Pair': f"{src_name}->{dst_name}",
            'Latency_ms': latency,
            'Bandwidth_Gbps': bandwidth
        })
    return results


def main():
    if os.geteuid() != 0:
        print("ERROR: Script must run as root. (sudo python3 Automated_Analysis1.py)")
        return

    all_results = []
    clean_environment()

    # ──────────────────────────────────────────────────────────────────────
    # TEST 1 — Part A: Direct OpenFlow Rules (ovs-ofctl shell script)
    # ──────────────────────────────────────────────────────────────────────
    print("[*] Booting Mininet for Part A (Direct Rules)...")
    topo = Mytopo()
    net1 = Mininet(
        topo=topo,
        controller=None,
        switch=lambda name, **kw: OVSSwitch(name, protocols='OpenFlow10', **kw)
    )
    net1.start()
    print("[*] Pushing Direct Rules via AddRules.sh...")
    subprocess.call(['sudo', './AddRules.sh'], stdout=subprocess.DEVNULL)
    time.sleep(2)

    all_results.extend(run_network_tests(net1, 'Part A (Direct Scripts)'))
    print("[*] Tearing down Part A network...")
    net1.stop()
    clean_environment()

    # ──────────────────────────────────────────────────────────────────────
    # TEST 2 — Part B: Floodlight REST API Controller
    # ──────────────────────────────────────────────────────────────────────
    print("\n[*] Booting Floodlight controller...")
    floodlight_proc = subprocess.Popen(
        ['java', '-jar', 'target/floodlight.jar'],
        cwd='/root/floodlight',
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(20)

    print("[*] Booting Mininet for Part B (Floodlight)...")
    net2 = Mininet(
        topo=topo,
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6653),
        switch=lambda name, **kw: OVSSwitch(name, protocols='OpenFlow10', **kw)
    )
    net2.start()
    time.sleep(5)

    print("[*] Pushing Rules via Floodlight REST API...")
    subprocess.call(['python3', 'AddRulesFloodlight.py'], stdout=subprocess.DEVNULL)
    time.sleep(3)

    all_results.extend(run_network_tests(net2, 'Part B (Floodlight API)'))
    print("[*] Tearing down Part B network...")
    net2.stop()
    floodlight_proc.terminate()
    clean_environment()

    # ──────────────────────────────────────────────────────────────────────
    # TEST 3 — Part C: Ryu Proactive Controller
    # ──────────────────────────────────────────────────────────────────────
    print("\n[*] Booting Ryu proactive controller...")
    ryu_proc = subprocess.Popen(
        ['ryu-manager', 'RyuController.py'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(5)   # Ryu boots much faster than Java Floodlight

    print("[*] Booting Mininet for Part C (Ryu)...")
    net3 = Mininet(
        topo=topo,
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633),
        switch=lambda name, **kw: OVSSwitch(name, protocols='OpenFlow13', **kw)
    )
    net3.start()
    time.sleep(5)   # Allow all 7 switches to handshake and receive rules

    # No separate rule-push script needed — Ryu installs rules on switch connect!
    print("[*] Ryu rules auto-installed on switch connect (proactive mode).")

    all_results.extend(run_network_tests(net3, 'Part C (Ryu Controller)'))
    print("[*] Tearing down Part C network...")
    net3.stop()
    ryu_proc.terminate()
    clean_environment()

    # ──────────────────────────────────────────────────────────────────────
    # REPORT GENERATION
    # ──────────────────────────────────────────────────────────────────────
    print("\n[*] Compiling three-way comparative reports...")

    os.makedirs('SUBMISSION_READY/Performance_Data', exist_ok=True)
    os.makedirs('SUBMISSION_READY/Analysis_Results', exist_ok=True)

    csv_file = 'SUBMISSION_READY/Performance_Data/Aggregated_Results.csv'
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
        writer.writeheader()
        writer.writerows(all_results)
    print(f"[*] CSV written to {csv_file}")

    df = pd.DataFrame(all_results)
    pivot_bw  = df.pivot(index='Pair', columns='Method', values='Bandwidth_Gbps')
    pivot_lat = df.pivot(index='Pair', columns='Method', values='Latency_ms')

    COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c']   # blue, orange, green

    # Bandwidth Plot
    ax = pivot_bw.plot(kind='bar', figsize=(14, 6), color=COLORS)
    plt.title('TCP Throughput Comparison: Part A vs Part B (Floodlight) vs Part C (Ryu)',
              fontsize=13, fontweight='bold')
    plt.ylabel('Bandwidth (Gbits/sec)')
    plt.xlabel('Host Pair')
    plt.xticks(rotation=15, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(loc='lower right')
    plt.tight_layout()
    plt.savefig('SUBMISSION_READY/Analysis_Results/Bandwidth_Comparison.png', dpi=150)
    print("[*] Bandwidth graph saved.")

    # Latency Plot
    ax2 = pivot_lat.plot(kind='bar', figsize=(14, 6), color=COLORS)
    plt.title('ICMP RTT Latency Comparison: Part A vs Part B (Floodlight) vs Part C (Ryu)',
              fontsize=13, fontweight='bold')
    plt.ylabel('Average RTT Latency (ms)')
    plt.xlabel('Host Pair')
    plt.xticks(rotation=15, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(loc='upper right')
    plt.tight_layout()
    plt.savefig('SUBMISSION_READY/Analysis_Results/Latency_Comparison.png', dpi=150)
    print("[*] Latency graph saved.")

    print("\n[SUCCESS] Three-way analysis complete!")


if __name__ == '__main__':
    main()

