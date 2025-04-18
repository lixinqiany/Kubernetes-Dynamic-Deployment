from kubernetes import client, config, watch
from datetime import datetime
import logging
import sys,time

# 配置日志
logging.basicConfig(
    stream=sys.stdout,
    format='%(asctime)s - %(levelname)s: %(message)s',
    level=logging.INFO
)


def watch_pending_pods():
    # 初始化客户端
    try:
        # 集群内运行使用
        config.load_kube_config('configurations/.kube/config')
        # 本地测试使用（注释上一行，取消注释下一行）
        # config.load_kube_config()
    except Exception as e:
        logging.error(f"初始化Kubernetes客户端失败: {str(e)}")
        return

    v1 = client.CoreV1Api()
    w = watch.Watch()
    resource_version = '0'

    while True:
        try:
            logging.info("开始监听Pending Pod事件...")

            # 创建事件流（阻塞式）
            stream = w.stream(
                v1.list_pod_for_all_namespaces,
                field_selector="status.phase=Pending",
                resource_version=resource_version,
                timeout_seconds=300
            )

            for event in stream:
                pod = event['object']
                resource_version = pod.metadata.resource_version

                # 只处理ADDED事件
                if event['type'] == 'ADDED':
                    print_pod_info(pod)

        except Exception as e:
            logging.error(f"监听中断，5秒后重试... 错误: {str(e)}")
            time.sleep(5)


def print_pod_info(pod):
    """打印Pod详细信息"""
    status = pod.status
    spec = pod.spec

    # 获取基本信息
    info = {
        'name': pod.metadata.name,
        'namespace': pod.metadata.namespace,
        'created_at': pod.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        'reason': status.container_statuses[0].state.waiting.reason if status.container_statuses else "Unknown",
        'message': status.container_statuses[0].state.waiting.message if status.container_statuses else "No message"
    }

    # 格式化输出
    output = f"""
=== 发现Pending Pod ===
名称:       {info['name']}
命名空间:   {info['namespace']}
创建时间:   {info['created_at']}
原因:       {info['reason']}
消息:       {info['message']}
节点选择器: {spec.node_selector or 'None'}
容忍配置:   {[toleration.key for toleration in spec.tolerations] if spec.tolerations else 'None'}
"""
    logging.info(output)


if __name__ == "__main__":
    logging.info("启动Pending Pod监控器")
    try:
        watch_pending_pods()
    except KeyboardInterrupt:
        logging.info("监控器已手动停止")