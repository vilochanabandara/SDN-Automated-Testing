#!/bin/bash

# Clear existing flows from all switches
for i in {1..7}; do
    ovs-ofctl del-flows s$i
    # Allow ARP on all switches so nodes can discover MACs (safely flood in Tree topology)
    ovs-ofctl add-flow s$i priority=50,arp,actions=flood
done

# Function to add bidirectional flow
function route_bidir {
    sw=$1; ip1=$2; p1=$3; ip2=$4; p2=$5
    ovs-ofctl add-flow $sw priority=100,ip,nw_src=$ip1,nw_dst=$ip2,actions=output:$p2
    ovs-ofctl add-flow $sw priority=100,ip,nw_src=$ip2,nw_dst=$ip1,actions=output:$p1
}

# --- GROUP: H1, H2 communicating with H5, H6 ---
for SRC in 10.0.0.1 10.0.0.2; do
    for DST in 10.0.0.5 10.0.0.6; do
        SRC_PORT=$(( ${SRC##*.} + 1 )) # 10.0.0.1 -> port 2, 10.0.0.2 -> port 3
        route_bidir s4 $SRC $SRC_PORT $DST 1
        route_bidir s2 $SRC 2 $DST 1
        route_bidir s1 $SRC 1 $DST 2
        route_bidir s3 $SRC 1 $DST 2
        
        DST_PORT=$(( ${DST##*.} - 3 )) # h5(5)->2, h6(6)->3
        route_bidir s6 $SRC 1 $DST $DST_PORT
    done
done

# --- GROUP: H3, H4 communicating with H7, H8 ---
for SRC in 10.0.0.3 10.0.0.4; do
    for DST in 10.0.0.7 10.0.0.8; do
        SRC_PORT=$(( ${SRC##*.} - 1 )) # h3(3)->2, h4(4)->3
        route_bidir s5 $SRC $SRC_PORT $DST 1
        route_bidir s2 $SRC 3 $DST 1
        route_bidir s1 $SRC 1 $DST 2
        route_bidir s3 $SRC 1 $DST 3
        
        DST_PORT=$(( ${DST##*.} - 5 )) # h7(7)->2, h8(8)->3
        route_bidir s7 $SRC 1 $DST $DST_PORT
    done
done

# --- Same Access Switch Communication ---
route_bidir s4 10.0.0.1 2 10.0.0.2 3
route_bidir s5 10.0.0.3 2 10.0.0.4 3
route_bidir s6 10.0.0.5 2 10.0.0.6 3
route_bidir s7 10.0.0.7 2 10.0.0.8 3

# --- Deny all other IP traffic (Default Drop) ---
for i in {1..7}; do
    ovs-ofctl add-flow s$i priority=10,ip,actions=drop
done

echo "Proactive Flow Rules Installed Successfully."
