# is-spot-workloads
Python script that scans your current Kubernetes cluster and indicates which workloads may be suitable to run on spot nodes.

**What do we check?**
1. All deployments that are NOT in the kube-system namespace. You can also add any additional namespaces you want to exclude.
2. For each deployment we check, we consider it suitable to run on Spot if:
   a. The deployment has more than one replica.
   b. If the deployment doesn't have any karpenter.sh/do-not-disrupt annotation set to true
   b. If the deployment doesn't have any cluster-autoscaler.kubernetes.io/safe-to-evict annotation set to false.
   c. If the deployment doesn't have any spotinst.io/restrict-scale-down label set to true.
   d. The deployment's pods don’t request ephemeral storage.
   e. If the deployment has termination_grace_period_seconds less than 600 seconds
4. PDBs that are too restrictive with no disruptions allowed, hence may not be suitable to run on Spot.   
5. Currently, we scan only deployments - and NOT: jobs, stateful sets, etc.

Prerequisites 
1. Python 3.x should be installed.
2. The module kubernetes should be installed as well. In case it’s not installed please run:
     **pip3 install kubernetes**
3. The script scans the cluster that your context points to.

**Script Output:**
The script output consists of:
1. The cluster name being scanned.
2. Namespaces excluded by the script.
3. All the Deployments Name & Namespaces that may be suitable for Spot instances.
4. All the Deployments Name & Namespaces that may be unsuitable for Spot instances.
5. Total vCPU & Total Memory of pods that are suitable to run on Spot.
6. The reason why the deployments were marked as unsuitable for spot instances.
7. All the PDBs Name, Namespace, Spec & Current Status that may not be suitable for spot instances.

Sample Output:
```
$ python3 spotableworkloads.py

#####################################################################
Scanning cluster: arn:aws:eks:us-west-2:xx6285426xx:cluster/test-cluster
#####################################################################
Enter namespaces to exclude: spot-system

Namespaces Excluded: 'kube-system', ['spot-system']


Starting to scan Deployments and PDBs across all namespaces except 'kube-system' and '['spot-system']' ...

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

* The deployment has the annotation karpenter.sh/do-not-evict set to "true":
default                        | applog

* The deployment has the label cluster-autoscaler.kubernetes.io/safe-to-evict set to "false":
default                        | backend-app

* The deployment has terminationGracePeriod greater than 10 minutes:
default                        | web-api
testing                        | perfapp

* The deployment does not have more than one replica:
default                        | kube-prometheus-stack-grafana
default                        | kube-prometheus-stack-kube-state-metrics
default                        | kube-prometheus-stack-operator
default                        | php-apache-app

#########################################################################
#########################################################################

The PDB fk-pdb in namespace testing has no disruptions allowed
PDB Spec:
 {'max_unavailable': None,
 'min_available': 2,
 'selector': {'match_expressions': None, 'match_labels': {'app': 'frontend'}},
 'unhealthy_pod_eviction_policy': None}
PDB Current Status:
 {'conditions': [{'last_transition_time': datetime.datetime(2024, 11, 22, 8, 44, 24, tzinfo=tzutc()),
                 'message': '',
                 'observed_generation': 1,
                 'reason': 'InsufficientPods',
                 'status': 'False',
                 'type': 'DisruptionAllowed'}],
 'current_healthy': 0,
 'desired_healthy': 2,
 'disrupted_pods': None,
 'disruptions_allowed': 0,
 'expected_pods': 2,
 'observed_generation': 1}
```
