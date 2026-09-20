package controllers

import (
	"context"
	"fmt"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/intstr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	platformv1alpha1 "db-orchestrator/api/v1alpha1"
)

const workspaceFinalizer = "platform.ebpf.io/finalizer"

type WorkspaceReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=platform.ebpf.io,resources=workspaces,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=platform.ebpf.io,resources=workspaces/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=platform.ebpf.io,resources=workspaces/finalizers,verbs=get;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=namespaces;services;persistentvolumeclaims,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="apps",resources=statefulsets,verbs=get;list;watch;create;update;patch;delete

func (r *WorkspaceReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := logf.FromContext(ctx)

	var workspace platformv1alpha1.Workspace
	if err := r.Get(ctx, req.NamespacedName, &workspace); err != nil {
		if errors.IsNotFound(err) {
			return ctrl.Result{}, nil
		}
		return ctrl.Result{}, err
	}

	tenantName := workspace.Spec.TenantName
	if tenantName == "" || tenantName == "string" {
		tenantName = workspace.Name
	}
	targetNamespace := fmt.Sprintf("postgres-%s", workspace.Name)

	// Handle deletion / finalizer
	if workspace.GetDeletionTimestamp() != nil {
		if controllerutil.ContainsFinalizer(&workspace, workspaceFinalizer) {
			log.Info("Deleting target namespace", "namespace", targetNamespace)
			ns := &corev1.Namespace{
				ObjectMeta: metav1.ObjectMeta{Name: targetNamespace},
			}
			if err := r.Delete(ctx, ns); err != nil && !errors.IsNotFound(err) {
				return ctrl.Result{}, err
			}

			controllerutil.RemoveFinalizer(&workspace, workspaceFinalizer)
			if err := r.Update(ctx, &workspace); err != nil {
				return ctrl.Result{}, err
			}
		}
		return ctrl.Result{}, nil
	}

	if !controllerutil.ContainsFinalizer(&workspace, workspaceFinalizer) {
		controllerutil.AddFinalizer(&workspace, workspaceFinalizer)
		if err := r.Update(ctx, &workspace); err != nil {
			return ctrl.Result{}, err
		}
	}

	// 1. Ensure Namespace exists (Cluster-scoped: no controller reference)
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: targetNamespace,
			Labels: map[string]string{
				"app.kubernetes.io/managed-by": "workspace-controller",
				"security.ebpf.io/zero-trust":  "enabled",
			},
		},
	}
	if _, err := ctrl.CreateOrUpdate(ctx, r.Client, ns, func() error {
		return nil
	}); err != nil {
		return ctrl.Result{}, err
	}

	// 2. Ensure StatefulSet exists (Minimal Footprint: 10Mi mem, 5m cpu, 100Mi storage)
	sts := &appsv1.StatefulSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "postgres",
			Namespace: targetNamespace,
		},
	}

	_, err := ctrl.CreateOrUpdate(ctx, r.Client, sts, func() error {
		replicas := int32(1)
		sts.Spec = appsv1.StatefulSetSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{"app": "postgres"},
			},
			ServiceName: "postgres-svc",
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{"app": "postgres"},
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:  "postgres",
							Image: "postgres:15-alpine",
							Env: []corev1.EnvVar{
								{Name: "POSTGRES_PASSWORD", Value: "secretpassword"},
							},
							Ports: []corev1.ContainerPort{
								{ContainerPort: 5432, Name: "postgresql"},
							},
							Resources: corev1.ResourceRequirements{
								Requests: corev1.ResourceList{
									corev1.ResourceMemory: resource.MustParse("10Mi"),
									corev1.ResourceCPU:    resource.MustParse("5m"),
								},
								Limits: corev1.ResourceList{
									corev1.ResourceMemory: resource.MustParse("64Mi"),
									corev1.ResourceCPU:    resource.MustParse("50m"),
								},
							},
							VolumeMounts: []corev1.VolumeMount{
								{Name: "postgres-data", MountPath: "/var/lib/postgresql/data"},
							},
						},
					},
				},
			},
			VolumeClaimTemplates: []corev1.PersistentVolumeClaim{
				{
					ObjectMeta: metav1.ObjectMeta{Name: "postgres-data"},
					Spec: corev1.PersistentVolumeClaimSpec{
						AccessModes: []corev1.PersistentVolumeAccessMode{corev1.ReadWriteOnce},
						Resources: corev1.VolumeResourceRequirements{
							Requests: corev1.ResourceList{
								corev1.ResourceStorage: resource.MustParse("100Mi"),
							},
						},
					},
				},
			},
		}
		return nil
	})
	if err != nil {
		return ctrl.Result{}, err
	}

	// 3. Ensure Service exists
	svc := &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "postgres-svc",
			Namespace: targetNamespace,
		},
	}
	_, err = ctrl.CreateOrUpdate(ctx, r.Client, svc, func() error {
		svc.Spec = corev1.ServiceSpec{
			Selector: map[string]string{"app": "postgres"},
			Ports: []corev1.ServicePort{
				{Port: 5432, TargetPort: intstr.FromInt(5432), Name: "postgresql"},
			},
		}
		return nil
	})
	if err != nil {
		return ctrl.Result{}, err
	}

	// Update Status
	workspace.Status.Phase = "Ready"
	workspace.Status.Namespace = targetNamespace
	if err := r.Status().Update(ctx, &workspace); err != nil {
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

func (r *WorkspaceReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&platformv1alpha1.Workspace{}).
		Complete(r)
}
