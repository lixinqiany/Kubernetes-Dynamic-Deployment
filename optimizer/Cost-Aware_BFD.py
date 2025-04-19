from utils.resources import Pod, Node
from pricing_model.Monitor import GCPMonitor
import logging, os, json

class CABFD:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,  # 设置全局日志级别（DEBUG及以上会记录）
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',  # 时间格式
        )
        self._load_pricing_model()

    def _load_pricing_model(self):
        try:
            with open("../data/pricing.json", 'r') as fp:
                self.gcp_pricing = json.load(fp)['gcp']
                logging.info("Initializing Pricing Model from GCP")
        except Exception as e:
            logging.error(e)
            raise

    def optimize(self, pods):
        sorted_pods = sorted(pods, key=lambda x:(-x.memory, -x.cpu))

        schedule = []
        for pod in sorted_pods:
            candidates = []
            candidates = self._find_in_existing_nodes(schedule, pod)
            candidates += self._find_possible_types(pod)
            best = self._find_best(candidates, pod)
            best.pods.append(pod)
            if best in schedule:
                continue
            schedule.append(best)
            #best.price = 0
            best.name="created"

        return schedule

    def summary(self, schedule):
        cnt = 0
        tot_price = 0
        for node in schedule:
            cnt +=1
            type = node.type
            price = node.price
            tot_price += price
            vcpu, ram = node.cpu, node.memory
            pods = [(pod.cpu, pod.memory) for pod in node.pods]
            logging.info(f"创建节点{cnt}, 类型为{type}, 价格为{price}, 配置为{vcpu} vCPU和{ram}G RAM"
                         f"\n\t 部署的pod为 {pods}"
                         f"\n\t 占用CPU{node.occupied_cpu}个, 占用Memory{node.occupied_memory}G"
                         f"\n\t CPU占用率{100*node.occupied_cpu/vcpu:.2f}%, Memory占用率{100*node.occupied_memory/ram:.2f}%")
        logging.info(f"总价为{tot_price}")
    def _find_in_existing_nodes(self, nodes, pod):
        request_cpu, request_ram = pod.cpu, pod.memory

        return [n for n in nodes
                if n.available_cpu >= request_cpu and n.availbale_memory >= request_ram]

    def _find_possible_types(self, pod:Pod):
        cnt = 0
        return [Node("not-created", x)
                for x in self.gcp_pricing
                if x["CPU"]>=pod.cpu and x["RAM"]>=pod.memory]

    def _find_best(self, nodes, pod):
        best = max(nodes, key=lambda x: self._score(x, pod, nodes))
        #print("+"*10)
        #for node in nodes:
        #    logging.info(f"当前 {node.name}={node.type} 得分 {self._score(node, pod, nodes)}")
        return best

    def _score(self, node:Node, pod:Pod, candidates):
        avai_cpu, avai_ram = node.available_cpu, node.availbale_memory
        ram_util = 1-(avai_cpu - pod.cpu)/node.cpu
        cpu_util = 1-(avai_ram - pod.memory)/node.memory
        price = 1 - (node.price / max(x.price for x in candidates))
        if node.name == "created":
            price = 1 - (0 / max(x.price for x in candidates))

        return 0.3*ram_util + 0.2*cpu_util + 0.5 * price


if __name__=="__main__":
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../configurations/single-cloud-ylxq-ed1608c43bb4.json"
    os.environ["GCP_PROJECT"] = "single-cloud-ylxq"  # 可选自定义项目变量
    cabfd = CABFD()
    request1 = {"CPU":2, "RAM":0.5}
    request2 = {"CPU":1, "RAM":2}
    request3 = {"CPU":4, "RAM":1}
    pods = [
        Pod(request1),
        Pod(request2),
        Pod(request3),
        Pod(request1),
        Pod(request2),
        Pod(request2),
    ]
    result = cabfd.optimize(pods)
    cabfd.summary(result)