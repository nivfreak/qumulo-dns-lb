#!/usr/bin/python
"""A DNS load balancer for Qumulo Clusters"""
import argparse
import copy
import sys
import time

from dnslib import RR
from dnslib.server import DNSServer, BaseResolver, DNSLogger

import qumulo.lib.auth as qauth
import qumulo.lib.request as qrequest
import qumulo.rest.auth as qrestauth
import qumulo.rest.network as qnetwork

FRONTEND_INTERFACE = 1

class ConnectionCountResolver(BaseResolver):
    """
    Respond with the floating IPs for the lowest connection count node.
    """

    def __init__(self, args):
        self.args = args

    def resolve(self, request, handler):
        reply = request.reply()
        qname = request.q.qname
        if qname not in self.args.dnsname:
            print "Skipping: %s is not a configured DNS name." % (qname)
            return reply
        # Replace labels with request label
        for ip in self.get_qfs_ips():
            rr = RR.fromZone('. 0 IN A {}'.format(ip))[0]
            a = copy.copy(rr)
            a.rname = qname
            reply.add_answer(a)
        return reply

    def get_qfs_ips(self):
        qapi = QumuloConnections(self.args)
        return qapi.get_ips()


class QumuloConnections(object):
    def __init__(self, args=None):

        self.port = args.port
        self.user = args.user
        self.passwd = args.passwd
        self.host = args.host
        self.vlan_id = args.vlan_id
        self.verbose = args.verbose

        self.connection = qrequest.Connection(self.host, int(self.port))
        self.credentials = qauth.credential_store_filename()
        self.login()

    def login(self):
        try:
            login_results, _ = qrestauth.login(\
                self.connection, None, self.user, self.passwd)

            self.credentials = qauth.Credentials.\
                from_login_response(login_results)
        except Exception, excpt:
            print "Error connecting to the REST server: %s" % excpt
            print __doc__
            sys.exit(1)

    def connection_count(self):
        """Returns a dictionary of nodes and protocol client connection counts"""
        connlist = qnetwork.connections(self.connection, self.credentials)
        per_node = {}
        for node_data in connlist.data:
            per_node[node_data['id']] = 0
            for _ in node_data['connections']:
                per_node[node_data['id']] += 1
        return per_node

    def floating_ips(self, nodeid):
        """Return the floating IPs for a node by id"""
        fips = qnetwork.get_network_status_v2(self.connection, self.credentials,
                                              FRONTEND_INTERFACE, nodeid)
        network_statuses = fips.data["network_statuses"]
        matched_network = [network_id for network_id, network in
                           enumerate(network_statuses) if network["vlan_id"]
                           == self.vlan_id][0]
        vlan_status = network_statuses[matched_network]
        return vlan_status['floating_addresses']

    def low_nodeid(self):
        """Find the node with the fewest connections"""
        conn_count = self.connection_count()
        return min(conn_count, key=conn_count.get)

    def get_ips(self):
        """Get the floating IPs of the node with the fewest connections"""
        low_nodeid = self.low_nodeid()
        return self.floating_ips(low_nodeid)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", "--host", dest="host", required=True,
                        help="Required: Specify host (cluster) for file lists")
    parser.add_argument("-P", "--port", type=int, dest="port", default=8000,
                        required=False,
                        help="specify port on cluster; defaults to 8000")
    parser.add_argument("-u", "--user", default="admin", dest="user",
                        required=False,
                        help="specify user credentials for login; defaults to admin")
    parser.add_argument("-p", "--pass", default="admin", dest="passwd",
                        required=False,
                        help="specify user pwd for login, defaults to admin")
    parser.add_argument("-v", "--verbose", default=False, required=False,
                        dest="verbose",
                        help="Echo values to console; defaults to False ",
                        action="store_true")
    parser.add_argument("--log", default="request,reply,truncated,error",
                        help="Log hooks to enable (default: +request,+reply,+truncated,+error,-recv,-send,-data)")
    parser.add_argument("--log-prefix", action='store_true', default=False,
                        help="Log prefix (timestamp/handler/resolver) (default: False)")
    parser.add_argument("--dnsname", required=True, dest="dnsname", nargs='+',
                        help="The hostname you wish to respond to.")
    parser.add_argument("--vlan-id", type=int, default=0, dest="vlan_id",
                        help="VLAN ID of desired cluster network, defaults to 0 (untagged)")
    parser.add_argument("--dnsport", type=int, default=53, dest="dnsport",
                        help="Server port (default:53)")
    parser.add_argument("--address", "-a", default="", dest="address",
                        help="Listen address (default:all)")

    args = parser.parse_args()

    resolver = ConnectionCountResolver(args)
    logger = DNSLogger(args.log, args.log_prefix)

    udp_server = DNSServer(resolver,
                           port=args.dnsport,
                           address=args.address,
                           logger=logger)

    udp_server.start_thread()

    while udp_server.isAlive():
        time.sleep(1)


# Main
if __name__ == '__main__':
    main()
