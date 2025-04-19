**Kubernetes关于CPU和RAM的背景**

> 1. 确保节点剩余CPU>Pod.requests.cpu才会被调度，资源竞争时至少能获得Pod.requests.cpu数量的vCPU。当尝试使用超过Pod.limits.cpu时，不会终止容器，理论上可能获得暂时超额CPU数量，但是在其他pod需要cpu时超额部分会被收回。
> 2. 内存不可压缩。节点必须有足够Pod.requests.memory才会调度pod，但是一旦超过Pod.limits.ram就会被强制终止，被驱逐。

## 二维Bin-Packing问题

#### Problem Formulation

- 物品 is Pod ($cpu_i, ram_i$)
  - $cpu_i$ pod请求的vcpu数目
  - $ram_i$ pod请求的ram量
- 箱子 is Node ($C_j, M_j$)
  - $C_i$ 节点vCPU储备
  - $M_j$ 节点RAM储备
- **目标**： 使用最少数量的节点分配所有pod

决策变量 $x_{ij} \in \{0,1\}$ （Pod $i$ 是否部署到节点 $j$），$y_j \in \{0,1\}$ （节点 $j$ 是否被使用）

**目标函数**

$$
\min \sum_{j=1}^n y_j
$$

**约束条件**

$$
\sum_{j=1}^n x_{ij} = 1 \quad \forall i \quad (\text{每个 Pod 必须被分配})
$$

$$
\sum_{i=1}^m c_i x_{ij} \leq C_j y_j \quad \forall j \quad (\text{CPU 容量约束})
$$

$$
\sum_{i=1}^m m_i x_{ij} \leq M_j y_j \quad \forall j \quad (\text{内存容量约束})
$$
