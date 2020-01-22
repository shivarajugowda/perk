# Perk
Reference implementation of a scalable, reactive SQL Query engine using : **P**r**e**sto, **R**edis, **K**ubernetes

## Description
With the explosion of data, many companies have a need for scalabe SQL analytical query engine. 
For analytical pipelines Presto serves the need well. However, it gets tedious to run and maintain 
that service on more than one cluster. This project is an attempt to provide such a service which 
is scalable, reactive and easier to maintain. Reactive in this context is intended to mean a Reactive System, which is described as
reslient, responsive, elastic and message-driven.


## Setup

### Setup Kubernetes Cluster (GKE)

	gcloud container --project "$(PROJECT_ID)" clusters create "$(CLUSTER_NAME)" --zone "$(ZONE)" --machine-type "n1-standard-2" --num-nodes "1" --min-nodes "1" --max-nodes "4" --preemptible  --image-type "COS" --enable-autoscaling --disk-size "50" --scopes "https://www.googleapis.com/auth/compute","https://www.googleapis.com/auth/devstorage.read_only","https://www.googleapis.com/auth/logging.write","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/servicecontrol","https://www.googleapis.com/auth/service.management.readonly","https://www.googleapis.com/auth/trace.append" --network "default" --cluster-version=1.15 --addons HorizontalPodAutoscaling,HttpLoadBalancing --no-enable-autoupgrade --enable-autorepair
	kubectl create clusterrolebinding cluster-admin-binding --clusterrole=cluster-admin --user=$(GCLOUD_USER)

### Setup Kubernetes Cluster.

####Redis :

    helm install redis --set cluster.enabled=false,usePassword=false stable/redis

####Service account :
The service account is needed by the worker to install Presto in the K8S cluster by itself when it is auto-scaled.
The worker does an "helm install" as one of its initializaiton step. For this reason it needs to be run with a service 
account which has previleges to install a deployment and a service. The cluster role "edit" give it that privilege. Here's
the description of the "edit" privileges from the Kubernetes documentation : "Allows read/write access to most objects 
in a namespace. It does not allow viewing or modifying roles or rolebindings."

	kubectl create serviceaccount prestosvcact --namespace default
	kubectl create clusterrolebinding presto-admin-binding --clusterrole=edit --serviceaccount=default:prestosvcact


### Helm install

    helm install myperk ./charts/perk --wait