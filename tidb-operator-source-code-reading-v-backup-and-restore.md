---
title: 'TiDB Operator Source Code Reading (V): Backup and Restore'
author: ['Elon Li']
date: 2021-12-14
summary: This post explains the design and implementation of the backup and restore features provided by TiDB Operator. You'll learn about the core logic of three related controllers and the backup-manager.
tags: ['TiDB Operator', 'Kubernetes']
categories: ['Engineering']
image: /images/blog/tidb-operator-source-code-reading-v-backup-and-restore.jpg
---

**Author:** [Elon Li](https://github.com/dragonly) (Software Engineer at PingCAP) 

**Transcreator:** [Ran Huang](https://github.com/ran-huang); **Editor:** Tom Dewan

![Kubernetes cloud-native TiDB](media/tidb-operator-source-code-reading-v-backup-and-restore.jpg)

_Previous articles in this series:_

* _[TiDB Operator Source Code Reading (I): Overview](https://pingcap.com/blog/tidb-operator-source-code-reading-1-overview)_
* _[TiDB Operator Source Code Reading (II): Operator Pattern](https://pingcap.com/blog/tidb-operator-source-code-reading-2-operator-pattern)_
* _[TiDB Operator Source Code Reading (III): The Component Control Loop](https://pingcap.com/blog/tidb-operator-source-code-reading-3-component-control-loop)_
* _[TiDB Operator Source Code Reading (IV): Implementing a Component Control Loop](https://pingcap.com/blog/tidb-operator-source-code-reading-4-implement-component-control-loop)_

In our last article, we learned how to [implement a component control loop](https://pingcap.com/blog/tidb-operator-source-code-reading-4-implement-component-control-loop) in TiDB Operator. This time, I'll move on to a new but important topic: backup and restore.

Backup and restore are two of the most important and frequently used operations when you maintain a database. To ensure data safety, database maintainers usually need a set of scripts that automatically back up the data and recover the dataset when data is corrupted. A well-designed backup and restore platform should allow you to:

* Choose different data sources and target storage.
* Execute backup jobs on scheduled time.
* Maintain the backup and restore history for auditing.
* Clean up obsolete backup files to save storage space.

TiDB Operator provides CustomResourceDefinitions (CRDs) for all these requirements. In this post, **I'll walk you through the core design logic of TiDB Operator's backup and restore features**, leaving out the trivial implementation details. Let's get started.

## Controllers

TiDB Operator performs ad-hoc backup, restore, and scheduled backup via custom resources (CRs) such as `Backup`, `Restore`, and `BackupSchedule`, so we implement three corresponding controllers to execute the control loops.

When a user needs to start a backup job, they can create a YAML file as follows and submit it to Kubernetes. For example:

```
# An example backup job
apiVersion: pingcap.com/v1alpha1
kind: Backup
metadata:
  name: demo-backup-gcp
  namespace: test1
spec:
  br:
    cluster: mycluster
  gcs:
    projectId: gcp
    location: us-west2
    bucket: backup
    prefix: test1-demo1
    secretName: gcp-secret
```

When the backup controller receives an event that creates the `Backup` resource, it creates a job to do the configured backup operation. In the case above, it backs up data in the `mycluster` database in the `test1` namespace and stores the data in the GCP storage specified in the `gcs` field.

In the following sections, I'll explain the internal logic of the three controllers. 

### The backup controller

The backup controller manages the `Backup` CR. Based on the configuration in the `spec` field, the controller uses [BR](https://docs.pingcap.com/tidb/stable/backup-and-restore-tool) or [Dumpling](https://docs.pingcap.com/tidb/stable/dumpling-overview) to perform the backup task and deletes the corresponding backup file when the user deletes the `Backup` CR. 

Similar to that of other controllers, **the core of the backup controller is a control loop**, which listens to the `Backup` CR events (create, update, and delete) and runs the required operations.  

In this section, I'll skip the generic control loop logic and focus on the core backup logic.

#### Core logic

The core logic of the backup controller is implemented in the `syncBackupJob` function in the `pkg/backup/backup/backup_manager.go` file. The actual code processes many corner cases; to facilitate understanding, we removed the unimportant details, so you may see some function signatures are inconsistent. The core logic code is as follows: 

```
backuputil.ValidateBackup(backup)
if err := JobLister.Jobs(ns).Get(backupJobName); err == nil {
    return nil
} else if !errors.IsNotFound(err) {
    return err
}
if backup.Spec.BR == nil {
    // create Job Spec which will use Dumpling to do the work
    job = bm.makeExportJob(backup)
} else {
    // create Job Spec which will use BR to do the work
    job = bm.makeBackupJob(backup)
}
if err := bm.deps.JobControl.CreateJob(backup, job); err != nil {
    // update Backup.Status with error message
}
```

In the code block above, `backup` is the Go struct converted from the `Backup` YAML created by the user. We use a `ValidateBackup` function to check the validity of the fields in `backup`. 

Because the backup task is executed as a Kubernetes-native job and because the controller must ensure idempotency—duplicated executions don't affect the end result—it is possible that a job already exists. Therefore, we try to find if there is an existing backup job in the same namespace:

* If a job is found, the `if` statement returns `nil` and stops processing the current backup object. 
* If a job is not found, the controller proceeds to the next step.

Next, the controller decides whether to use BR or Dumpling to perform the backup task and executes the corresponding function to create the Job spec. In this step, if you have configured the `br` field, the controller chooses BR; otherwise, it goes with Dumpling.

Finally, the controller uses `CreateJob` to create the job object and executes the backup operation in the job Pod. 

#### Create Job

The actual backup job is created by two functions: `makeExportJob` and `makeBackupJob`. I'll take `makeBackupJob` as an example and explain its core code (which is simplified below):

```
tc := bm.deps.TiDBClusterLister.TidbClusters(backupNamespace).Get(backup.Spec.BR.Cluster)
envVars := backuputil.GenerateTidbPasswordEnv(ns, name, backup, bm)
envVars = append(envVars, backuputil.GenerateStorageCertEnv(ns, backup, bm))
args := []string{"backup", fmt.Sprintf("--namespace=%s", ns), fmt.Sprintf("--backupName=%s", name)}
podSpec := &corev1.PodTemplateSpec{
    Spec: corev1.PodSpec{
        InitContainers: []corev1.Container{{
            Image:   "pingcap/br",
            Command: []string{"/bin/sh", "-c"},
            Args:    []string{fmt.Sprintf("cp /br %s/br; echo 'BR copy finished'", util.BRBinPath)},
        }},
        Containers: []corev1.Container{{
            Image:           "pingcap/tidb-backup-manager",
            Args:            args,
            Env:             util.AppendEnvIfPresent(envVars, "TZ"),
        }},
        Volumes:          volumes,
    },
}
job := &batchv1.Job{
    Spec: batchv1.JobSpec{
        Template:     *podSpec,
    },
}
```

In the code above, the controller:

1. Obtains the `TidbCluster` resources according to the backup information.
2. Sets the environment variables and command-line arguments.
3. Constructs a job using `pingcap/tidb-backup-manager` as the image to perform the backup task. In this process, the `pingcap/br` image is used as the init container so that BR is copied to the actual working container. 
4. Executes the [backup-manager](#heading=h.g8pxm2t1s6sp) logic after the job is created.

The `makeExportJob` function takes similar steps, except that it uses Dumpling rather than BR. 

<div class="trackable-btns">
  <a href="/download" onclick="trackViews('TiDB Operator Source Code Reading (V): Backup and Restore', 'download-tidb-btn-middle')"><button>Download TiDB</button></a>
  <a href="https://share.hsforms.com/1e2W03wLJQQKPd1d9rCbj_Q2npzm" onclick="trackViews('TiDB Operator Source Code Reading (V): Backup and Restore', 'subscribe-blog-btn-middle')"><button>Subscribe to Blog</button></a>
</div>

#### Clean backup files

After a user deletes the `Backup` resource, the backup controller deletes the backup files and releases the storage space.

As mentioned in the previous section, the backup controller creates a job when it receives the create event. Meanwhile, the controller adds a string (`tidb.pingcap.com/backup-protection`) to `finalizers` of the `Backup` resource, which signals that the resource needs special treatment when deleted. When a user deletes the `Backup` resource, the API server sets a value for the `metadata.deletionTimestamp` field. The backup controller then checks the clean policy of the `Backup` resource. If the clean policy isn't `Retain`, the controller creates a clean job to delete the backup files and reclaim the storage space. 

### The restore controller

Restoration is the reverse process of backup, and their core logic is similar. 

The restore controller checks the validity of the `Restore` field and then calls the `makeImportJob` function (using TiDB Lightning) or the `makeRestoreJob` function (using BR) to create the restore job. The restore job also uses the backup-manager as a basic image. 

### The backupschedule controller

To ensure data safety, we usually need to automatically back up important data on a scheduled basis. The backupschedule controller implements such functionality. 

A user can schedule a backup job in Cron format and configure backup details similar to ad-hoc backup. After the configuration is submitted to the API server, TiDB Operator runs a scheduled backup with this configuration. 

To avoid taking up a lot of storage, a user can also decide on the maximum number of copies to save or the maximum time to keep them. TiDB Operator deletes the outdated backup files.  

The design logic of the backupschedule controller uses the existing functionality of the backup controller and encapsulates an abstraction layer for scheduled execution. When TiDB Operator runs a scheduled backup task, the backupschedule controller simply creates a `Backup` resource and has the backup controller do the rest. 

You may have noticed that this design is similar to the relationship between [CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/) and [the Job controller](https://kubernetes.io/docs/concepts/workloads/controllers/job/). In fact, the implementation of the backupschedule controller is borrowed from CronJob, especially the logic that determines the next execution time.

#### Core logic

The core logic of the backupschedule controller is implemented in the `Sync` function in the `pkg/backup/backupschedule/backup_schedule_manager.go` file. The main logic is as follows. For implementation details, you can refer to the source code.

```
func (bm *backupScheduleManager) Sync(bs *v1alpha1.BackupSchedule) error {
    defer bm.backupGC(bs)
    if err := bm.canPerformNextBackup(bs); err != nil { 
        return err 
    }    
    scheduledTime, err := getLastScheduledTime(bs, bm.now)
    if err := bm.deleteLastBackupJob(bs); err != nil { 
        return nil 
    }
    backup, err := createBackup(bm.deps.BackupControl, bs, *scheduledTime)
    bs.Status.LastBackup = backup.GetName()
    bs.Status.LastBackupTime = &metav1.Time{Time: *scheduledTime}
    bs.Status.AllBackupCleanTime = nil
    return nil
}
```

The code first calls the `canPerformNextBackup` function to determine if a new `Backup` resource should be created to perform a new backup task. If the previous backup has completed or the previous backup has failed, the function agrees to execute the next backup; otherwise, the request is rejected.

After deciding to execute the backup task, the controller call `getLastScheduledTime` to get the next backup execution time. `getLastScheduledTime` calculates the last Cron time just before the current time, based on the current time and the Cron settings. `getLastScheduledTime` also handles a lot of boundary conditions; you can check the source code if you're interested to know more.

When the controller gets the backup time, it calls the `createBackup` function to create the `Backup` resource, thus leaving the actual backup operation to the backup controller. 

## backup-manager

To adapt TiDB Operator to the Kubernetes execution environment, we abstracted a backup-manager on top of BR, Dumpling, and TiDB Lightning. The backup-manager provides a uniform encapsulation of entry parameters for the tools. When each controller creates a job resource, it uses the backup-manager as an image. The backup-manager starts the corresponding tools to perform backup or restore tasks with the container start parameters and the `Backup`/`Restore` resource specs. Moreover, the backup-manager syncs the status of the `Backup` and `Restore` resources and updates their progress. 

### Backup/restore using BR

This section explains how the backup-manager implements the main logic of backup and restore. When the backup controller calls the `makeBackupJob` function to create a backup job, the Job controller starts a Pod to run the task, using the backup-manager as the image. The first container start parameter passed to `makeBackupJob` is `backup`; the `backup` processing logic is located in **`cmd/backup-manager/app/cmd/backup.go`**.

Similar to controllers, when the Pod is started, the backup-manager constructs a series of common Kubernetes client objects, such as Informer, Lister, and Updater. Then it calls the `ProcessBackup` function and performs the backup. The simplified main logic is as follows:

```
    backup, err := bm.backupLister.Backups(bm.Namespace).Get(bm.ResourceName)
    if backup.Spec.From == nil {
        return bm.performBackup(ctx, backup.DeepCopy(), nil)
    }
func (bm *Manager) performBackup(ctx context.Context, backup *v1alpha1.Backup, db *sql.DB) error {
    // update status to BackupRunning
    backupFullPath, err := util.GetStoragePath(backup)
    backupErr := bm.backupData(ctx, backup)
    // update status to BackupComplete
}
func (bo *Options) backupData(ctx context.Context, backup *v1alpha1.Backup) error {
    clusterNamespace := backup.Spec.BR.ClusterNamespace
    args := make([]string, 0)
    args = append(args, fmt.Sprintf("--pd=%s-pd.%s:2379", backup.Spec.BR.Cluster, clusterNamespace))
    dataArgs, err := constructOptions(backup)
    args = append(args, dataArgs...)
    fullArgs := []string{"backup", backupType}
    fullArgs = append(fullArgs, args...)
    klog.Infof("Running br command with args: %v", fullArgs)
    bin := path.Join(util.BRBinPath, "br")
    cmd := exec.CommandContext(ctx, bin, fullArgs...)
    // parse error messages
}
```

`ProcessBackup` runs on a simple logic:

1. It obtains the `Backup` object in the corresponding namespace and calls `performBackup`. 
2. The `performBackup` function gets the backup storage path and calls the `backupData` function. We support three backup paths: `s3`, `gcs`, and `local`. `local` refers to the local path mounted by persistent volumes (PVs). 
3. `backupData` uses BR to perform the backup. This function combines the command-line parameters BR needs and uses `backup` as the command to run the BR binary and parse error messages. 

After the `backup` command runs successfully, the backup task is complete. 

### Import/export using Dumpling and TiDB Lightning

Import and export are similar to backup and restore using BR, except that the tools involved are Dumpling and TiDB Lightning. You can check the previous section for details. 

### Clean

When the backup controller creates a job to execute the **clean** command, the backup-manager executes the clean logic to delete the corresponding backup files. In `cmd/backup-manager/app/cmd/clean.go`, the clean logic calls the `ProcessCleanBackup` function to start the clean process. 

After a series of checks, the controller calls `cleanBRRemoteBackupData` or `cleanRemoteBackupData` to delete the BR or Dumpling backup files from remote storage. 

## Summary

In this post, we talked about the design and implementation of TiDB Operator's backup and restore features. When a user creates a backup or restore task, the corresponding backup, restore, or backupschedule controller calls the backup-manager to run the actual operations. The backupschedule controller encapsulates the timing task logic based on the backup controller, while the backup-manager encapsulates the specific tools into a unified portal for each controller to call. 

If you are interested in learning more about TiDB Operator, feel free to [join our Slack channel](https://slack.tidb.io/invite?team=tidb-community&channel=sig-k8s&ref=pingcap-blog) or join our discussions at [pingcap/tidb-operator](https://github.com/pingcap/tidb-operator).
