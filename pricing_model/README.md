### Cost-Aware Monitor Module

此模块负责实现“成本可感知”的定价池。

- 通过Google提供的API访问GCP项目下的Billing Client和Compute Client对指定种类的机型进行价格监控。
  - 跳转Goolge定价网站：https://cloud.google.com/compute/all-pricing?hl=zh-CN#section-1
  - 但是**很奇怪**的一点是不是所有的在上述网站中的机型都在SKU API中可获得。但我又不想实现爬虫监听，所以最后手动筛选了可以从SKU API中估算定价的机器种类
    - 通用类型机型：C4, N4, E2, C3
    - 计算优化：C2D
    - 内存优化：M3 (太贵）
  - 表格中囊括的配置还是太多，需要根据任务缩小可选范围
  - 经过代码测试，并不是所有表格中的机型都在australia-southeast1都有提供

```json
{
'australia-southeast1-b': [
                          {'name': 'c3-standard-4', 'vcpu': 4, 'memory_mb': 16384, 'is_shared_core': False, 'region': 'australia-southeast1-b'}, 
                          {'name': 'c3-standard-8', 'vcpu': 8, 'memory_mb': 32768, 'is_shared_core': False, 'region': 'australia-southeast1-b'}, 
                          {'name': 'e2-standard-2', 'vcpu': 2, 'memory_mb': 8192, 'is_shared_core': False, 'region': 'australia-southeast1-b'}, 
                          {'name': 'e2-standard-4', 'vcpu': 4, 'memory_mb': 16384, 'is_shared_core': False, 'region': 'australia-southeast1-b'}, 
                          {'name': 'e2-standard-8', 'vcpu': 8, 'memory_mb': 32768, 'is_shared_core': False, 'region': 'australia-southeast1-b'}, 
                          {'name': 'n4-standard-2', 'vcpu': 2, 'memory_mb': 8192, 'is_shared_core': False, 'region': 'australia-southeast1-b'}, 
                          {'name': 'n4-standard-4', 'vcpu': 4, 'memory_mb': 16384, 'is_shared_core': False, 'region': 'australia-southeast1-b'}]
}

```


| Flavor         | vCPU | RAM | On-Demand Price | Note                                          |
| -------------- | ---- | --- | --------------- | --------------------------------------------- |
| c4-standard-2  | 2    | 7   | 0.1210825       | CPU 0.0433125 / 1 hour                        |
| c4-standard-4  | 4    | 15  | 0.2470875       | RAM 0.0049225 / 1 gibibyte hour               |
| c4-standard-8  | 8    | 30  | 0.494175        |                                               |
| n4-standard-2  | 2    | 8   | 0.118465        | CPU 0.0407225 / 1 hour                        |
| n4-standard-4  | 4    | 16  | 0.23693         | RAM 0.0046275 / 1 gibibyte hour               |
| n4-standard-8  | 8    | 32  | 0.47386         |                                               |
| c3-standard-4  | 4    | 16  | 0.25201         | CPU 0.0433125 / 1 hour                        |
| c3-standard-8  | 8    | 32  | 0.50402         | RAM 0.0049225 / 1 gibibyte hour               |
| e2-standard-2  | 2    | 8   | 0.095082        | CPU 0.03095064 / 1 hour                       |
| e2-standard-4  | 4    | 16  | 0.190164        | RAM 0.00414759 / 1 gibibyte hour              |
| e2-standard-8  | 8    | 32  | 0.380328        |                                               |
| c2d-standard-2 | 2    | 8   | 0.12888         | CPU 0.041964 / 1 hour                         |
| c2d-standard-4 | 4    | 16  | 0.25776         | RAM 0.005619 / 1 gibibyte hour                |
| c2d-standard-8 | 8    | 32  | 0.51552         |                                               |
| M3             |      |     |                 | M3的RAM都是几百的，太大了，太贵了。直接不考虑 |


- `compute_v1.ListMachineTypesRequest`构成一个查询“当前项目可以创建的机器实例”的请求，作为`compute client`的参数。
- `billing_client.list_skus(parent=self.compute_service_id)`通过Compute Engine的服务id查找旗下所有的sku的定价
  - 所需要的sku的描述类似“N2 Instance Core running in Sydney”这种是我们所需要的单vpcu和Ram的定价的sku
  - 目前只考虑On-Demand：`sku.category.usage_type=="OnDemand"`
  - 目前只考虑指定region：` <region> in sku.service_regions`
  - 过滤出所有关于估计定价相关的sku
