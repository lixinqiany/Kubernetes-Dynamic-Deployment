import logging, os, warnings
from kubernetes import client
from pricing_model.Monitor import GCPMonitor
from optimizer.CABFD import CABFD
from utils.resources import Pod, Node
from cluster.Monitor import ClusterMonitor
from datetime import datetime
warnings.filterwarnings("ignore")

class Scheduler:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self._setup()

    def _setup(self):
        self.cabfd = CABFD()
        self.cluster_monitor = ClusterMonitor()
        self.gcp_monitor = GCPMonitor(project_id=os.getenv("GCP_PROJECT", default="single-cloud-ylxq"))

    def _get_available_nodes(self):
        self.cluster_monitor.refresh()
        ip2type = self.gcp_monitor.get_instance_type()
        for k8s_node, node in self.cluster_monitor.node_cache:
            node.type = ip2type.get(node.internalIP, None)
        logging.info(f"调度器获取{datetime.today().strftime('%H:%M:%S')}时的集群内节点")

        return [x for x in self.cluster_monitor.node_cache if x[1].name!="master"]

    def _get_pendding_pods(self):
        self.cluster_monitor.refresh()
        logging.info(f"调度器获取{datetime.today().strftime('%H:%M:%S')}时的pending pods")
        return self.cluster_monitor.pending_pods

    def schedule(self):
        logging.info(f"开始准备调度")
        pendding_pods = [p[1] for p in self._get_pendding_pods()]
        nodes = self._get_available_nodes()
        logging.info(f"待调度节点如下：")
        _ = [logging.info(x) for x in pendding_pods]
        logging.info(f"已有节点如下：")
        _ = [logging.info(x) for x in nodes]

        if nodes == []:
            result = self.cabfd.optimize(pendding_pods)
            self.cabfd.summary(result)




if __name__=="__main__":
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../configurations/single-cloud-ylxq-ed1608c43bb4.json"
    os.environ["GCP_PROJECT"] = "single-cloud-ylxq"  # 可选自定义项目变量
    scheduler = Scheduler()
    scheduler.schedule()
