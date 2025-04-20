import logging, json, os
from utils.resources import Pod,Node

class BFD:
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
        sorted_pods = sorted(pods, key=lambda x:-x.memory)

        schedule = []
        for pod in sorted_pods:
            candidates = []
            best = None
            candidates = self._find_in_existing_nodes(schedule, pod)
            if candidates != []:
                best = self._get_node_least_ram(candidates, flag=True)
                if best is not None:
                    best.pods.append(pod)
                    continue

            candidates = self._find_possible_types(pod)
            best = self._get_node_least_ram(candidates)
            best.name = "created"
            best.pods.append(pod)
            schedule.append(best)

        return schedule

    def _find_in_existing_nodes(self, nodes, pod):
        request_cpu, request_ram = pod.cpu, pod.memory

        return [n for n in nodes
                if n.available_cpu >= request_cpu and n.availbale_memory >= request_ram]

    def _find_possible_types(self, pod:Pod):
        return [Node("not-created", x)
                for x in self.gcp_pricing
                if x["CPU"]>=pod.cpu and x["RAM"]>=pod.memory]

    def _get_node_least_ram(self, nodes, flag=False):
        if flag:
            return min(nodes, key=lambda x:(x.availbale_memory,))
        return min(nodes, key=lambda x:(x.availbale_memory,x.price))

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



if __name__=="__main__":
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../configurations/single-cloud-ylxq-ed1608c43bb4.json"
    os.environ["GCP_PROJECT"] = "single-cloud-ylxq"  # 可选自定义项目变量
    bfd = BFD()
    request1 = {"CPU": 0.7, "RAM": 0.2}
    request2 = {"CPU": 1, "RAM": 0.7}
    request3 = {"CPU": 0.1, "RAM": 1}
    request4 = {"CPU": 0.2, "RAM": 0.9}
    setup = [20, 20, 40, 5]
    requests = [request1, request2, request3, request4]
    pods = []
    for i, s in zip(setup, requests):
        for _ in range(i):
            pods.append(Pod(s))
    result = bfd.optimize(pods)
    bfd.summary(result)
