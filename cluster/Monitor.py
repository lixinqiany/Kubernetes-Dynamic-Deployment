from kubernetes import config,client
import logging, time
from utils.resources import Node, Pod

class ClusterMonitor:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,  # 设置全局日志级别（DEBUG及以上会记录）
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',  # 时间格式
        )
        self._setup()

    def _setup(self):
        config.load_kube_config("../configurations/.kube/config")
        self.core_v1 = client.CoreV1Api()
        self.node_cache = []
        self.pod_cache = []
        self.last_update = None

    def refresh(self):
        self.get_nodes()
        self.get_pods()
        self.last_update = time.time()

    def get_nodes(self):
        self.node_cache.clear()
        try:
            nodes = self.core_v1.list_node().items
            for node in nodes:
                self.node_cache.append(self._parse_node(node))
            logging.info(f"Obtain {len(self.node_cache)}  in this Cluster...")
        except Exception as e:
            logging.error(e)

    def _parse_node(self, node):
        addresses = {x.type: x.address for x in node.status.addresses}
        status = "NotReady"
        for cond in node.status.conditions:
            if cond.type == "Ready":
                status = "Ready" if cond.status=="True" else "NotReady"

        node_info = {
            "name": node.metadata.name,
            "InternalIP": addresses.get("InternalIP", None),
            "Hostname":addresses.get("Hostname", None),
            "CPU":node.status.capacity["cpu"],
            "RAM": self._parse_node_memory(node.status.capacity["memory"]),
            "status": status
        }
        #logging.info(f"Parse Node ->\n\t{node_info}")
        return (node, Node(node.metadata.name, node_info))

    def _parse_node_memory(self, mem_str):
        if mem_str.endswith("Ki"):
            return float(mem_str[:-len("Ki")])/1024/1024
        return None

    def get_pods(self):
        self.pod_cache.clear()
        try:
            pods = self.core_v1.list_pod_for_all_namespaces().items
            pods = [x for x in pods if x.metadata.namespace == "default"]
            for pod in pods:
                self.pod_cache.append(self._parse_pod(pod))
            logging.info(f"Obtain {len(self.pod_cache)} pods in the default namespace")
        except Exception as e:
            logging.error(e)

    def _parse_pod(self, pod):
        name, ns = pod.metadata.name, pod.metadata.namespace
        status = pod.status.phase
        node = pod.spec.node_name
        cpu = sum([self._parse_pod_cpu(x.resources.requests["cpu"]) for x in pod.spec.containers])
        ram = sum([self._parse_pod_ram(x.resources.requests["memory"]) for x in pod.spec.containers])

        pod_info = {
            "name":name,
            "namespace":ns,
            "status": status,
            "node": node,
            "CPU":cpu, "RAM":ram
        }
        #logging.info(f"Parse Pod ->\n\t{pod_info}")
        return (pod, Pod(pod_info))

    def _parse_pod_cpu(self, cpu):
        if cpu.endswith("m"):
            return float(cpu[:-len("m")])/1000
        else:
            return float(cpu)

    def _parse_pod_ram(self, ram):
        if ram.endswith("Gi"):
            return float(ram[:-len("Gi")])
        elif ram.endswith("Mi"):
            return float(ram[:-len("Mi")]) / 1024

    @property
    def pending_pods(self):
        return [x for x in self.pod_cache if x[1].status == "Pending"]


if __name__=="__main__":
    monitor = ClusterMonitor()
    monitor.get_nodes()
    monitor.get_pods()
    print(monitor.pending_pods)