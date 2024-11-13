# is-spot-workloads
Python script that scans your current Kubernetes cluster and indicates which workloads may be suitable to run on spot nodes.

**What do we check?**
1. All deployments that are NOT in the kube-system namespace. You can also add namespaces you want to avoid the script checking on.
2. For each deployment we check, we consider it suitable to run on Spot if:
   a. The restart_policy is Always.
   b. The deployment has more than one replica.
   c. If pods take more than 10 minutes to get into Ready state.
   d. If the deployment doesn't have any cluster-autoscaler.kubernetes.io/safe-to-evict label set to false.
   e. The deployment's pods don’t request ephemeral storage.
   f. If the deployment has termination_grace_period_seconds less than 600 seconds
3. Currently, we scan only deployments - and NOT: jobs, stateful sets, etc.

Prerequisites 
1. Python 3.x should be installed.
2. The module kubernetes should be installed as well. In case it’s not installed please run:
     **pip3 install kubernetes**
3. The script scans the cluster that your context points to.

**Script Output:**
The script output consists of:
1. The cluster name being scanned.
2. Namespaces excluded by the script.
3. All the Deployments Name & Namespaces that may be suitable for spot instances.
4. All the Deployments Name & Namespaces that may not be suitable for spot instances.
5. Total vCPU & Total Memory of pods that are suitable to run on Spot.
6. The reason why the deployments were marked as unsuitable for spot instances.

Sample Output:
```
$ python3 spotableworkloads.py

#####################################################################
Scanning cluster: arn:aws:eks:us-west-2:xx6285426xx:cluster/test-cluster
#####################################################################
Enter namespaces to exclude: spot-system

Namespaces Excluded: 'kube-system', ['spot-system']


Starting to scan Deployments across all namespaces except 'kube-system' and '['spot-system']' ...

#########################################################################
Results:
#########################################################################

Total number of deployments that may be suitable for spot instances: 3
Namespace Name                 | Deployment Name

default                        | nginx-deploy
default                        | slow-starting-deployment
olm                            | packageserver

Total vCPU of workloads that may be suitable for spot instances: 12.020 vCPU

Total Memory of workloads that may be suitable for spot instances: 6200 MiB

#########################################################################
#########################################################################

Total number of deployments that may be unsuitable for spot instances: 9

* The deployment's pods take longer than 10 minutes to become ready:
default                        | applog
default                        | backend-app
default                        | frontend-app
default                        | web-api
testing                        | perfapp

* The deployment does not have more than one replica:
default                        | kube-prometheus-stack-grafana
default                        | kube-prometheus-stack-kube-state-metrics
default                        | kube-prometheus-stack-operator
default                        | php-apache-app
```
