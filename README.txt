SDN Assignment 2
Group ID: [PUT YOUR GROUP ID HERE]
Leader Reg No: [PUT LEADER REG NO HERE]
Member 1 Reg No: [PUT REG NO HERE]
Member 2 Reg No: [PUT REG NO HERE]

=========================
EXECUTION INSTRUCTIONS
=========================

Important Note: Mininet requires a Linux environment to run. 

### Starting the Topology
1. Open a terminal in your Ubuntu VM.
2. Run Mininet with the custom topology:
   sudo mn --custom Topology.py --topo mytopo --mac --controller=remote,ip=127.0.0.1,port=6653
3. The Mininet CLI (mininet>) will open.

### Part A: Direct OpenFlow Rules
1. In a separate terminal, navigate to this folder.
2. Make the bash script executable:
   chmod +x AddRules.sh
3. Run the script:
   ./AddRules.sh
4. Go back to Mininet CLI and test connecting:
   mininet> pingall
5. Use `dpctl dump-flows` to take your flow screenshots.

### Part B: Floodlight Controller
1. Start your Floodlight Instance.
2. Start the Mininet topology pointing to the Floodlight port (usually 6653).
3. In a separate terminal, run the python script to push statically:
   python3 PartC_Controller/AddRulesFloodlight.py
4. Validate in Mininet.

### Part C: Performance Testing
Use the mininet `ping` and `iperf` commands manually across the 3 setups, take screenshots, and save performance data into the respective empty folders provided here.
