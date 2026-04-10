import requests
import json
import time

FLOODLIGHT_URL = "http://127.0.0.1:8080/wm/staticentrypusher/json"
FLOW_ID = 1

def push_flow(switch_dpid, priority, eth_type, match_fields, actions):
    global FLOW_ID
    flow = {
        "switch": switch_dpid,
        "name": f"flow-reg-{FLOW_ID}",
        "cookie": "0",
        "priority": str(priority),
        "eth_type": eth_type,
        "active": "true",
        "instruction_apply_actions": actions # OpenFlow 1.3 usually, or just "actions" for OpenFlow 1.0
    }
    
    # Adding OpenFlow 1.3 action compatibility just in case
    # Often "actions" also works in Floodlight Static Entry Pusher for basic output ports
    flow["actions"] = actions
    
    flow.update(match_fields)
    try:
        requests.post(FLOODLIGHT_URL, data=json.dumps(flow), headers={'Content-Type': 'application/json'})
    except Exception as e:
        print(f"Failed to post to floodlight: {e}")
    FLOW_ID += 1

def push_route(switch_dpid, ip1, p1, ip2, p2):
    # forward
    push_flow(switch_dpid, 100, "0x0800", {"ipv4_src": ip1, "ipv4_dst": ip2}, f"output={p2}")
    # reverse
    push_flow(switch_dpid, 100, "0x0800", {"ipv4_src": ip2, "ipv4_dst": ip1}, f"output={p1}")

def dpid(n):
    return f"00:00:00:00:00:00:00:0{n}"

print("Pushing proactive flow rules to Floodlight REST API...")

# Default rules for all switches
for num in range(1, 8):
    sw = dpid(num)
    # Default DROP (IP)
    push_flow(sw, 10, "0x0800", {}, "")
    # Allow ARP (Flood)
    push_flow(sw, 50, "0x0806", {}, "output=flood")

# Specific routing rules
# SW1
for s in ['10.0.0.1', '10.0.0.2']:
    for d in ['10.0.0.5', '10.0.0.6']:
        push_route(dpid(1), s, 1, d, 2)
for s in ['10.0.0.3', '10.0.0.4']:
    for d in ['10.0.0.7', '10.0.0.8']:
        push_route(dpid(1), s, 1, d, 2)

# SW2
for s in ['10.0.0.1', '10.0.0.2']:
    for d in ['10.0.0.5', '10.0.0.6']:
        push_route(dpid(2), s, 2, d, 1)
for s in ['10.0.0.3', '10.0.0.4']:
    for d in ['10.0.0.7', '10.0.0.8']:
        push_route(dpid(2), s, 3, d, 1)

# SW3
for s in ['10.0.0.1', '10.0.0.2']:
    for d in ['10.0.0.5', '10.0.0.6']:
        push_route(dpid(3), s, 1, d, 2)
for s in ['10.0.0.3', '10.0.0.4']:
    for d in ['10.0.0.7', '10.0.0.8']:
        push_route(dpid(3), s, 1, d, 3)

# SW4
for s, s_port in [('10.0.0.1', 2), ('10.0.0.2', 3)]:
    for d in ['10.0.0.5', '10.0.0.6']:
        push_route(dpid(4), s, s_port, d, 1)
push_route(dpid(4), '10.0.0.1', 2, '10.0.0.2', 3)

# SW5
for s, s_port in [('10.0.0.3', 2), ('10.0.0.4', 3)]:
    for d in ['10.0.0.7', '10.0.0.8']:
        push_route(dpid(5), s, s_port, d, 1)
push_route(dpid(5), '10.0.0.3', 2, '10.0.0.4', 3)

# SW6
for s, s_port in [('10.0.0.5', 2), ('10.0.0.6', 3)]:
    for d in ['10.0.0.1', '10.0.0.2']:
        push_route(dpid(6), s, s_port, d, 1)
push_route(dpid(6), '10.0.0.5', 2, '10.0.0.6', 3)

# SW7
for s, s_port in [('10.0.0.7', 2), ('10.0.0.8', 3)]:
    for d in ['10.0.0.3', '10.0.0.4']:
        push_route(dpid(7), s, s_port, d, 1)
push_route(dpid(7), '10.0.0.7', 2, '10.0.0.8', 3)

print("Finished submitting Flow rules.")
