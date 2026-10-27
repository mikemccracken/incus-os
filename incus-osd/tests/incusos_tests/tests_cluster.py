from .incus_test_vm import IncusTestCluster, IncusOSException

def TestClusterFormation(install_image):
    test_name = "cluster-formation"

    with IncusTestCluster(test_name, install_image) as cluster:
        cluster.WaitSystemReady()
        cluster.CreateCluster()

        # Every member should see the full cluster.
        for name, vm in cluster.members.items():
            members = vm.IncusRequest("/1.0/cluster/members")
            if len(members) != len(cluster.members):
                raise IncusOSException("member %s sees %d cluster members, expected %d" % (name, len(members), len(cluster.members)))

        # The IncusOS API of each member should be reachable through the first member.
        first = cluster.members["node1"]

        for name, vm in cluster.members.items():
            result = first.APIRequest("/1.0/system/network?target=" + name)
            if result["status_code"] != 200:
                raise IncusOSException("unexpected status code %d: %s" % (result["error_code"], result["error"]))

            addresses = [address.split("/")[0] for address in result["metadata"]["state"]["interfaces"]["enp5s0"]["addresses"]]
            if vm.GetIP() not in addresses:
                raise IncusOSException("expected IncusOS API response from member %s, got addresses %s" % (name, addresses))

def TestClusterEvacuation(install_image):
    test_name = "cluster-evacuation"

    with IncusTestCluster(test_name, install_image) as cluster:
        cluster.WaitSystemReady()
        cluster.CreateCluster()

        first = cluster.members["node1"]

        # An empty, stopped VM is enough to test instance placement and migration.
        first.IncusRequest("/1.0/instances?target=node2", method="POST", body={"name": "v1", "type": "virtual-machine", "source": {"type": "none"}})

        instance = first.IncusRequest("/1.0/instances/v1")
        if instance["location"] != "node2":
            raise IncusOSException("expected instance v1 to be on node2, found on " + instance["location"])

        # Evacuating the member should migrate the VM elsewhere.
        first.IncusRequest("/1.0/cluster/members/node2/state", method="POST", body={"action": "evacuate"})

        member = first.IncusRequest("/1.0/cluster/members/node2")
        if member["status"] != "Evacuated":
            raise IncusOSException("unexpected status for node2 after evacuation: " + member["status"])

        instance = first.IncusRequest("/1.0/instances/v1")
        if instance["location"] == "node2":
            raise IncusOSException("instance v1 wasn't migrated off of evacuated node2")

        # Restoring the member should bring the VM back.
        first.IncusRequest("/1.0/cluster/members/node2/state", method="POST", body={"action": "restore"})

        member = first.IncusRequest("/1.0/cluster/members/node2")
        if member["status"] != "Online":
            raise IncusOSException("unexpected status for node2 after restore: " + member["status"])

        instance = first.IncusRequest("/1.0/instances/v1")
        if instance["location"] != "node2":
            raise IncusOSException("expected instance v1 to be back on node2, found on " + instance["location"])
