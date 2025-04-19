#!/usr/bin/env python3
import re,os
from google.cloud import billing_v1
from googleapiclient.discovery import build
from google.auth import default

COMPUTE_SVC = "services/6F81-5844-456A"

REGEX = {
    "vcpu": re.compile(r"(?:core|cpu)", re.I),
    "ram" : re.compile(r"(?:ram|memory)", re.I)
}

def get_machine_spec(machine_type: str, project: str, zone: str):
    creds, _ = default()
    compute = build("compute", "v1", credentials=creds, cache_discovery=False)
    mt = compute.machineTypes().get(
        project=project, zone=zone, machineType=machine_type).execute()
    return mt["guestCpus"], mt["memoryMb"] / 1024  # GiB

def get_unit_price(kind: str, region: str, skus):
    pat = REGEX[kind]
    for sku in skus:
        if not pat.search(sku.description):
            continue
        expr = sku.pricing_info[0].pricing_expression
        money = expr.tiered_rates[0].unit_price
        usd   = money.units + money.nanos / 1e9
        rate  = usd / expr.base_unit_conversion_factor
        if expr.usage_unit in ("h", "GiBy.h"):
            rate /= 3600
        return rate
    raise RuntimeError(f"{kind} SKU not found in region {region}")

def price_machine(machine_type: str, project: str, region: str):
    client = billing_v1.CloudCatalogClient()
    all_skus = list(client.list_skus(parent=COMPUTE_SVC))
    region_skus = [s for s in all_skus
                   if region in s.service_regions or "global" in s.service_regions]
    vcpu_price = get_unit_price("vcpu", region, region_skus)
    ram_price  = get_unit_price("ram",  region, region_skus)

    vcpu, ram = get_machine_spec(machine_type, project, f"{region}-a")
    return vcpu * vcpu_price + ram * ram_price  # USD / s

if __name__ == "__main__":
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./configurations/single-cloud-ylxq-bdc460579827.json"
    os.environ["GCP_PROJECT"] = "single-cloud-ylxq"  # 可选自定义项目变量
    mt = "c2d-standard-4"
    usd_per_sec = price_machine(mt, project="single-cloud-ylxq", region="us-central1")
    print(f"{mt}: ${usd_per_sec*3600:.4f}/hour")
