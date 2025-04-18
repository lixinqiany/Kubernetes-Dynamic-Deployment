from kubernetes import client, config, watch
import time


def main():
    # 加载kubeconfig配置
    config.load_kube_config('configurations/.kube/config')  # 本地测试用，集群部署需改为使用ServiceAccount
    v1 = client.CoreV1Api()

    # 调度器名称
    scheduler_name = "test-scheduler"
    pods = get_pending_pods(v1)
    valid_pods = filter_unscheduled_pods(pods, scheduler_name)
    for pod in valid_pods:
        process_pod(pod, v1)


def get_pending_pods(v1):
    """获取待调度的Pod列表"""
    try:
        field_selector = "status.phase=Pending"
        return v1.list_namespaced_pod(
            namespace="default",
            field_selector=field_selector
        ).items
    except Exception as e:
        print(f"获取Pod列表失败: {str(e)}")
        return []

def filter_unscheduled_pods(pods, scheduler_name):
    """筛选需要本调度器处理的Pod"""
    valid_pods = []
    for pod in pods:
        if not pod.spec.scheduler_name:
            print(f"发现未分配调度器的Pod: {pod.metadata.name}")
            valid_pods.append(pod)
        elif pod.spec.scheduler_name == scheduler_name:
            print(f"发现已分配本调度器的Pod: {pod.metadata.name}")
            valid_pods.append(pod)
    return valid_pods

def process_pod(pod, v1):
    """处理单个Pod调度流程"""
    pod_name = pod.metadata.name
    print(f"开始处理Pod: {pod_name}")

    if node_name := select_target_node(v1):
        if bind_pod_to_node(pod_name, node_name,v1):
            return True
    else:
        print(f"没有可用节点可以调度 {pod_name}")
    return False

def select_target_node(v1):
    """选择目标节点（核心筛选逻辑）"""
    try:
        nodes = v1.list_node().items
        for node in nodes:
            if is_valid_node(node):
                print(f"找到有效节点: {node.metadata.name}")
                return node.metadata.name
        return None
    except Exception as e:
        print(f"节点选择失败: {str(e)}")
        return None

def is_valid_node(node):
    """验证节点是否符合调度条件"""
    node_ready = any(
        cond.type == "Ready" and cond.status == "True"
        for cond in node.status.conditions
    )
    has_work1_label = node.metadata.name == "master-1"
    return node_ready and has_work1_label

def bind_pod_to_node( pod_name, node_name,v1):
    """执行Pod绑定操作"""
    try:
        target_ref = client.V1ObjectReference(
            api_version="v1",
            kind="Node",
            name=node_name
        )
        print(target_ref)
        metadata = client.V1ObjectMeta(
            name=pod_name
        )
        binding_body = client.V1Binding(
            metadata=metadata,
            target=target_ref
        )
        api_response = v1.create_namespaced_pod_binding(
            name=pod_name,
            namespace="default",
            body=binding_body
        )
        print(f"成功绑定 {pod_name} 到 {node_name}")
        return True
    except Exception as e:
        if True:
            print(f"绑定冲突: {pod_name} 可能已被其他调度器处理")
            print(f"绑定操作失败: {str(e)}")
        return False

if __name__ == "__main__":
    main()