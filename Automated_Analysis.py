import os
import re
import csv
import time
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mininet.net import Mininet
from mininet.node import RemoteController
from Topology import Mytopo

PAIRS_TO_TEST = [
    ('h1', 'h5'), ('h1', 'h6'),
    ('h2', 'h5'), ('h2', 'h6'),
    ('h3', 'h7'), ('h3', 'h8'),
    ('h4', 'h7'), ('h4', 'h8')
]

def clean_environment():
    subprocess.call(['sudo', 'mn', '-c'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Kill any lingering floodlight java processes just in case
    subprocess.call(['sudo', 'pkill', '-f', 'floodlight.jar'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

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
        print("ERROR: Script must run as root. (sudo python3 Automated_Analysis.py)")
        return

    all_results = []
    clean_environment()

    # ==========================================
    # TEST 1: Direct Rules (Part A)
    # ==========================================
    print("[*] Booting Mininet for direct scripting...")
    topo = Mytopo()
    net1 = Mininet(topo=topo, controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6653))
    net1.start()
    
    print("[*] Pushing Direct Rules via AddRules.sh...")
    subprocess.call(['sudo', './AddRules.sh'], stdout=subprocess.DEVNULL)
    time.sleep(2)
    
    all_results.extend(run_network_tests(net1, 'Part A (Direct Scripts)'))
    
    print("[*] Tearing down Direct Rules network...")
    net1.stop()
    clean_environment()

    # ==========================================
    # TEST 2: Floodlight (Part C)
    # ==========================================
    print("\n[*] Booting Floodlight Java Controller in background...")
    floodlight_proc = subprocess.Popen(['java', '-jar', 'target/floodlight.jar'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(8) # Wait for Java server to fully bind
    
    print("[*] Booting Mininet for Floodlight connection...")
    net2 = Mininet(topo=topo, controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6653))
    net2.start()
    time.sleep(5) # Wait for switch handshakes
    
    print("[*] Pushing Rules via REST API (AddRulesFloodlight.py)...")
    subprocess.call(['python3', 'AddRulesFloodlight.py'], stdout=subprocess.DEVNULL)
    time.sleep(3) # Wait for REST static flows to manifest
    
    all_results.extend(run_network_tests(net2, 'Part C (Floodlight API)'))
    
    print("[*] Tearing down Floodlight network...")
    net2.stop()
    floodlight_proc.terminate()
    clean_environment()

    # ==========================================
    # REPORT GENERATION
    # ==========================================
    print("\n[*] Data collection complete! Compiling comprehensive comparative reports...")
    
    os.makedirs('SUBMISSION_READY/Performance_Data', exist_ok=True)
    os.makedirs('SUBMISSION_READY/Analysis_Results', exist_ok=True)
    
    # 1. Output CSV
    csv_file = 'SUBMISSION_READY/Performance_Data/Aggregated_Results.csv'
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
        writer.writeheader()
        writer.writerows(all_results)
    
    # 2. Comparative Matplotlib Graphs
    df = pd.DataFrame(all_results)
    
    # Group by Pair and Method
    pivot_bw = df.pivot(index='Pair', columns='Method', values='Bandwidth_Gbps')
    pivot_lat = df.pivot(index='Pair', columns='Method', values='Latency_ms')

    # Bandwidth Plot
    ax = pivot_bw.plot(kind='bar', figsize=(12, 6), color=['#1f77b4', '#ff7f0e'])
    plt.title('TCP Throughput Comparison: Direct Scripting vs Floodlight API')
    plt.ylabel('Bandwidth (Gbits/sec)')
    plt.xticks(rotation=0)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('SUBMISSION_READY/Analysis_Results/Bandwidth_Comparison.png')

    # Latency Plot
    ax2 = pivot_lat.plot(kind='bar', figsize=(12, 6), color=['#2ca02c', '#d62728'])
    plt.title('ICMP RTT Latency Comparison: Direct Scripting vs Floodlight API')
    plt.ylabel('Latency (ms)')
    plt.xticks(rotation=0)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('SUBMISSION_READY/Analysis_Results/Latency_Comparison.png')
    
    print("[SUCCESS] Everything successfully compiled!")

if __name__ == '__main__':
    main()
