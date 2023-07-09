#!/usr/bin/env python

import os
import os.path
import unittest

from pyangbind.lib.xpathhelper import YANGPathHelper
from tests.base import PyangBindTestCase


class OpenconfigInterfacesTests(PyangBindTestCase):
    yang_files = [
        os.path.join("openconfig", "%s.yang" % fname)
        for fname in ["openconfig-interfaces", "openconfig-if-aggregate", "openconfig-if-ip"]
    ]
    pyang_flags = [
        "-p %s" % os.path.join(os.path.dirname(__file__), "include"),
        "--use-xpathhelper",
        "--lax-quote-checks",
    ]
    split_class_dir = True
    module_name = "ocbind"

    remote_yang_files = [
        {
            "local_path": "include",
            "remote_prefix": "https://raw.githubusercontent.com/robshakir/yang/master/standard/ietf/RFC/",
            "files": ["ietf-inet-types.yang", "ietf-yang-types.yang", "ietf-interfaces.yang"],
        },
        {
            "local_path": "include",
            "remote_prefix": "https://raw.githubusercontent.com/openconfig/public/8527e6426cf136930ff24f60939994949cefc073/release/models/",
            "files": [
                "openconfig-extensions.yang",
                "types/openconfig-types.yang",
                "vlan/openconfig-vlan.yang",
                "vlan/openconfig-vlan-types.yang",
                "types/openconfig-inet-types.yang",
                "types/openconfig-yang-types.yang",
            ],
        },
        {
            "local_path": "openconfig",
            "remote_prefix": "https://raw.githubusercontent.com/openconfig/public/8527e6426cf136930ff24f60939994949cefc073/release/models/",
            "files": [
                "interfaces/openconfig-if-ip.yang",
                "interfaces/openconfig-if-ethernet.yang",
                "interfaces/openconfig-if-aggregate.yang",
                "interfaces/openconfig-if-types.yang",
                "interfaces/openconfig-interfaces.yang",
            ],
        },
    ]

    @classmethod
    def _fetch_remote_yang_files(cls):
        super()._fetch_remote_yang_files()

        # Fix the following pyang error:
        # pyangbind/tests/integration/openconfig-interfaces/openconfig/openconfig-if-ethernet.yang:427:
        # warning: node "openconfig-interfaces::state" is config false and is
        # not part of the accessible tree

        # This has since been fixed in openconfig/public:
        # https://github.com/openconfig/public/commit/d31dd1a137022700daa9c3ec33e471c48fd431cf
        # However, upgrading to the latest version of the openconfig models
        # would require many changes to the expected output
        need_fixes = ["openconfig-if-aggregate.yang", "openconfig-if-ethernet.yang"]
        for dirpath, dirnames, filenames in os.walk(cls._test_path):
            for need_fix in need_fixes:
                if need_fix in filenames:
                    with open(os.path.join(dirpath, need_fix), "r") as f:
                        yang_text = f.read()
                    yang_text = yang_text.replace("oc-if:state/oc-if:type", "oc-if:config/oc-if:type")
                    with open(os.path.join(dirpath, need_fix), "w") as f:
                        f.write(yang_text)

    def setUp(self):
        self.yang_helper = YANGPathHelper()
        self.instance = self.ocbind.openconfig_interfaces(path_helper=self.yang_helper)

    def test_001_populated_intf_type(self):
        i0 = self.instance.interfaces.interface.add("eth0")
        self.assertEqual(len(i0.config.type._restriction_dict), 1)


if __name__ == "__main__":
    unittest.main()
