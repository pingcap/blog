---
title: 'TiDB Operator Source Code Reading (II): Operator Pattern'
author: ['Yiwen Chen']
date: 2021-05-27
summary: Learn about Kubernetes's Operator pattern and TiDB Operator's major reconcile loop.
tags: ['TiDB Operator', 'Kubernetes']
categories: ['Engineering']
image: /images/blog/tidb-operator-source-code-reading-2-operator-pattern.png
---

**Author:** [Yiwen Chen](https://github.com/handlerww) (Committer of TiDB Operator)

**Transcreator:** [Ran Huang](https://github.com/ran-huang); **Editor:** Tom Dewan

![TiDB Operator Source Code Reading (II): Operator Pattern](media/tidb-operator-source-code-reading-2-operator-pattern.png)

In [my last article](https://pingcap.com/blog/tidb-operator-source-code-reading-1-overview), I introduced TiDB Operator's architecture and what it is capable of. But how does TiDB Operator code run? How does TiDB Operator manage the lifecycle of each component in the TiDB cluster?

In this post, I'll present Kubernetes's Operator pattern and how it is implemented in TiDB Operator. More specifically, **we'll go through TiDB Operator's major control loop, from its entry point to the trigger of the lifecycle management**.

## From Controller to Operator

Because TiDB Operator learns from the [kube-controller-manager](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/), understanding the design of `kube-controller-manager` helps you better understand the internal logic of TiDB Operator.

In Kubernetes, various [controllers](https://kubernetes.io/docs/concepts/architecture/controller/) manage the lifecycle of resources, such as Namespace, Node, Deployment, and StatefulSet. Controllers watch the current state of the cluster resources, compare it with the desired state, and move the cluster towards the desired state. Kubernetes's built-in controllers run inside `kube-controller-manager` and are managed by it.

To allow users to customize resource management, Kubernetes put forward the [Operator pattern](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/). Users can create their own [custom resources](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) (CRs) by defining a [CustomResourceDefinitions](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/#customresourcedefinitions) (CRDs) object and use custom controllers to watch the state of the corresponding CRs and complete relevant management tasks. The Operator pattern allows users to extend Kubernetes behaviors without modifying its code.

## How TiDB controller manager works

As illustrated in [TiDB Operator Source Code Reading (I): Overview](https://pingcap.com/blog/tidb-operator-source-code-reading-1-overview#how-tidb-operator-works), TiDB Operator has a core component, `tidb-controller-manager`, which runs a set of custom controllers that manages CRDs for TiDB.

### Entry point

Starting from `cmd/controller-manager/main.go`, `tidb-controller-manager` first loads kubeconfig to access the kube-apiserver. It then uses a series of `NewController` functions to load the init function of each controller.

```go
controllers := []Controller{
    tidbcluster.NewController(deps),
    dmcluster.NewController(deps),
    backup.NewController(deps),
    restore.NewController(deps),
    backupschedule.NewController(deps),
    tidbinitializer.NewController(deps),
    tidbmonitor.NewController(deps),
}
```

During the execution of init functions, `tidb-controller-manager` initializes a set of informers, which interact with the kube-apiserver to obtain the changes of CRs and related resources. Taking `TidbCluster` as an example, in the `NewController` function, `tidb-controller-manager` initializes the Informer objects:

```go
tidbClusterInformer.Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
        AddFunc: c.enqueueTidbCluster,
        UpdateFunc: func(old, cur interface{}) {
            c.enqueueTidbCluster(cur)
        },
        DeleteFunc: c.enqueueTidbCluster,
    })
statefulsetInformer.Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
        AddFunc: c.addStatefulSet,
        UpdateFunc: func(old, cur interface{}) {
            c.updateStatefulSet(old, cur)
        },
        DeleteFunc: c.deleteStatefulSet,
    })
```

EventHandlers that process `add`, `update`, and `delete` events are registered to the Informers. These EventHandlers handle the events and add the relevant CR keys to the queue.

### Controller's internal logic

After the initialization, `tidb-controller-manager` launches InformerFactory and waits for cache synchronization to complete:

```go
informerFactories := []InformerFactory{
            deps.InformerFactory,
            deps.KubeInformerFactory,
            deps.LabelFilterKubeInformerFactory,
        }
        for _, f := range informerFactories {
            f.Start(ctx.Done())
            for v, synced := range f.WaitForCacheSync(wait.NeverStop) {
                if !synced {
                    klog.Fatalf("error syncing informer for %v", v)
                }
            }
        }
```

Next, `tidb-controller-manager` calls the Run function of each controller and executes the internal logic of controllers in a loop:

```go
// Start syncLoop for all controllers.
for _,controller := range controllers {
    c := controller
    go wait.Forever(func() { c.Run(cliCfg.Workers,ctx.Done()) },cliCfg.WaitDuration)
}
```

Again, take the `TidbCluster` controller as an example. The Run function starts the worker queue:

```go
// Run runs the tidbcluster controller.
func (c *Controller) Run(workers int, stopCh <-chan struct{}) {
    defer utilruntime.HandleCrash()
    defer c.queue.ShutDown()

    klog.Info("Starting tidbcluster controller")
    defer klog.Info("Shutting down tidbcluster controller")

    for i := 0; i < workers; i++ {
        go wait.Until(c.worker, time.Second, stopCh)
    }

    <-stopCh
}
```

The worker calls the `processNextWorkItem` function, dequeues the items, and calls the `sync` function to synchronize the CR:

```go
// worker runs a worker goroutine that invokes processNextWorkItem until the controller's queue is closed.
func (c *Controller) worker() {
    for c.processNextWorkItem() {
    }
}

// processNextWorkItem dequeues items, processes them, and marks them done. It enforces that the syncHandler is never
// invoked concurrently with the same key.
func (c *Controller) processNextWorkItem() bool {
    key, quit := c.queue.Get()
    if quit {
        return false
    }
    defer c.queue.Done(key)
    if err := c.sync(key.(string)); err != nil {
        if perrors.Find(err, controller.IsRequeueError) != nil {
            klog.Infof("TidbCluster: %v, still need sync: %v, requeuing", key.(string), err)
        } else {
            utilruntime.HandleError(fmt.Errorf("TidbCluster: %v, sync failed %v, requeuing", key.(string), err))
        }
        c.queue.AddRateLimited(key)
    } else {
        c.queue.Forget(key)
    }
    return true
}
```

Based on the key, the `sync` function obtains the corresponding CR object (for example, the `TidbCluster` object) and syncs it:

```go
// sync syncs the given tidbcluster.
func (c *Controller) sync(key string) error {
    startTime := time.Now()
    defer func() {
        klog.V(4).Infof("Finished syncing TidbCluster %q (%v)", key, time.Since(startTime))
    }()

    ns, name, err := cache.SplitMetaNamespaceKey(key)
    if err != nil {
        return err
    }
    tc, err := c.deps.TiDBClusterLister.TidbClusters(ns).Get(name)
    if errors.IsNotFound(err) {
        klog.Infof("TidbCluster has been deleted %v", key)
        return nil
    }
    if err != nil {
        return err
    }

    return c.syncTidbCluster(tc.DeepCopy())
}

func (c *Controller) syncTidbCluster(tc *v1alpha1.TidbCluster) error {
    return c.control.UpdateTidbCluster(tc)
}
```

The `syncTidbCluster` function calls the `updateTidbCluster` function, which further invokes a series of component `sync` functions, to complete the management of the whole TiDB cluster.

In `pkg/controller/tidbcluster/tidb_cluster_control.go`, you can check the implementation of the `updateTidbCluster` function, where there are comments that describe the lifecycle management performed by each `sync` function. Through these comments, you can understand what operations are required for reconciling each component. For example, in Placement Driver (PD):

```go
// To make the current state of the pd cluster match the desired state:
//   - create or update the pd service
//   - create or update the pd headless service
//   - create the pd statefulset if it does not exist
//   - sync pd cluster status from pd to TidbCluster object
//   - upgrade the pd cluster
//   - scale out/in the pd cluster
//   - failover the pd cluster
if err := c.pdMemberManager.Sync(tc); err != nil {
    return err
}
```

That's all for now.

## Summary

In this article, **we covered TiDB Operator from its entry point in `cmd/controller-manager/main.go` to the implementation of controllers and explained the controllers' internal logic**. Now, you are familiar with how the control loop is triggered. The only question left is how to refine the control loop and instill in it the special operation logic of TiDB. That way, you can deploy TiDB and run it in Kubernetes as desired.

For those who would like to develop a resource management system, we recommend two scaffolding projects: [Kubebuilder](https://github.com/kubernetes-sigs/kubebuilder) and [Operator Framework](https://github.com/operator-framework/operator-sdk). These projects generate the code template based on [controller-runtime](https://github.com/kubernetes-sigs/controller-runtime), allowing you to focus on the reconcile loop of your CRD objects.

In the next article, I'll discuss [how to refine the control loop and implement the component reconcile loop](https://pingcap.com/blog/tidb-operator-source-code-reading-3-component-control-loop). If you have any questions, talk to us via [our Slack channel](https://slack.tidb.io/invite?team=tidb-community&channel=sig-k8s&ref=pingcap-blog) or at [pingcap/tidb-operator](https://github.com/pingcap/tidb-operator).
