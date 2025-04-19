from google.cloud import compute_v1, billing_v1
import os, logging, json
from collections import defaultdict

class GCPMonitor:
    def __init__(self, project_id = None, region=None, zone='b'):
        logging.basicConfig(
            level=logging.INFO,  # 设置全局日志级别（DEBUG及以上会记录）
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',  # 时间格式
        )

        self.project_id = project_id or os.getenv("GCP_PROJECT")
        self.region = region or "australia-southeast1"
        self.zone = self.region + "-" + zone
        self._init_clients()
        self.flavor_pool = self._read_flavor_pool()
        self.machine_cache = self.fetch_machine_specs()
        self.pricing_cache = self.fetch_pricing_data()
        self.machine_price_cache = self.cal_VM_price()

    def _init_clients(self):
        self.compute_client = compute_v1.MachineTypesClient()
        self.billing_client = billing_v1.CloudCatalogClient()
        logging.info("Connecting to Compute Client and Billing Client")

        services = list(self.billing_client.list_services())
        self.compute_service_id = next(
            s.name for s in services
            if s.display_name == "Compute Engine"
        )
        logging.info(f"Retrieving Compute Engine Service {self.compute_service_id} to get SKUs")

    def _read_flavor_pool(self):
        """
        We have already narrowed the range of VMs in project
        :return: A list containing names of flavors
        """
        with open('../data/pre-defined-Flavors.json', 'r') as fp:
            gcp_flavors = json.load(fp)['gcp']
            logging.info(f"Flavor Pool Loaded as {gcp_flavors}")
            return gcp_flavors

    def fetch_machine_specs(self):
        """
        Get all available flavors of VMs in GCP project
        Do intersection with pre-defined flavors of VMs
        :return: available machine types
        """
        specs = defaultdict(list)

        logging.info(f"Fetching machine types in {self.region}")
        try:
            request = compute_v1.ListMachineTypesRequest(
                project=self.project_id,
                zone=self.zone  # 每个区域选择第一个可用区
            )
            machine_types = self.compute_client.list(request)
            _ = [specs[mt.name.split("-")[0]].append(
                {
                    "name": mt.name,
                    "vcpu": mt.guest_cpus,
                    "memory_mb": mt.memory_mb,
                    "is_shared_core": "shared-core" in mt.name,
                    "region": self.region
                }
            )
                for mt in machine_types if mt.name in self.flavor_pool]
            # assert len(self.flavor_pool) == len(specs)
        except Exception as e:
            logging.error(f"Error fetching specs in {self.region}: {str(e)}")

        return specs

    def fetch_pricing_data(self):
        """获取计算引擎的定价数据"""
        pricing_cache = defaultdict(dict)
        skus = self.billing_client.list_skus(parent=self.compute_service_id)
        skus = [sku
                for sku in skus
                if sku.category.usage_type=="OnDemand" and
                self.region in sku.service_regions and
                ("Instance Core" in sku.description or "Instance Ram" in sku.description) and
                len(sku.description.split(" ")) == 6]

        for sku in skus:
            entry = self._parse_sku(sku)
            if entry:
                pricing_cache[entry['id']][entry['resource']] = entry['pricing_info']

        return pricing_cache

    def _parse_sku(self, sku):
        """解析单个SKU的数据结构"""
        try:
            # 切分后第一个是类似“n4”, "c3"类似
            mt_id = sku.description.lower().split()[0]
            if self.machine_cache == {}:
                raise Exception("请先获取项目可用VM类型")
            else:
                if mt_id not in self.machine_cache.keys():
                    return None
            # 解析定价信息
            pricing_info = {}
            for tier in sku.pricing_info:
                pricing_expression = tier.pricing_expression
                usage_unit_count = pricing_expression.usage_unit_description

                for tier_rate in pricing_expression.tiered_rates:
                    price = tier_rate.unit_price
                    currency = price.currency_code
                    amount = price.nanos / 1e9

                    pricing_info = {
                        "currency": currency,
                        "hourly_rate": amount,
                        "usage_unit": usage_unit_count
                    }
            logging.info(f"Get {mt_id}'s {sku.category.resource_group} price => {pricing_info['hourly_rate']}")
            return {
                "sku_id": sku.sku_id,
                "id": mt_id,
                "region": self.region,
                "resource": sku.category.resource_group, # cpu or ram
                "pricing_info": pricing_info
            }
        except Exception as e:
            logging.error(f"Error parsing SKU {sku.sku_id}: {str(e)}")
            return None

    def cal_VM_price(self):
        machine_price_cache = []
        for type, VMs in self.machine_cache.items():
            cpu, ram = self.pricing_cache[type]['CPU'], self.pricing_cache[type]['RAM']
            for VM in VMs:
                temp = {}
                name = VM['name']
                temp['type'] = name
                vcpu, memory = VM['vcpu'], VM['memory_mb'] / 1024
                temp["CPU"], temp["RAM"] = vcpu,  memory
                price = vcpu * cpu['hourly_rate'] + memory * ram['hourly_rate']
                temp["price"] = price
                machine_price_cache.append(temp)
                logging.info(f"{name} Calculated as {price:.6f}")

        return machine_price_cache

    def export(self):
        with open("../data/pricing.json", 'w') as fp:
            res = {'gcp': self.machine_price_cache}
            json.dump(res, fp)




if __name__=="__main__":
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../configurations/single-cloud-ylxq-ed1608c43bb4.json"
    os.environ["GCP_PROJECT"] = "single-cloud-ylxq"  # 可选自定义项目变量
    gcp = GCPMonitor()
    gcp.export()


