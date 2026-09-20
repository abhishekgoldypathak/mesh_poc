package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

type WorkspaceSpec struct {
	WorkspaceID     string `json:"workspaceId"`
	TenantName      string `json:"tenantName"`
	MemgraphVersion string `json:"memgraphVersion,omitempty"`
	MemgraphImage   string `json:"memgraphImage,omitempty"` // <-- Added dynamic image support
	StorageSize     string `json:"storageSize,omitempty"`
}

type WorkspaceStatus struct {
	Phase     string `json:"phase,omitempty"`
	Namespace string `json:"namespace,omitempty"`
	Endpoint  string `json:"endpoint,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Tenant",type="string",JSONPath=".spec.tenantName"
// +kubebuilder:printcolumn:name="Status",type="string",JSONPath=".status.phase"

type Workspace struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   WorkspaceSpec   `json:"spec,omitempty"`
	Status WorkspaceStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

type WorkspaceList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []Workspace `json:"items"`
}

func init() {
	SchemeBuilder.Register(&Workspace{}, &WorkspaceList{})
}
