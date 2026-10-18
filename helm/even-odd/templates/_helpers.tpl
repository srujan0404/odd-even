{{- define "even-odd.name" -}}
{{- .Release.Name -}}
{{- end -}}

{{- define "even-odd.tag" -}}
{{- required "image.tag is required, pass --set image.tag=<git sha>" .Values.image.tag -}}
{{- end -}}

{{- define "even-odd.labels" -}}
app.kubernetes.io/name: even-odd
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ include "even-odd.tag" . | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "even-odd.selector" -}}
app.kubernetes.io/name: even-odd
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
