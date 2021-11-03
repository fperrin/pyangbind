#!/usr/bin/env python

import os.path
import unittest

import json
import lxml

from pyangbind.lib.serialise import pybindIETFJSONEncoder, pybindJSONDecoder, pybindJSONEncoder, pybindJSONIOError
from pyangbind.lib.xpathhelper import YANGPathHelper
from tests.base import PyangBindTestCase


class IetfRoutingTests(PyangBindTestCase):
    yang_files = [
        "yang/ietf-routing@2018-03-13.yang",
        "yang/ietf-ipv4-unicast-routing@2018-03-13.yang",
        "yang/ietf-ipv6-unicast-routing@2018-03-13.yang",
    ]
    split_class_dir = True

    def test_serialise_configuration(self):
        """Generate the example configuration given in Appendix D of RFC8349

        That configuration truncated to only contain the ietf-routing module
        (skipping the interface configuration).
        """
        instance = self.bindings.ietf_routing()
        routing = instance.routing
        routing.router_id = "192.0.2.1"
        cp = routing.control_plane_protocols.control_plane_protocol.add("ietf-routing:static st0")
        cp.description = "Static routing is used for the internal network."

        st_v4 = cp.static_routes.ipv4.route
        rt_v4 = st_v4.add("0.0.0.0/0")
        rt_v4.next_hop.next_hop_address = "192.0.2.2"

        st_v6 = cp.static_routes.ipv6.route
        rt_v6 = st_v6.add("::/0")
        rt_v6.next_hop.next_hop_address = "2001:db8:0:1::2"

        pybind_json = json.loads(
            json.dumps(pybindIETFJSONEncoder.generate_element(instance, flt=True), cls=pybindIETFJSONEncoder, indent=4)
        )

        with open(os.path.join(os.path.dirname(__file__), "testdata", "configuration.json"), "r") as fp:
            external_json = json.load(fp)

        self.assertEqual(external_json, pybind_json, "JSON did not match the expected output.")

    def test_deserialise_operational_state(self):
        """Loads the example operational state given in Appendix D of RFC8349."""
        with open(os.path.join(os.path.dirname(__file__), "testdata", "operational.json"), "r") as fp:
            external_json = json.load(fp)

        obj = pybindJSONDecoder.load_ietf_json(external_json, self.bindings, "ietf-routing")

        self.assertEqual(obj.routing.router_id, "192.0.2.1")
        self.assertEqual(len(obj.routing.control_plane_protocols.control_plane_protocol), 1)
        self.assertIn("ietf-routing:static st0", obj.routing.control_plane_protocols.control_plane_protocol)
        st0 = obj.routing.control_plane_protocols.control_plane_protocol["ietf-routing:static st0"]

        self.assertEqual(len(st0.static_routes.ipv4.route), 1)
        v4_rt = st0.static_routes.ipv4.route["0.0.0.0/0"]
        self.assertEqual(v4_rt.next_hop.next_hop_address, "192.0.2.2")

        self.assertEqual(len(st0.static_routes.ipv6.route), 1)
        v6_rt = st0.static_routes.ipv6.route["::/0"]
        self.assertEqual(v6_rt.next_hop.next_hop_address, "2001:db8:0:1::2")

        rib_list = obj.routing.ribs.rib
        self.assertEqual(len(rib_list), 2)

        v4_rib = rib_list["ipv4-master"]
        self.assertIn(v4_rib.address_family, ("ietf-ipv4-unicast-routing:ipv4-unicast", "ipv4-unicast"))
        self.assertTrue(v4_rib.default_rib, True)
        self.assertEqual(len(v4_rib.routes.route), 3)

        for v4_rib_rt in v4_rib.routes.route.values():
            if v4_rib_rt.destination_prefix == "192.0.2.1/24":
                self.assertEqual(v4_rib_rt.next_hop.outgoing_interface, "eth0")
                self.assertFalse(v4_rib_rt.next_hop.next_hop_address._changed())
                self.assertEqual(v4_rib_rt.next_hop.next_hop_address, "")
                self.assertEqual(v4_rib_rt.route_preference, 0)
                self.assertIn(v4_rib_rt.source_protocol, ("ietf-routing:direct", "direct"))
                self.assertEqual(v4_rib_rt.last_updated, "2015-10-24T17:11:27+02:00")

            elif v4_rib_rt.destination_prefix == "198.51.100.0/24":
                self.assertEqual(v4_rib_rt.next_hop.outgoing_interface, "eth1")
                self.assertFalse(v4_rib_rt.next_hop.next_hop_address._changed())
                self.assertEqual(v4_rib_rt.next_hop.next_hop_address, "")
                self.assertEqual(v4_rib_rt.route_preference, 0)
                self.assertIn(v4_rib_rt.source_protocol, ("ietf-routing:direct", "direct"))
                self.assertEqual(v4_rib_rt.last_updated, "2015-10-24T17:11:27+02:00")

            elif v4_rib_rt.destination_prefix == "0.0.0.0/0":
                self.assertFalse(v4_rib_rt.next_hop.outgoing_interface._changed())
                self.assertEqual(v4_rib_rt.next_hop.outgoing_interface, "")
                self.assertEqual(v4_rib_rt.next_hop.next_hop_address, "192.0.2.2")
                self.assertEqual(v4_rib_rt.route_preference, 5)
                self.assertIn(v4_rib_rt.source_protocol, ("ietf-routing:static", "static"))
                self.assertEqual(v4_rib_rt.last_updated, "2015-10-24T18:02:45+02:00")

            else:
                self.fail(f"Route with unexpected destination: {v4_rib_rt.destination_prefix}")

        v6_rib = rib_list["ipv6-master"]
        self.assertIn(v6_rib.address_family, ("ietf-ipv6-unicast-routing:ipv6-unicast", "ipv6-unicast"))
        self.assertTrue(v6_rib.default_rib, True)
        self.assertEqual(len(v6_rib.routes.route), 3)

        for v6_rib_rt in v6_rib.routes.route.values():
            if v6_rib_rt.destination_prefix == "2001:db8:0:1::/64":
                self.assertEqual(v6_rib_rt.next_hop.outgoing_interface, "eth0")
                self.assertFalse(v6_rib_rt.next_hop.next_hop_address._changed())
                self.assertEqual(v6_rib_rt.next_hop.next_hop_address, "")
                self.assertEqual(v6_rib_rt.route_preference, 0)
                self.assertIn(v6_rib_rt.source_protocol, ("ietf-routing:direct", "direct"))
                self.assertEqual(v6_rib_rt.last_updated, "2015-10-24T17:11:27+02:00")

            elif v6_rib_rt.destination_prefix == "2001:db8:0:2::/64":
                self.assertEqual(v6_rib_rt.next_hop.outgoing_interface, "eth1")
                self.assertFalse(v6_rib_rt.next_hop.next_hop_address._changed())
                self.assertEqual(v6_rib_rt.next_hop.next_hop_address, "")
                self.assertEqual(v6_rib_rt.route_preference, 0)
                self.assertIn(v6_rib_rt.source_protocol, ("ietf-routing:direct", "direct"))
                self.assertEqual(v6_rib_rt.last_updated, "2015-10-24T17:11:27+02:00")

            elif v6_rib_rt.destination_prefix == "::/0":
                self.assertFalse(v6_rib_rt.next_hop.outgoing_interface._changed())
                self.assertEqual(v6_rib_rt.next_hop.outgoing_interface, "")
                self.assertEqual(v6_rib_rt.next_hop.next_hop_address, "2001:db8:0:1::2")
                self.assertEqual(v6_rib_rt.route_preference, 5)
                self.assertIn(v6_rib_rt.source_protocol, ("ietf-routing:static", "static"))
                self.assertEqual(v6_rib_rt.last_updated, "2015-10-24T18:02:45+02:00")

            else:
                self.fail(f"Route with unexpected destination: {v6_rib_rt.destination_prefix}")

    @unittest.skip("Incorrect JSON serialisation")
    def test_roundtrip_operational_state(self):
        """
        Deserialise / serialise the example operational state for ietf-routing.

        This test currently fails:

        ietf-ipv4-unicast-routing and ietf-ipv6-unicast-routing both add a
        'destination-prefix', with a different type (and 'when' clause,
        restriction), for each. When serialising, currently pyangbind cannot
        decide which module to pick, so it generates JSON that looks like:

            'ribs': {'rib': [{'address-family': 'ietf-ipv4-unicast-routing:ipv4-unicast',
                      'default-rib': True,
                      'name': 'ipv4-master',
                      'routes': {'route': [{'ietf-ipv4-unicast-routing|ietf-ipv6-unicast-routing:destination-prefix': '192.0.2.1/24',
        """
        with open(os.path.join(os.path.dirname(__file__), "testdata", "operational.json"), "r") as fp:
            external_json = json.load(fp)

        instance = pybindJSONDecoder.load_ietf_json(external_json, self.bindings, "ietf-routing")

        pybind_json = json.loads(
            json.dumps(pybindIETFJSONEncoder.generate_element(instance, flt=True), cls=pybindIETFJSONEncoder, indent=4)
        )

        self.maxDiff = 20_000
        self.assertEqual(external_json, pybind_json, "JSON did not match the expected output.")


if __name__ == "__main__":
    unittest.main()
