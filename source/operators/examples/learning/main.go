package main

import "k8s.io/apimachinery/pkg/runtime"

func main() {
	scheme := runtime.NewScheme()

	_ = corev1.AddToScheme(scheme)
}
