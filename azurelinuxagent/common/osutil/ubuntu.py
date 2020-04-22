#
# Copyright 2018 Microsoft Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requires Python 2.6+ and Openssl 1.0+
#
import os
import time

import azurelinuxagent.common.logger as logger
import azurelinuxagent.common.utils.shellutil as shellutil
from azurelinuxagent.common import conf

from azurelinuxagent.common.osutil.default import DefaultOSUtil


UBUNTU_20_04_IMAGE_PATH = "/etc/ub20-image"

def get_python_symlink_path_if_ubuntu_20_04_image():
    if not os.path.exists(UBUNTU_20_04_IMAGE_PATH):
        return None
    return os.path.join(conf.get_lib_dir(), "python")

class Ubuntu14OSUtil(DefaultOSUtil):

    def __init__(self):
        super(Ubuntu14OSUtil, self).__init__()
        self.jit_enabled = True
        self.service_name = self.get_service_name()

    @staticmethod
    def get_service_name():
        return "walinuxagent"

    def start_network(self):
        return shellutil.run("service networking start", chk_err=False)

    def stop_agent_service(self):
        return shellutil.run("service {0} stop".format(self.service_name), chk_err=False)

    def start_agent_service(self):
        return shellutil.run("service {0} start".format(self.service_name), chk_err=False)

    def remove_rules_files(self, rules_files=""):
        pass

    def restore_rules_files(self, rules_files=""):
        pass

    def get_dhcp_lease_endpoint(self):
        return self.get_endpoint_from_leases_path('/var/lib/dhcp/dhclient.*.leases')


class Ubuntu12OSUtil(Ubuntu14OSUtil):
    def __init__(self):
        super(Ubuntu12OSUtil, self).__init__()

    # Override
    def get_dhcp_pid(self):
        return self._get_dhcp_pid(["pidof", "dhclient3"])

    def mount_cgroups(self):
        pass


class Ubuntu16OSUtil(Ubuntu14OSUtil):
    """
    Ubuntu 16.04, 16.10, and 17.04.
    """
    def __init__(self):
        super(Ubuntu16OSUtil, self).__init__()
        self.service_name = self.get_service_name()

    def register_agent_service(self):
        return shellutil.run("systemctl unmask {0}".format(self.service_name), chk_err=False)

    def unregister_agent_service(self):
        return shellutil.run("systemctl mask {0}".format(self.service_name), chk_err=False)

    def mount_cgroups(self):
        """
        Mounted by default in Ubuntu 16.04
        """
        pass


class Ubuntu18OSUtil(Ubuntu16OSUtil):
    """
    Ubuntu 18.04
    """
    def __init__(self):
        super(Ubuntu18OSUtil, self).__init__()
        self.service_name = self.get_service_name()

    def get_dhcp_pid(self):
        return self._get_dhcp_pid(["pidof", "systemd-networkd"])

    def start_network(self):
        return shellutil.run("systemctl start systemd-networkd", chk_err=False)

    def stop_network(self):
        return shellutil.run("systemctl stop systemd-networkd", chk_err=False)

    def start_dhcp_service(self):
        return self.start_network()

    def stop_dhcp_service(self):
        return self.stop_network()

    def start_agent_service(self):
        return shellutil.run("systemctl start {0}".format(self.service_name), chk_err=False)

    def stop_agent_service(self):
        return shellutil.run("systemctl stop {0}".format(self.service_name), chk_err=False)


class UbuntuOSUtil(Ubuntu16OSUtil):
    def __init__(self):
        super(UbuntuOSUtil, self).__init__()

    def restart_if(self, ifname, retries=3, wait=5):
        """
        Restart an interface by bouncing the link. systemd-networkd observes
        this event, and forces a renew of DHCP.
        """
        retry_limit=retries+1
        for attempt in range(1, retry_limit):
            return_code=shellutil.run("ip link set {0} down && ip link set {0} up".format(ifname))
            if return_code == 0:
                return
            logger.warn("failed to restart {0}: return code {1}".format(ifname, return_code))
            if attempt < retry_limit:
                logger.info("retrying in {0} seconds".format(wait))
                time.sleep(wait)
            else:
                logger.warn("exceeded restart retries")


class UbuntuSnappyOSUtil(Ubuntu14OSUtil):
    def __init__(self):
        super(UbuntuSnappyOSUtil, self).__init__()
        self.conf_file_path = '/apps/walinuxagent/current/waagent.conf'
