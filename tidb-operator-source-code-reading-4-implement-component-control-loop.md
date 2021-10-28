---
title: 'TiDB Operator Source Code Reading (IV): Implementing a Component Control Loop'
author: ['Yiwen Chen']
date: 2021-10-28
summary: This post explains how TiDB Operator implements a component control loop by taking PD as an example. You'll learn PD and other component's lifecycle management.
tags: ['TiDB Operator', 'Kubernetes']
categories: ['Engineering']
image: /images/blog/tidb-operator-source-code-reading-4.jpg
---

**Author:** [Yiwen Chen](https://github.com/handlerww) (Committer of TiDB Operator, Software Engineer at PingCAP)

**Transcreator:** Ran Huang; **Editor:** Tom Dewan

![TiDB Operator Source Code Reading (IV): Implementing a Component Control Loop](media/tidb-operator-source-code-reading-4.jpg)

> _Previous articles in this series:_
>
> * _[TiDB Operator Source Code Reading (I): Overview](https://pingcap.com/blog/tidb-operator-source-code-reading-1-overview)_
> * _[TiDB Operator Source Code Reading (II): Operator Pattern](https://pingcap.com/blog/tidb-operator-source-code-reading-2-operator-pattern)_
> * _[TiDB Operator Source Code Reading (III): The Component Control Loop](https://pingcap.com/blog/tidb-operator-source-code-reading-3-component-control-loop)_

In our [last article](https://pingcap.com/blog/tidb-operator-source-code-reading-3-component-control-loop), we introduced how TiDB Operator orchestrates control loop events to manage the lifecycles of TiDB components. The `TidbCluster` controller manages TiDB components' lifecycles, and the member manager of each TiDB component encapsulates that component's specific management logic.

In this post, I'll explain in detail **how we implement a component control loop by taking PD as an example**. You'll learn about the PD member manager and its lifecycle management operations. I'll also compare other components with PD and show their differences.

## The PD control loop

[Placement Driver](https://docs.pingcap.com/tidb/stable/tidb-scheduling) (PD) manages a TiDB cluster and schedules Regions in the cluster. The PD member manager maintains the PD lifecycle management logic. Most of its code resides in ``pkg/manager/member/pd_member_manager.go``, and other code related to scaling, upgrade, and failover is located in `pd_scaler.go`, `pd_upgrader.go`, and `pd_failover.go` respectively.

As is illustrated in [Part III](https://pingcap.com/blog/tidb-operator-source-code-reading-3-component-control-loop#call-the-component-control-loop), it takes the following tasks to manage a component's lifecycle:

* Sync Service
* Start syncing StatefulSet
* Sync status
* Sync ConfigMap
* Rolling update
* Scaling in and scaling out
* Failover
* Finish syncing StatefulSet

Syncing StatefulSet is the major logic. Other tasks, like syncing status and syncing ConfigMap, are defined as sub-functions and called by the PD member manager when it syncs StatefulSet.

### Sync StatefulSet

To sync StatefulSet, the PD member manager:

1. Obtains the current PD StatefulSet using `StatefulSetLister`.

    ```go
    oldPDSetTmp, err := m.deps.StatefulSetLister.StatefulSets(ns).Get(controller.PDMemberName(tcName))
    if err != nil && !errors.IsNotFound(err) {
        return fmt.Errorf("syncPDStatefulSetForTidbCluster: fail to get sts %s for cluster %s/%s, error: %s", controller.PDMemberName(tcName), ns, tcName, err)
    }
    setNotExist := errors.IsNotFound(err)

    oldPDSet := oldPDSetTmp.DeepCopy()
    ```

2. Gets the latest status using ``m.syncTidbClusterStatus(tc, oldPDSet)``.

    ```go
    if err := m.syncTidbClusterStatus(tc, oldPDSet); err != nil {
        klog.Errorf("failed to sync TidbCluster: [%s/%s]'s status, error: %v", ns, tcName, err)
    }
    ```

3. Checks whether the TiDB cluster pauses the synchronization. If so, terminate the following reconciliation.

    ```go
    if tc.Spec.Paused {
        klog.V(4).Infof("tidb cluster %s/%s is paused, skip syncing for pd statefulset", tc.GetNamespace(), tc.GetName())
        return nil
    }
    ```

4. Syncs ConfigMap according to the latest `tc.Spec`.

    ```go
    cm, err := m.syncPDConfigMap(tc, oldPDSet)
    ```

5. Generates the latest StatefulSet template according to the latest `tc.Spec`, `tc.Status`, and ConfigMap obtained in the last step.

    ```go
    newPDSet, err := getNewPDSetForTidbCluster(tc, cm)
    ```

6. If the new PD StatefulSet hasn't been created yet, first create the StatefulSet.

    ```go
    if setNotExist {
        if err := SetStatefulSetLastAppliedConfigAnnotation(newPDSet); err != nil {
            return err
        }
        if err := m.deps.StatefulSetControl.CreateStatefulSet(tc, newPDSet); err != nil {
            return err
        }
        tc.Status.PD.StatefulSet = &apps.StatefulSetStatus{}
        return controller.RequeueErrorf("TidbCluster: [%s/%s], waiting for PD cluster running", ns, tcName)
    }
    ```

7. If a user configures a forced upgrade using [annotations](https://kubernetes.io/docs/concepts/overview/working-with-objects/annotations/), this step configures the StatefulSet to perform a rolling upgrade directly. This is to avoid an upgrade failure if the reconciliation loop is blocked.

    ```go
    if !tc.Status.PD.Synced && NeedForceUpgrade(tc.Annotations) {
        tc.Status.PD.Phase = v1alpha1.UpgradePhase
        setUpgradePartition(newPDSet, 0)
        errSTS := UpdateStatefulSet(m.deps.StatefulSetControl, tc, newPDSet, oldPDSet)
        return controller.RequeueErrorf("tidbcluster: [%s/%s]'s pd needs force upgrade, %v", ns, tcName, errSTS)
    }
    ```

8. Calls the scaling logic implemented in `pd_scaler.go`.

    ```go
    if err := m.scaler.Scale(tc, oldPDSet, newPDSet); err != nil {
        return err
    }
    ```

9. Calls the failover logic implemented in `pd_failover.go`. The function first checks if the cluster needs to recover, then checks if all Pods are started and all members are healthy, and finally determines whether it needs to begin failover.

    ```go
    if m.deps.CLIConfig.AutoFailover {
        if m.shouldRecover(tc) {
            m.failover.Recover(tc)
        } else if tc.PDAllPodsStarted() && !tc.PDAllMembersReady() || tc.PDAutoFailovering() {
            if err := m.failover.Failover(tc); err != nil {
                return err
            }
        }
    }
    ```

10. Calls the upgrade logic implemented in `pd_upgrader.go`. When the newly generated PD StatefulSet is inconsistent with the existing one or when the two StatefulSets are consistent but `tc.Status.PD.Phase` is `upgrade`, the PD Member Manager enters `upgrader` to process the rolling upgrade logic.

    ```go
    if !templateEqual(newPDSet, oldPDSet) || tc.Status.PD.Phase == v1alpha1.UpgradePhase {
        if err := m.upgrader.Upgrade(tc, oldPDSet, newPDSet); err != nil {
            return err
        }
    }
    ```

11. The PD StatefulSet is synced, and the new StatefulSet is updated to the Kubernetes cluster.

### Sync Service

PD uses ​​both [Services](https://kubernetes.io/docs/concepts/services-networking/service/) and [headless Services](https://kubernetes.io/docs/concepts/services-networking/service/#headless-services), managed by `syncPDServiceForTidbCluster` and `syncPDHeadlessServiceForTidbCluster`.

The Service address is used in TiDB, TiKV, and TiFlash to configure the PD endpoint. For example, TiDB uses `--path=${CLUSTER_NAME}-pd:2379` as its PD service address in the startup parameter:

```
ARGS="--store=tikv \
--advertise-address=${POD_NAME}.${HEADLESS_SERVICE_NAME}.${NAMESPACE}.svc \
--path=${CLUSTER_NAME}-pd:2379 \
```

The headless Service provides a unique identifier for each Pod. When PD starts up, the PD Pod registers its endpoint in PD members as `"${POD_NAME}.${PEER_SERVICE_NAME}.${NAMESPACE}.svc"`:

```
domain="${POD_NAME}.${PEER_SERVICE_NAME}.${NAMESPACE}.svc"
ARGS="--data-dir=/var/lib/pd \
--name=${POD_NAME} \
--peer-urls=http://0.0.0.0:2380 \
--advertise-peer-urls=http://${domain}:2380 \
--client-urls=http://0.0.0.0:2379 \
--advertise-client-urls=http://${domain}:2379 \
--config=/etc/pd/pd.toml \
"
```

### Sync ConfigMap

PD uses ConfigMap to manage the configurations and the start script. The `syncPDConfigMap` function calls `getPDConfigMap` to get the latest ConfigMap and apply it to the Kubernetes cluster. ConfigMap handles the following tasks:

1. Get `PD.Config` for the follow-up sync. To remain compatible with earlier versions that use Helm, when the config object is empty, ConfigMap is not synced.

    ```go
    config := tc.Spec.PD.Config
    if config == nil {
        return nil, nil
    }
    ```

2. Modify TLS-related configuration. Because TiDB 4.0 and earlier versions don't support TiDB Dashboard, PD member manager skips configuring Dashboard certificates for PD in earlier versions.

    ```go
    // override CA if tls enabled
    if tc.IsTLSClusterEnabled() {
        config.Set("security.cacert-path", path.Join(pdClusterCertPath, tlsSecretRootCAKey))
        config.Set("security.cert-path", path.Join(pdClusterCertPath, corev1.TLSCertKey))
        config.Set("security.key-path", path.Join(pdClusterCertPath, corev1.TLSPrivateKeyKey))
    }
    // Versions below v4.0 do not support Dashboard
    if tc.Spec.TiDB != nil && tc.Spec.TiDB.IsTLSClientEnabled() && !tc.SkipTLSWhenConnectTiDB() && clusterVersionGE4 {
        config.Set("dashboard.tidb-cacert-path", path.Join(tidbClientCertPath, tlsSecretRootCAKey))
        config.Set("dashboard.tidb-cert-path", path.Join(tidbClientCertPath, corev1.TLSCertKey))
        config.Set("dashboard.tidb-key-path", path.Join(tidbClientCertPath, corev1.TLSPrivateKeyKey))
    }
    ```

3. Transform the configuration to TOML format so that PD can read it.

    ```go
    confText, err := config.MarshalTOML()
    ```

4. Generate the PD start script using `RenderPDStartScript`. The script template is stored in the `pdStartScriptTpl` variable in `pkg/manager/member/template.go`. The PD start script is a Bash script. `RenderPDStartScript` inserts some variables and annotations configured by the `TidbCluster` object into the start script. These variables and annotations are used for PD startup and debugging.

5. Assemble the PD configurations and the start script as the Kubernetes ConfigMap object, and return the ConfigMap to the `syncPDConfigMap` function.

    ```go
    cm := &corev1.ConfigMap{
        ObjectMeta: metav1.ObjectMeta{
            Name:            controller.PDMemberName(tc.Name),
            Namespace:       tc.Namespace,
            Labels:          pdLabel,
            OwnerReferences: []metav1.OwnerReference{controller.GetOwnerRef(tc)},
        },
        Data: map[string]string{
            "config-file":    string(confText),
            "startup-script": startScript,
        },
    }
    ```

### Scaling

The scaling logic is implemented `in pkg/manager/member/pd_scaler.go`. The StatefulSet calls the `Scale` function to scale out or scale in the PD cluster.

Before scaling, TiDB Operator needs to perform some preliminary operations. For example, to scale in the PD cluster, TiDB Operator needs to transfer Leaders, take members offline, and add annotations to [PersistentVolumeClaims](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#introduction) (PVCs) for deferred deletion. To scale out the cluster, TiDB Operator needs to delete the previously retained PVCs.

After the preliminary operations are completed, TiDB Operator adjusts the number of StatefulSet replicas and begins the scaling process. The preliminary operations minimize the impact of the scaling operation.

The `Scale` function acts like a router. Based on the scaling direction, step, and length, it determines which scaling plan to use. If the `scaling` variable is a positive number, PD is scaled out; otherwise, PD is scaled in. In each scaling operation, PD is only scaled by one step. The specific plan is implemented by the `ScaleIn` and `ScaleOut` functions.

```go
func (s *pdScaler) Scale(meta metav1.Object, oldSet *apps.StatefulSet, newSet *apps.StatefulSet) error {
    scaling, _, _, _ := scaleOne(oldSet, newSet)
    if scaling > 0 {
        return s.ScaleOut(meta, oldSet, newSet)
    } else if scaling &lt; 0 {
        return s.ScaleIn(meta, oldSet, newSet)
    }
    return s.SyncAutoScalerAnn(meta, oldSet)
}
```

#### Scaling in

Before TiDB Operator takes a PD member offline, it must **transfer the Leader**. Otherwise, when the Leader member is taken offline, the rest of the PD members are forced into a Leader election, which affects cluster performance. Therefore, TiDB Operator needs to transfer the Leader to the PD member with the smallest ID. This makes sure that the PD Leader is only transferred once.

To transfer the PD Leader, first get the PD client and the PD Leader:

```go
pdClient := controller.GetPDClient(s.deps.PDControl, tc)
leader, err := pdClient.GetPDLeader()
```

When the Leader name equals the member name, TiDB Operator transfers the Leader. If there is only one member left, no other member is available for transfer, so TiDB Operator skips transferring the Leader.

After the Leader is transferred, the `ScaleIn` function calls PD's `DeleteMember` API and deletes the member from PD members. The PD member is then taken offline. Finally, the function calls `setReplicasAndDeleteSlots` to adjust the number of StatefulSet replicas, and the scaling-in process is completed.

#### Scaling out

Before TiDB Operator scales out the PD cluster, it needs to delete deferred PVCs by calling `deleteDeferDeletingPVC`. When TiDB Operator previously scaled in PD, these PVCs were retained for deferred deletion to achieve data reliability; now, TiDB Operator must delete them to avoid the cluster using old data. After these PVCs are deleted, TiDB Operator only has to adjust the number of StatefulSet replicas and scale out the PD cluster.

Whether you scale in or scale out the PD cluster, the operation is performed by configuring the number of StatefulSet replicas. Therefore, when TiDB Operator supports the [advanced StatefulSet](https://docs.pingcap.com/tidb-in-kubernetes/stable/advanced-statefulset), it must take into account the empty slots when counting the replicas.

<div class="trackable-btns">
  <a href="/download" onclick="trackViews('TiDB Operator Source Code Reading (IV): Implementing a Component Control Loop', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
  <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('TiDB Operator Source Code Reading (IV): Implementing a Component Control Loop', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

### Rolling upgrade

The upgrade logic is implemented in `pkg/manager/member/pd_upgrader.go`. The `UpdateStrategy` in the StatefulSet performs the rolling upgrade on PD. To mitigate the impact of upgrade on the PD cluster, `pd_upgrader.go` performs some preliminary operations when it updates `UpdateStrategy` in the StatefulSet. For details on how to control `UpdateStrategy`, refer to [our last article](https://pingcap.com/blog/tidb-operator-source-code-reading-3-component-control-loop#rolling-update).

Before upgrade, TiDB Operator completes the following status check:

1. It checks whether there are other ongoing operations. In particular, it checks whether TiCDC and TiFlash is being upgraded and whether PD is being scaled out or scaled in.

    ```go
    if tc.Status.TiCDC.Phase == v1alpha1.UpgradePhase ||
        tc.Status.TiFlash.Phase == v1alpha1.UpgradePhase ||
        tc.PDScaling()
    ```

2. The PD member manager determines to enter `Upgrader` on two circumstances:

    * When the newly generated PD StatefulSet is inconsistent with the existing one, the status check returns `nil`, and TiDB Operator updates the StatefulSet. There is no need to perform the following checks in steps 3 and 4.

        ```go
        if !templateEqual(newSet, oldSet) {
            return nil
        }
        ```

    * When the two StatefulSets are consistent but `tc.Status.PD.Phase` is `upgrade`, `newSet` and `oldSet` have the same template spec, and TiDB Operator continues the following two checks.

    For more information on these two situations, see [Sync StatefulSet](#sync-statefulset), Step 10.

3. It compares `tc.Status.PD.StatefulSet.UpdateRevision` and `tc.Status.PD.StatefulSet.CurrentRevision`. If the two variables are equal, the rolling upgrade operation is already completed. Then, TiDB Operator ends the upgrade process.

    ```go
    if tc.Status.PD.StatefulSet.UpdateRevision == tc.Status.PD.StatefulSet.CurrentRevision
    ```

4. It checks if the `UpdateStrategy` in the StatefulSet is manually modified. If yes, follow the modified strategy.

    ```go
    if oldSet.Spec.UpdateStrategy.Type == apps.OnDeleteStatefulSetStrategyType || oldSet.Spec.UpdateStrategy.RollingUpdate == nil {
        newSet.Spec.UpdateStrategy = oldSet.Spec.UpdateStrategy
        klog.Warningf("tidbcluster: [%s/%s] pd statefulset %s UpdateStrategy has been modified manually", ns, tcName, oldSet.GetName())
        return nil
    }
    ```

After all checks are passed, TiDB Operator begins processing each Pod and rolling upgrades the PD cluster:

1. It checks whether the PD Pod is updated. By comparing the `controller-revision-hash` value in the Pod Label with the `UpdateRevision` value of the StatefulSet, TiDB Operator can tell whether this Pod is updated or still unprocessed. If the Pod is updated, TiDB Operator then checks whether the PD member is healthy. If the PD member is healthy, TiDB Operator moves on to the next Pod. If not, TiDB Operator returns an error and checks the health state in the next sync.

    ```go
    revision, exist := pod.Labels[apps.ControllerRevisionHashLabelKey]
        if !exist {
            return controller.RequeueErrorf("tidbcluster: [%s/%s]'s pd pod: [%s] has no label: %s", ns, tcName, podName, apps.ControllerRevisionHashLabelKey)
        }

        if revision == tc.Status.PD.StatefulSet.UpdateRevision {
            if member, exist := tc.Status.PD.Members[PdName(tc.Name, i, tc.Namespace, tc.Spec.ClusterDomain)]; !exist || !member.Health {
                return controller.RequeueErrorf("tidbcluster: [%s/%s]'s pd upgraded pod: [%s] is not ready", ns, tcName, podName)
            }
            continue
        }
    ```

2. If `Pod revision != tc.Status.PD.StatefulSet.UpdateRevision`, the Pod is not updated yet. TiDB Operator calls the `upgradePDPod` function to process this Pod. When TiDB Operator processes the PD Leader Pod, it transfers the Leader before it continues the upgrade process.

    ```go
    if tc.Status.PD.Leader.Name == upgradePdName || tc.Status.PD.Leader.Name == upgradePodName {
        var targetName string
        targetOrdinal := helper.GetMaxPodOrdinal(*newSet.Spec.Replicas, newSet)
        if ordinal == targetOrdinal {
            targetOrdinal = helper.GetMinPodOrdinal(*newSet.Spec.Replicas, newSet)
        }
        targetName = PdName(tcName, targetOrdinal, tc.Namespace, tc.Spec.ClusterDomain)
        if _, exist := tc.Status.PD.Members[targetName]; !exist {
            targetName = PdPodName(tcName, targetOrdinal)
        }

        if len(targetName) > 0 {
            err := u.transferPDLeaderTo(tc, targetName)
            if err != nil {
                klog.Errorf("pd upgrader: failed to transfer pd leader to: %s, %v", targetName, err)
                return err
            }
            klog.Infof("pd upgrader: transfer pd leader to: %s successfully", targetName)
            return controller.RequeueErrorf("tidbcluster: [%s/%s]'s pd member: [%s] is transferring leader to pd member: [%s]", ns, tcName, upgradePdName, targetName)
        }
    }
    setUpgradePartition(newSet, ordinal)
    ```

### Failover

The PD failover logic is implemented in `pd_failover.go`. PD deletes failed Pods to fix the failure, which is different from other component failover logic.

Before performing failover, TiDB Operator also carries out health checks. If the PD cluster is unavailable, which means half of the PD members are unhealthy, recreating PD members cannot recover the cluster. Under such circumstances, TiDB Operator doesn't perform failover.

1. TiDB Operator traverses the PD member health status obtained from the PD client. When the PD member is unhealthy and the duration between its last transition time and now is longer than `failoverDeadline`, the member is marked as unhealthy. Its Pod information and PVC information are recorded in `tc.Status.PD.FailureMembers`.

    ```go
    for pdName, pdMember := range tc.Status.PD.Members {
        podName := strings.Split(pdName, ".")[0]

        failoverDeadline := pdMember.LastTransitionTime.Add(f.deps.CLIConfig.PDFailoverPeriod)
        _, exist := tc.Status.PD.FailureMembers[pdName]

        if pdMember.Health || time.Now().Before(failoverDeadline) || exist {
            continue
        }

        pod, _ := f.deps.PodLister.Pods(ns).Get(podName)

        pvcs, _ := util.ResolvePVCFromPod(pod, f.deps.PVCLister)

        f.deps.Recorder.Eventf(tc, apiv1.EventTypeWarning, "PDMemberUnhealthy", "%s/%s(%s) is unhealthy", ns, podName, pdMember.ID)

        pvcUIDSet := make(map[types.UID]struct{})
        for _, pvc := range pvcs {
            pvcUIDSet[pvc.UID] = struct{}{}
        }
        tc.Status.PD.FailureMembers[pdName] = v1alpha1.PDFailureMember{
            PodName:       podName,
            MemberID:      pdMember.ID,
            PVCUIDSet:     pvcUIDSet,
            MemberDeleted: false,
            CreatedAt:     metav1.Now(),
        }
        return controller.RequeueErrorf("marking Pod: %s/%s pd member: %s as failure", ns, podName, pdMember.Name)
    }
    ```

2. TiDB Operator calls the `tryToDeleteAFailureMember` function to process the `FailureMembers`. It traverses all failure members, and when it encounters a member whose `MemberDeleted` is `False`, it calls the PD client to delete the member and tries to recover the Pod.

    ```go
    func (f *pdFailover) tryToDeleteAFailureMember(tc *v1alpha1.TidbCluster) error {
        ns := tc.GetNamespace()
        tcName := tc.GetName()
        var failureMember *v1alpha1.PDFailureMember
        var failurePodName string
        var failurePDName string

        for pdName, pdMember := range tc.Status.PD.FailureMembers {
            if !pdMember.MemberDeleted {
                failureMember = &pdMember
                failurePodName = strings.Split(pdName, ".")[0]
                failurePDName = pdName
                break
            }
        }
        if failureMember == nil {
            klog.Infof("No PD FailureMembers to delete for tc %s/%s", ns, tcName)
            return nil
        }

        memberID, err := strconv.ParseUint(failureMember.MemberID, 10, 64)
        if err != nil {
            return err
        }

        if err := controller.GetPDClient(f.deps.PDControl, tc).DeleteMemberByID(memberID); err != nil {
            klog.Errorf("pd failover[tryToDeleteAFailureMember]: failed to delete member %s/%s(%d), error: %v", ns, failurePodName, memberID, err)
            return err
        }
        klog.Infof("pd failover[tryToDeleteAFailureMember]: delete member %s/%s(%d) successfully", ns, failurePodName, memberID)
    ...
    ```

    Delete the failed Pod.

    ```go
    pod, err := f.deps.PodLister.Pods(ns).Get(failurePodName)
        if err != nil && !errors.IsNotFound(err) {
            return fmt.Errorf("pd failover[tryToDeleteAFailureMember]: failed to get pod %s/%s for tc %s/%s, error: %s", ns, failurePodName, ns, tcName, err)
        }
        if pod != nil {
            if pod.DeletionTimestamp == nil {
                if err := f.deps.PodControl.DeletePod(tc, pod); err != nil {
                    return err
                }
            }
        } else {
            klog.Infof("pd failover[tryToDeleteAFailureMember]: failure pod %s/%s not found, skip", ns, failurePodName)
        }
    ```

    Delete the PVC.

    ```go
    for _, pvc := range pvcs {
        _, pvcUIDExist := failureMember.PVCUIDSet[pvc.GetUID()]
        // for backward compatibility, if there exists failureMembers and user upgrades operator to newer version
        // there will be failure member structures with PVCUID set from api server, we should handle this as pvcUIDExist == true
        if pvc.GetUID() == failureMember.PVCUID {
            pvcUIDExist = true
        }
        if pvc.DeletionTimestamp == nil && pvcUIDExist {
            if err := f.deps.PVCControl.DeletePVC(tc, pvc); err != nil {
                klog.Errorf("pd failover[tryToDeleteAFailureMember]: failed to delete PVC: %s/%s, error: %s", ns, pvc.Name, err)
                return err
            }
            klog.Infof("pd failover[tryToDeleteAFailureMember]: delete PVC %s/%s successfully", ns, pvc.Name)
        }
    }
    ```

    Mark the status of ``tc.Status.PD.FailureMembers`` as `Deleted`.

    ```go
    setMemberDeleted(tc, failurePDName)
    ```

3. `​​tc.PDStsDesiredReplicas()` obtains the number of PD StatefulSet replicas, which equals the number of StatefulSet replicas plus the deleted failure members. When syncing the StatefulSet, TiDB Operator calls the scaling-out logic to add a PD Pod for failover.

    ```go
    func (tc *TidbCluster) GetPDDeletedFailureReplicas() int32 {
        var deletedReplicas int32 = 0
        for _, failureMember := range tc.Status.PD.FailureMembers {
            if failureMember.MemberDeleted {
                deletedReplicas++
            }
        }
        return deletedReplicas
    }

    func (tc *TidbCluster) PDStsDesiredReplicas() int32 {
        return tc.Spec.PD.Replicas + tc.GetPDDeletedFailureReplicas()
    }
    ```

## Other component's control loop

Now that you know how TiDB Operator manages PD's lifecycle, I'll move on to the differences between PD and other components.

### TiKV and TiFlash

[TiKV](https://docs.pingcap.com/tidb/stable/tikv-overview) and [TiFlash](https://docs.pingcap.com/tidb/stable/tiflash-overview) are two storage engines of TiDB and have a similar lifecycle management mechanism. In this section, I'll take TiKV as an example.

* When syncing the StatefulSet, the TiKV member manager needs to set TiKV store labels using the `setStoreLabelsForTiKV` function. This function gets the node labels and sets labels for TiKV stores via the PD client's `SetStoreLables` function.

    ```go
    for _, store := range storesInfo.Stores {
        nodeName := pod.Spec.NodeName
        ls, _ := getNodeLabels(m.deps.NodeLister, nodeName, storeLabels)

        if !m.storeLabelsEqualNodeLabels(store.Store.Labels, ls) {
            set, err := pdCli.SetStoreLabels(store.Store.Id, ls)
            if err != nil {
                continue
            }
            if set {
                setCount++
                klog.Infof("pod: [%s/%s] set labels: %v successfully", ns, podName, ls)
            }
        }
    }
    ```

* When syncing Status, the TiKV member manager calls the PD client's `GetStores` function and obtains the TiKV store information from PD. It then categorizes the store information for later synchronization. This operation is similar to PD's syncing status, in which the PD member manager calls the `GetMembers` function and records PD member information.

* When syncing Service, the TiKV member manager only creates headless Services for parsing TiKV Pod DNS.

* When syncing ConfigMap, the TiKV member manager uses a template in the `templates.go` file, calls the `RenderTiKVStartScript` function to generate the TiKV start script, and calls the `transformTiKVConfigMap` function to get the TiKV configuration file.

* When performing scaling operations, the TiKV member manager must safely take TiKV stores offline. It calls the PD client's `DeleteStore` function to delete the corresponding store from the TiKV Pod.

* In terms of rolling upgrade, the TiKV member manager must ensure that the Region Leader is not on the Pod to be upgraded. Before the rolling upgrade, TiKV Upgrader checks whether the Pod annotation contains `EvictLeaderBeginTime` and determines whether it has performed `EvictLeader` on this Pod. If not, it calls the `BeginEvictLeader` function from the PD client and adds an evict leader scheduler to the TiKV store. The Region Leader is then evicted from the TiKV store.

    ```go
    ​​_, evicting := upgradePod.Annotations[EvictLeaderBeginTime]
    if !evicting {
        return u.beginEvictLeader(tc, storeID, upgradePod)
    }
    ```

    In the `readyToUpgrade` function, when the Region Leader is zero, or when the evict Leader duration exceeds `tc.Spec.TiKV.EvictLeaderTimeout`, the partition configuration in the StatefulSet `UpdateStrategy` is updated, which triggers Pod upgrade. When PD finishes the upgrade, it calls the `endEvictLeaderbyStoreID` function to end the operation.

* When performing failover, the TiKV member manager records the timestamp of the last store state change.

    ```go
    status.LastTransitionTime = metav1.Now()
    if exist && status.State == oldStore.State {
        status.LastTransitionTime = oldStore.LastTransitionTime
    }
    ```

    When the store state is `v1alpha1.TiKVStateDown` and the downtime exceeds the maximum failover timeout, the TiKV Pod is added to `FailureStores`.

    ```go
    ​​if store.State == v1alpha1.TiKVStateDown && time.Now().After(deadline) && !exist {
        if tc.Status.TiKV.FailureStores == nil {
            tc.Status.TiKV.FailureStores = map[string]v1alpha1.TiKVFailureStore{}
        }
        if tc.Spec.TiKV.MaxFailoverCount != nil && *tc.Spec.TiKV.MaxFailoverCount > 0 {
            maxFailoverCount := *tc.Spec.TiKV.MaxFailoverCount
            if len(tc.Status.TiKV.FailureStores) >= int(maxFailoverCount) {
                klog.Warningf("%s/%s failure stores count reached the limit: %d", ns, tcName, tc.Spec.TiKV.MaxFailoverCount)
                return nil
            }
            tc.Status.TiKV.FailureStores[storeID] = v1alpha1.TiKVFailureStore{
                PodName:   podName,
                StoreID:   store.ID,
                CreatedAt: metav1.Now(),
            }
            msg := fmt.Sprintf("store[%s] is Down", store.ID)
            f.deps.Recorder.Event(tc, corev1.EventTypeWarning, unHealthEventReason, fmt.Sprintf(unHealthEventMsgPattern, "tikv", podName, msg))
        }
    }
    ```

    When syncing TiKV StatefulSet, the number of replicas includes the number of `FailureStores`, which triggers the scaling-out logic and completes the failover operation.

### TiDB, TiCDC, and Pump

TiDB, TiCDC, and Pump have a similar lifecycle management mechanism. Compared to other components, their rolling upgrade is only carried out when the member is healthy.

During scaling, TiDB Operator needs to pay extra attention to PVC usage. When scaling in the cluster, TiDB Operator needs to add `deferDeleting` to ensure data safety; when scaling out the cluster, TiDB Operator also needs to remove the PVC.

In addition, TiDB Operator only supports failover logic for TiDB, but not for TiCDC or Pump.

## Summary

In this post, taking PD as an example, we have learned the implementation of PD's control loop and compared PD with other components. By now you should be familiar with the member manager design of major TiDB components and how TiDB Operator implements TiDB lifecycle management.

In the next article, we'll discuss **how TiDB Operator implements backup and restore for TiDB clusters**. Stay tuned!

If you are interested in learning more about TiDB Operator, feel free to [join our Slack channel](https://slack.tidb.io/invite?team=tidb-community&channel=sig-k8s&ref=pingcap-blog) or join our discussions at [pingcap/tidb-operator](https://github.com/pingcap/tidb-operator).

---

If you've missed an article in our series, you can read them here:

* [TiDB Operator Source Code Reading (I): Overview](https://pingcap.com/blog/tidb-operator-source-code-reading-1-overview)
* [TiDB Operator Source Code Reading (II): Operator Pattern](https://pingcap.com/blog/tidb-operator-source-code-reading-2-operator-pattern)
* [TiDB Operator Source Code Reading (III): The Component Control Loop](https://pingcap.com/blog/tidb-operator-source-code-reading-3-component-control-loop)
