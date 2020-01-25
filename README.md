# Perk
Reference implementation of a scalable, reactive SQL Query engine using : **P**r**e**sto, **R**edis, **K**ubernetes

## Description
With the explosion of data, many companies have a need for scalabe SQL analytical query engine. 
For analytical pipelines Presto serves the need well. However, it gets tedious to run and maintain 
that service on more than one cluster. This project is an attempt to provide a queue based Presto service which 
is scalable, reactive and easier to maintain. Reactive in this context is intended to mean a [Reactive System](https://www.reactivemanifesto.org/), which is described as
reslient, responsive, elastic and message-driven. This framework is queue based and manages multiple Presto cluster with Autoscaling 
of clusters(and not Presto workers). Autoscaling Presto Clusters instead of the Presto workers in a cluster has several benefits.
It provides isolation for the queries and it removes conductor as single point of failure. It also allows to restart the cluster
without impacting the 


The implementation consists of three components: gateway, queue and worker written in Python. 
Gateway implements the [Presto Rest HTTP Protocol](https://github.com/prestodb/presto/wiki/HTTP-Protocol). Right now the normal JDBC
statements and PreparedStatements are tested. Transactions might not work since the queries in a single transaction may be executed 
on different clusters. The Queue is implemented using [Redis Streams](https://redis.io/topics/streams-intro). The worker launches 
it's own Presto cluster and executes the queries from the queue. The number of threads in the worker can be controlled. In the future,
 we could add a back-pressure based on it's Presto Cluster's load metric. The results 
are stored in Redis. The Gateway and the Workers scale independently based on cpu load. The life 
cycle of the Presto Cluster is controlled by the Worker process. When the worker process is scaled down it automatically uninstalls
the associated Presto Cluster. The Presto Clusters also have the ["Owner Reference"](https://kubernetes.io/docs/concepts/workloads/controllers/garbage-collection/#owners-and-dependents)
 set to the worker pod so that the Presto Cluster is garbage collected even when it worker pod exits abruptly.

All the custom configurations of the Presto Clusters could be encapsulated in a Docker image and this 
framework could be used to manage those dynamic clusters in Kubernetes. 


## Setup

### Setup Kubernetes Cluster.

#### Install Redis :

    helm install redis --set cluster.enabled=false,usePassword=false stable/redis

#### Service account :
The service account is needed by the worker to install Presto in the K8S cluster by itself when it is auto-scaled.
The worker does an "helm install" as one of its initialization step. For this reason it needs to be run with a service 
account which has privileges to install a kubernetes deployment and service. The cluster role "edit" give it that privilege. Here's
the description of the "edit" privileges from the [Kubernetes documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#user-facing-roles) : "Allows read/write access to most objects 
in a namespace. It does not allow viewing or modifying roles or rolebindings."

	kubectl create serviceaccount prestosvcact --namespace default
	kubectl create clusterrolebinding presto-admin-binding --clusterrole=edit --serviceaccount=default:prestosvcact


### Helm install Perk

    cd src
    helm install myperk ./charts/perk --wait