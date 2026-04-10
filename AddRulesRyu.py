from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3

class SDNAssignmentRyu(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SDNAssignmentRyu, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # 1. Default drop for IP (priority 10)
        match_ip = parser.OFPMatch(eth_type=0x0800)
        self.add_flow(datapath, 10, match_ip, [])

        # 2. Allow ARP (priority 50), flood
        match_arp = parser.OFPMatch(eth_type=0x0806)
        actions_arp = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.add_flow(datapath, 50, match_arp, actions_arp)

        # Helper to add bidirectional routing flows
        def route(ip1, p1, ip2, p2):
            match1 = parser.OFPMatch(eth_type=0x0800, ipv4_src=ip1, ipv4_dst=ip2)
            act1 = [parser.OFPActionOutput(p2)]
            self.add_flow(datapath, 100, match1, act1)
            
            match2 = parser.OFPMatch(eth_type=0x0800, ipv4_src=ip2, ipv4_dst=ip1)
            act2 = [parser.OFPActionOutput(p1)]
            self.add_flow(datapath, 100, match2, act2)

        if dpid == 1:
            for s in ['10.0.0.1', '10.0.0.2']:
                for d in ['10.0.0.5', '10.0.0.6']:
                    route(s, 1, d, 2)
            for s in ['10.0.0.3', '10.0.0.4']:
                for d in ['10.0.0.7', '10.0.0.8']:
                    route(s, 1, d, 2)
        elif dpid == 2:
            for s in ['10.0.0.1', '10.0.0.2']:
                for d in ['10.0.0.5', '10.0.0.6']:
                    route(s, 2, d, 1)
            for s in ['10.0.0.3', '10.0.0.4']:
                for d in ['10.0.0.7', '10.0.0.8']:
                    route(s, 3, d, 1)
        elif dpid == 3:
            for s in ['10.0.0.1', '10.0.0.2']:
                for d in ['10.0.0.5', '10.0.0.6']:
                    route(s, 1, d, 2)
            for s in ['10.0.0.3', '10.0.0.4']:
                for d in ['10.0.0.7', '10.0.0.8']:
                    route(s, 1, d, 3)
        elif dpid == 4:
            for s, s_port in [('10.0.0.1', 2), ('10.0.0.2', 3)]:
                for d in ['10.0.0.5', '10.0.0.6']:
                    route(s, s_port, d, 1)
            route('10.0.0.1', 2, '10.0.0.2', 3)
        elif dpid == 5:
            for s, s_port in [('10.0.0.3', 2), ('10.0.0.4', 3)]:
                for d in ['10.0.0.7', '10.0.0.8']:
                    route(s, s_port, d, 1)
            route('10.0.0.3', 2, '10.0.0.4', 3)
        elif dpid == 6:
            for s, s_port in [('10.0.0.5', 2), ('10.0.0.6', 3)]:
                for d in ['10.0.0.1', '10.0.0.2']:
                    route(s, s_port, d, 1)
            route('10.0.0.5', 2, '10.0.0.6', 3)
        elif dpid == 7:
            for s, s_port in [('10.0.0.7', 2), ('10.0.0.8', 3)]:
                for d in ['10.0.0.3', '10.0.0.4']:
                    route(s, s_port, d, 1)
            route('10.0.0.7', 2, '10.0.0.8', 3)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)
