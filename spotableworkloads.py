from datetime import timedelta
from kubernetes import client, config, utils

def is_stateless(deployment):
    # Check if the deployment is stateless.
    if deployment.spec.template.spec.restart_policy != "Always":
        return False, "The deployment is not stateless"
    return True, ""

def has_replica_set(deployment):
    # Check if the deployment has more than one replica.
    if deployment.spec.replicas is None or deployment.spec.replicas < 2:
        return False, "The deployment does not have more than one replica"
    return True, ""

def gets_ready_quickly(deployment, v1):
    # Check the time it takes for pods to become ready.
    # Construct label selector from deployment.spec.selector.matchLabels
    label_selector = ",".join([f"{k}={v}" for k, v in deployment.spec.selector.match_labels.items()])
    #print("Label selector:")
    #print(label_selector)
    pods = v1.list_namespaced_pod(deployment.metadata.namespace, label_selector=label_selector).items
    #print(pods)
    if not pods:
        return False, "The deployment has no pods"
    for pod in pods:
        scheduled_time = None
        ready_time = None
        for condition in pod.status.conditions:
            if condition.type == "PodScheduled":
                scheduled_time = condition.last_transition_time
            elif condition.type == "Ready":
                ready_time = condition.last_transition_time
        if scheduled_time is None or ready_time is None:
            return False, "Pod schedule time or ready time is missing"
        if (ready_time - scheduled_time) > timedelta(minutes=2):
            return False, "The deployment's pods take longer than 2 minutes to become ready"
    return True, ""

def is_safe_to_evict(deployment):
    # Check if the deployment has the label cluster-autoscaler.kubernetes.io/safe-to-evict set to "false"
    if deployment.metadata.labels is not None and deployment.metadata.labels.get('cluster-autoscaler.kubernetes.io/safe-to-evict') == "false":
        return False, 'The deployment has the label cluster-autoscaler.kubernetes.io/safe-to-evict set to "false"'
    return True, ""

def has_terminationGracePeriodSeconds(deployment):
    # Check if the deployment has terminationGracePeriod greater than 600 seconds.
    if (deployment.spec.template.spec.termination_grace_period_seconds > 600):
        return False, "The deployment has terminationGracePeriod greater than 10 minutes"
    return True, ""

def uses_no_ephemeral_storage(deployment):
    # Check if the deployment's pods request ephemeral storage.
    containers = deployment.spec.template.spec.containers

    for container in containers:
        requests = container.resources.requests
        if requests and 'ephemeral-storage' in requests:
            return False, "The deployment's pods request ephemeral storage"
    return True, ""

def is_suitable_for_spot_instances(deployment, v1):
    checks = [(is_stateless, []), (has_replica_set, []), (is_safe_to_evict, []), (has_terminationGracePeriodSeconds, []), (uses_no_ephemeral_storage, []), (gets_ready_quickly, [v1])]

    for check, args in checks:
        result, message = check(deployment, *args)
        if not result:
            return False, message
    return True, ""

def get_cpu_requests(deployment):
    # Get the total CPU requests of the deployment, factoring in the number of replicas.
    cpu_requests = 0
    containers = deployment.spec.template.spec.containers
    for container in containers:
        requests = container.resources.requests
        if requests and 'cpu' in requests:
            cpu_requests += utils.parse_quantity(requests['cpu'])
    return cpu_requests * (deployment.spec.replicas if deployment.spec.replicas else 1)

def get_mem_requests(deployment):
    # Get the total CPU requests of the deployment, factoring in the number of replicas.
    memory_requests = 0
    containers = deployment.spec.template.spec.containers
    for container in containers:
        requests = container.resources.requests
        if requests and 'memory' in requests:
            memory_requests += utils.parse_quantity(requests['memory'])
    return memory_requests * (deployment.spec.replicas if deployment.spec.replicas else 1)

def main():
    # Load the kube config from the default location.
    config.load_kube_config()

    # Load the kube config from the default location.
    current_context = config.load_kube_config()

    # Get the current context.
    _, current_context = config.list_kube_config_contexts()

    # Get the cluster name from the current context.
    cluster_name = current_context['context']['cluster']

    # Print the cluster name.
    # Prepare the output string.
    output = f"Scanning cluster: {cluster_name}"

    # Print the cluster name with additional formatting.
    print("#" * len(output))
    print(output)
    print("#" * len(output))

    # Create a client for the CoreV1 API.
    v1 = client.CoreV1Api()

    # Create a client for the AppsV1 API.
    v1_apps = client.AppsV1Api()

    # List all deployments in all namespaces.
    deployments = v1_apps.list_deployment_for_all_namespaces().items
    #print(deployments)

    p1 = client.PolicyV1Api()
    #PodDisruptionBudgetStatus
    pdbs = p1.list_pod_disruption_budget_for_all_namespaces().items
    #print(pdbs)

    # Dictionaries to keep track of suitable and unsuitable deployments
    suitable_deployments = []
    unsuitable_deployments = {}

    # Variable to keep track of the total CPU requests of suitable deployments
    total_cpu_requests = 0
    # Variable to keep track of the total Memory requests of suitable deployments
    total_mem_requests = 0

    excludeNamespaces = []
    excludeNamespaces = input("Enter namespaces to exclude: ").split()
    print(f"\nNamespaces Excluded 'kube-system',: {excludeNamespaces}\n")

    print(f"\nStarting to scan Deployments across all namespaces except 'kube-system' and '{excludeNamespaces}' ...\n")

    for deployment in deployments:
        if (deployment.metadata.namespace == "kube-system"):
            continue
        if (deployment.metadata.namespace in excludeNamespaces):
            continue
        suitable, message = is_suitable_for_spot_instances(deployment, v1)
        if suitable:
            suitable_deployments.append((deployment.metadata.namespace, deployment.metadata.name))
            total_cpu_requests += get_cpu_requests(deployment)
            total_mem_requests += get_mem_requests(deployment)
        else:
            if message not in unsuitable_deployments:
                unsuitable_deployments[message] = []
            unsuitable_deployments[message].append((deployment.metadata.namespace, deployment.metadata.name))

    # Print the results
    print("#########################################################################")
    print("Results:")
    print("#########################################################################")
    print(f"\nTotal number of deployments that may be suitable for spot instances: {len(suitable_deployments)}")
    print(f"{'Namespace Name':30} | Deployment Name\n")
    for namespace, name in suitable_deployments:
        print(f"{namespace:30} | {name}")

    if total_cpu_requests > 0:
        print(f"\nTotal vCPU of workloads that may be suitable for spot instances: {total_cpu_requests} vCPU\n")

    if total_mem_requests > 0:
        total_mem_requests_mib=total_mem_requests/(1024*1024)
        print(f"\nTotal Memory of workloads that may be suitable for spot instances: {total_mem_requests_mib} MiB\n")

    print("#########################################################################")
    print("#########################################################################")

    print(f"\nTotal number of deployments that may be unsuitable for spot instances: {sum(len(v) for v in unsuitable_deployments.values())}")
    for reason, deployments in unsuitable_deployments.items():
        print(f"\n* {reason}:")
        for namespace, name in deployments:
            print(f"{namespace:30} | {name}")

if __name__ == "__main__":
    main()
