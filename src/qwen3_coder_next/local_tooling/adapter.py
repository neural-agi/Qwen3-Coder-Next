"""Tool adapter layer for the local tooling boundary."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from qwen3_coder_next.local_tooling.artifact_registry import ArtifactRegistry, ArtifactRegistryRequest, ArtifactRegistryResult
from qwen3_coder_next.local_tooling.audit import AuditLogger, AuditLoggerRequest, AuditLoggerResult
from qwen3_coder_next.local_tooling.commands import CommandRequest, CommandRunResult, CommandRunner
from qwen3_coder_next.local_tooling.contracts import (
    ArtifactManifest,
    ArtifactProvenance,
    AuditRecord,
    RequestEnvelope,
    ResponseEnvelope,
    WorkspaceContext,
)
from qwen3_coder_next.local_tooling.diff import DiffRequest, DiffResult, DiffService
from qwen3_coder_next.local_tooling.filesystem import FileSystemOperationRequest, FileSystemOperationResult, FileSystemService
from qwen3_coder_next.local_tooling.operations import (
    DeterministicFileSystemOperator,
    DeterministicFileMutationService,
    FileMutationRequest,
    FileMutationResult,
    FileMutationService,
    FileMutationType,
    FileSystemOperation,
    FileSystemOperationType,
    FileSystemOperator,
)
from qwen3_coder_next.local_tooling.reads import FileReadRequest, FileReadResult, FileReadService
from qwen3_coder_next.local_tooling.resolution import WorkspaceResolutionRequest, WorkspaceResolver


class ToolAdapterOperation(StrEnum):
    """Supported normalized tool adapter operations."""

    FILE_READ = "file.read"
    FILESYSTEM_OPERATION = "filesystem.operation"
    FILESYSTEM_MUTATION = "filesystem.mutation"
    DIFF_GENERATE = "diff.generate"
    COMMAND_RUN = "command.run"
    ARTIFACT_REGISTER = "artifact.register"
    ARTIFACT_SUPERSEDE = "artifact.supersede"
    ARTIFACT_ARCHIVE = "artifact.archive"
    ARTIFACT_GET = "artifact.get"
    ARTIFACT_LIST = "artifact.list"
    ARTIFACT_HISTORY = "artifact.history"
    AUDIT_APPEND = "audit.append"
    AUDIT_GET = "audit.get"
    AUDIT_LIST = "audit.list"
    AUDIT_HISTORY = "audit.history"


class ToolAdapter(ABC):
    """Abstract tool adapter interface."""

    @abstractmethod
    def handle(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Handle a normalized tool request."""


class DeterministicToolAdapter(ToolAdapter):
    """Deterministic adapter that routes local tooling requests to services."""

    def __init__(
        self,
        *,
        workspace_resolver: WorkspaceResolver,
        file_read_service: FileReadService | None = None,
        filesystem_service: FileSystemService | None = None,
        filesystem_operator: FileSystemOperator | None = None,
        file_mutation_service: FileMutationService | None = None,
        diff_service: DiffService | None = None,
        command_runner: CommandRunner | None = None,
        artifact_registry: ArtifactRegistry | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._workspace_resolver = workspace_resolver
        self._file_read_service = file_read_service
        self._filesystem_service = filesystem_service
        self._filesystem_operator = filesystem_operator or DeterministicFileSystemOperator(filesystem_service)
        self._file_mutation_service = file_mutation_service or DeterministicFileMutationService()
        self._diff_service = diff_service
        self._command_runner = command_runner
        self._artifact_registry = artifact_registry
        self._audit_logger = audit_logger

    def handle(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Normalize the request, route it, and return a normalized response."""

        if not isinstance(request.payload, dict):
            return self._failure(request, "invalid_payload", "Payload must be a mapping.")

        operation = self._normalize_operation(request.operation)
        workspace_result = self._workspace_resolver.resolve(
            WorkspaceResolutionRequest(
                request_id=request.request_id,
                workspace_id=request.workspace.workspace_id,
                metadata=request.metadata,
            )
        )
        if not workspace_result.resolved or workspace_result.workspace is None:
            return self._failure(request, operation, "workspace_not_resolved", "Workspace could not be resolved.")

        workspace = workspace_result.workspace
        if operation == ToolAdapterOperation.FILE_READ:
            return self._handle_file_read(request, workspace, operation)
        if operation == ToolAdapterOperation.FILESYSTEM_OPERATION:
            return self._handle_filesystem_operation(request, workspace, operation)
        if operation == ToolAdapterOperation.FILESYSTEM_MUTATION:
            return self._handle_filesystem_mutation(request, workspace, operation)
        if operation == ToolAdapterOperation.DIFF_GENERATE:
            return self._handle_diff(request, workspace, operation)
        if operation == ToolAdapterOperation.COMMAND_RUN:
            return self._handle_command(request, workspace, operation)
        if operation in {
            ToolAdapterOperation.ARTIFACT_REGISTER,
            ToolAdapterOperation.ARTIFACT_SUPERSEDE,
            ToolAdapterOperation.ARTIFACT_ARCHIVE,
            ToolAdapterOperation.ARTIFACT_GET,
            ToolAdapterOperation.ARTIFACT_LIST,
            ToolAdapterOperation.ARTIFACT_HISTORY,
        }:
            return self._handle_artifact_registry(request, workspace, operation)
        if operation in {
            ToolAdapterOperation.AUDIT_APPEND,
            ToolAdapterOperation.AUDIT_GET,
            ToolAdapterOperation.AUDIT_LIST,
            ToolAdapterOperation.AUDIT_HISTORY,
        }:
            return self._handle_audit_logger(request, workspace, operation)
        return self._failure(request, operation, "unsupported_operation", "Operation is not supported.", workspace=workspace)

    def _handle_file_read(self, request: RequestEnvelope, workspace: WorkspaceContext, operation: str) -> ResponseEnvelope:
        if self._file_read_service is None:
            return self._failure(request, operation, "service_unavailable", "File read service is unavailable.", workspace=workspace)
        read_result = self._file_read_service.read(
            FileReadRequest(
                request_id=request.request_id,
                workspace=workspace,
                path=request.payload.get("path", ""),
                preview_length=int(request.payload.get("preview_length", 0) or 0),
                metadata=request.metadata,
            )
        )
        result_payload = self._serialize_file_read_result(read_result)
        artifact = self._capture_artifact(request, workspace, result_payload, "file-read", "file_read")
        audit = self._log_audit_event(request, operation, str(read_result.path), read_result.success, result_payload, artifact)
        return self._response(request, operation, workspace, "file_read", read_result.success, result_payload, artifact, audit)

    def _handle_filesystem_operation(self, request: RequestEnvelope, workspace: WorkspaceContext, operation: str) -> ResponseEnvelope:
        operation_type = self._parse_filesystem_operation_type(request.payload.get("operation_type"))
        if operation_type is None:
            return self._failure(request, operation, "invalid_operation", "Unsupported filesystem operation type.", workspace=workspace)
        fs_operation = FileSystemOperation(
            operation_id=request.request_id,
            operation_type=operation_type,
            path=Path(str(request.payload.get("path", ""))),
            content=str(request.payload.get("content", "")),
            metadata=request.metadata,
        )
        op_result = self._filesystem_operator.execute(fs_operation)
        result_payload = self._serialize_filesystem_operation_result(op_result)
        artifact = self._capture_artifact(request, workspace, result_payload, "filesystem-operation", "filesystem_operation")
        audit = self._log_audit_event(request, operation, str(op_result.path), op_result.success, result_payload, artifact)
        return self._response(request, operation, workspace, "filesystem_operation", op_result.success, result_payload, artifact, audit)

    def _handle_filesystem_mutation(self, request: RequestEnvelope, workspace: WorkspaceContext, operation: str) -> ResponseEnvelope:
        mutation_type = self._parse_mutation_type(request.payload.get("mutation_type"))
        if mutation_type is None:
            return self._failure(request, operation, "invalid_operation", "Unsupported mutation type.", workspace=workspace)
        mutation_result = self._file_mutation_service.apply(
            FileMutationRequest(
                request_id=request.request_id,
                workspace=workspace,
                path=request.payload.get("path", ""),
                mutation_type=mutation_type,
                content=str(request.payload.get("content", "")),
                expected_content=str(request.payload.get("expected_content", "")),
                metadata=request.metadata,
            )
        )
        result_payload = self._serialize_file_mutation_result(mutation_result)
        artifact = self._capture_artifact(request, workspace, result_payload, "filesystem-mutation", "filesystem_mutation")
        audit = self._log_audit_event(request, operation, str(mutation_result.path), mutation_result.success, result_payload, artifact)
        return self._response(request, operation, workspace, "filesystem_mutation", mutation_result.success, result_payload, artifact, audit)

    def _handle_diff(self, request: RequestEnvelope, workspace: WorkspaceContext, operation: str) -> ResponseEnvelope:
        if self._diff_service is None:
            return self._failure(request, operation, "service_unavailable", "Diff service is unavailable.", workspace=workspace)
        diff_result = self._diff_service.generate_diff(
            DiffRequest(
                request_id=request.request_id,
                path=Path(str(request.payload.get("path", ""))),
                before=str(request.payload.get("before", "")),
                after=str(request.payload.get("after", "")),
                metadata=request.metadata,
            )
        )
        result_payload = self._serialize_diff_result(diff_result)
        artifact = self._capture_artifact(request, workspace, result_payload, "diff", "diff")
        audit = self._log_audit_event(request, operation, str(diff_result.path), diff_result.has_changes or diff_result.diff_text == "", result_payload, artifact)
        return self._response(request, operation, workspace, "diff", True, result_payload, artifact, audit)

    def _handle_command(self, request: RequestEnvelope, workspace: WorkspaceContext, operation: str) -> ResponseEnvelope:
        if self._command_runner is None:
            return self._failure(request, operation, "service_unavailable", "Command runner is unavailable.", workspace=workspace)
        arguments = request.payload.get("arguments", ())
        if isinstance(arguments, list):
            arguments = tuple(str(argument) for argument in arguments)
        elif not isinstance(arguments, tuple):
            arguments = ()
        command_result = self._command_runner.run(
            CommandRequest(
                request_id=request.request_id,
                workspace=workspace,
                command=str(request.payload.get("command", "")),
                arguments=arguments,
                working_directory=request.payload.get("working_directory"),
                metadata=request.metadata,
            )
        )
        result_payload = self._serialize_command_result(command_result)
        artifact = self._capture_artifact(request, workspace, result_payload, "command", "command")
        success = command_result.allowed and command_result.result is not None and command_result.result.exit_code == 0
        audit = self._log_audit_event(request, operation, str(command_result.path), success, result_payload, artifact)
        return self._response(request, operation, workspace, "command", success, result_payload, artifact, audit)

    def _handle_artifact_registry(self, request: RequestEnvelope, workspace: WorkspaceContext, operation: str) -> ResponseEnvelope:
        if self._artifact_registry is None:
            return self._failure(request, operation, "service_unavailable", "Artifact registry is unavailable.", workspace=workspace)

        if operation == ToolAdapterOperation.ARTIFACT_REGISTER:
            registry_result = self._artifact_registry.register(self._artifact_request(request, workspace))
        elif operation == ToolAdapterOperation.ARTIFACT_SUPERSEDE:
            registry_result = self._artifact_registry.supersede(str(request.payload.get("manifest_id", "")), self._artifact_request(request, workspace))
        elif operation == ToolAdapterOperation.ARTIFACT_ARCHIVE:
            registry_result = self._artifact_registry.archive(str(request.payload.get("manifest_id", "")), request.request_id)
        elif operation == ToolAdapterOperation.ARTIFACT_GET:
            try:
                manifest = self._artifact_registry.get(str(request.payload.get("manifest_id", "")))
            except Exception as error:
                return self._failure(request, operation, "artifact_lookup_failed", str(error), workspace=workspace)
            registry_result = ArtifactRegistryResult(request_id=request.request_id, manifest=manifest, success=True)
        elif operation == ToolAdapterOperation.ARTIFACT_LIST:
            registry_result = ArtifactRegistryResult(
                request_id=request.request_id,
                manifest=None,
                success=True,
                metadata={"manifests": [self._serialize_manifest(item) for item in self._artifact_registry.list()]},
            )
        else:
            registry_result = ArtifactRegistryResult(
                request_id=request.request_id,
                manifest=None,
                success=True,
                metadata={"history": [self._serialize_manifest(item) for item in self._artifact_registry.history(str(request.payload.get("artifact_id", "")))]},
            )

        payload = {
            "operation": operation,
            "service": "artifact_registry",
            "workspace_id": workspace.workspace_id,
            "success": registry_result.success,
            "status": "ok" if registry_result.success else "error",
            "result": {
                "manifest": self._serialize_manifest(registry_result.manifest) if registry_result.manifest else None,
                "error_code": str(registry_result.error_code) if registry_result.error_code else "",
                "error_message": registry_result.error_message,
                "metadata": registry_result.metadata,
            },
            "artifact": None,
            "audit": None,
        }
        return ResponseEnvelope(request_id=request.request_id, success=registry_result.success, status=payload["status"], payload=payload, metadata=request.metadata)

    def _handle_audit_logger(self, request: RequestEnvelope, workspace: WorkspaceContext, operation: str) -> ResponseEnvelope:
        if self._audit_logger is None:
            return self._failure(request, operation, "service_unavailable", "Audit logger is unavailable.", workspace=workspace)

        if operation == ToolAdapterOperation.AUDIT_APPEND:
            audit_result = self._audit_logger.append(
                AuditLoggerRequest(
                    request_id=request.request_id,
                    action=str(request.payload.get("action", "")),
                    subject=str(request.payload.get("subject", "")),
                    status=str(request.payload.get("status", "")),
                    details=dict(request.payload.get("details", {})),
                    metadata=request.metadata,
                )
            )
        elif operation == ToolAdapterOperation.AUDIT_GET:
            try:
                record = self._audit_logger.get(str(request.payload.get("event_id", "")))
            except Exception as error:
                return self._failure(request, operation, "audit_lookup_failed", str(error), workspace=workspace)
            audit_result = AuditLoggerResult(request_id=request.request_id, record=record, success=True)
        elif operation == ToolAdapterOperation.AUDIT_LIST:
            audit_result = AuditLoggerResult(
                request_id=request.request_id,
                record=None,
                success=True,
                metadata={"records": [self._serialize_audit_record(item) for item in self._audit_logger.list()]},
            )
        else:
            audit_result = AuditLoggerResult(
                request_id=request.request_id,
                record=None,
                success=True,
                metadata={"history": [self._serialize_audit_record(item) for item in self._audit_logger.history(str(request.payload.get("request_id", "")))]},
            )

        payload = {
            "operation": operation,
            "service": "audit_logger",
            "workspace_id": workspace.workspace_id,
            "success": audit_result.success,
            "status": "ok" if audit_result.success else "error",
            "result": {
                "record": self._serialize_audit_record(audit_result.record) if audit_result.record else None,
                "error_code": str(audit_result.error_code) if audit_result.error_code else "",
                "error_message": audit_result.error_message,
                "metadata": audit_result.metadata,
            },
            "artifact": None,
            "audit": None,
        }
        return ResponseEnvelope(request_id=request.request_id, success=audit_result.success, status=payload["status"], payload=payload, metadata=request.metadata)

    def _response(
        self,
        request: RequestEnvelope,
        operation: str,
        workspace: WorkspaceContext,
        service_name: str,
        success: bool,
        result_payload: dict[str, Any],
        artifact: dict[str, Any] | None,
        audit: dict[str, Any] | None,
    ) -> ResponseEnvelope:
        payload = {
            "operation": operation,
            "service": service_name,
            "workspace_id": workspace.workspace_id,
            "success": success,
            "status": "ok" if success else "error",
            "result": result_payload,
            "artifact": artifact,
            "audit": audit,
        }
        return ResponseEnvelope(request_id=request.request_id, success=success, status=payload["status"], payload=payload, metadata=request.metadata)

    def _failure(
        self,
        request: RequestEnvelope,
        operation: str,
        code: str,
        message: str,
        *,
        workspace: WorkspaceContext | None = None,
    ) -> ResponseEnvelope:
        payload = {
            "operation": operation,
            "service": "adapter",
            "workspace_id": (workspace or request.workspace).workspace_id,
            "success": False,
            "status": "error",
            "result": None,
            "artifact": None,
            "audit": None,
            "error_code": code,
            "error_message": message,
        }
        return ResponseEnvelope(request_id=request.request_id, success=False, status="error", payload=payload, metadata=request.metadata)

    def _normalize_operation(self, operation: str) -> str:
        normalized = operation.strip().lower().replace(" ", ".")
        alias_map = {
            "read": ToolAdapterOperation.FILE_READ,
            "file.read": ToolAdapterOperation.FILE_READ,
            "filesystem.operation": ToolAdapterOperation.FILESYSTEM_OPERATION,
            "filesystem.ops": ToolAdapterOperation.FILESYSTEM_OPERATION,
            "fs.operation": ToolAdapterOperation.FILESYSTEM_OPERATION,
            "filesystem.mutation": ToolAdapterOperation.FILESYSTEM_MUTATION,
            "mutation": ToolAdapterOperation.FILESYSTEM_MUTATION,
            "file.mutation": ToolAdapterOperation.FILESYSTEM_MUTATION,
            "diff": ToolAdapterOperation.DIFF_GENERATE,
            "diff.generate": ToolAdapterOperation.DIFF_GENERATE,
            "command": ToolAdapterOperation.COMMAND_RUN,
            "command.run": ToolAdapterOperation.COMMAND_RUN,
            "artifact.register": ToolAdapterOperation.ARTIFACT_REGISTER,
            "artifact.supersede": ToolAdapterOperation.ARTIFACT_SUPERSEDE,
            "artifact.archive": ToolAdapterOperation.ARTIFACT_ARCHIVE,
            "artifact.get": ToolAdapterOperation.ARTIFACT_GET,
            "artifact.list": ToolAdapterOperation.ARTIFACT_LIST,
            "artifact.history": ToolAdapterOperation.ARTIFACT_HISTORY,
            "audit.append": ToolAdapterOperation.AUDIT_APPEND,
            "audit.get": ToolAdapterOperation.AUDIT_GET,
            "audit.list": ToolAdapterOperation.AUDIT_LIST,
            "audit.history": ToolAdapterOperation.AUDIT_HISTORY,
        }
        return alias_map.get(normalized, normalized)

    def _parse_filesystem_operation_type(self, value: Any) -> FileSystemOperationType | None:
        try:
            return FileSystemOperationType(str(value).strip().lower())
        except Exception:
            return None

    def _parse_mutation_type(self, value: Any) -> FileMutationType | None:
        try:
            return FileMutationType(str(value).strip().lower())
        except Exception:
            return None

    def _artifact_request(self, request: RequestEnvelope, workspace: WorkspaceContext) -> ArtifactRegistryRequest:
        provenance = request.payload.get("provenance")
        if isinstance(provenance, ArtifactProvenance):
            artifact_provenance = provenance
        else:
            timestamp = request.metadata.get("artifact_timestamp")
            artifact_provenance = ArtifactProvenance(
                request_id=request.request_id,
                operation=str(request.payload.get("provenance_operation", request.operation)),
                source=str(request.payload.get("provenance_source", "local_tooling.adapter")),
                timestamp=timestamp if isinstance(timestamp, datetime) else datetime.fromtimestamp(0, UTC),
                metadata=dict(request.payload.get("provenance_metadata", {})),
            )
        return ArtifactRegistryRequest(
            request_id=request.request_id,
            artifact_id=str(request.payload.get("artifact_id", request.request_id)),
            name=str(request.payload.get("name", request.operation)),
            location=Path(str(request.payload.get("location", workspace.root_path))),
            artifact_type=str(request.payload.get("artifact_type", request.operation)),
            content=str(request.payload.get("content", "")),
            provenance=artifact_provenance,
            metadata=request.metadata,
        )

    def _capture_artifact(
        self,
        request: RequestEnvelope,
        workspace: WorkspaceContext,
        result_payload: dict[str, Any],
        artifact_name: str,
        artifact_type: str,
    ) -> dict[str, Any] | None:
        if self._artifact_registry is None:
            return None
        artifact_request = ArtifactRegistryRequest(
            request_id=request.request_id,
            artifact_id=str(request.payload.get("artifact_id", request.request_id)),
            name=str(request.payload.get("artifact_name", artifact_name)),
            location=Path(str(request.payload.get("artifact_location", workspace.root_path / artifact_name))),
            artifact_type=str(request.payload.get("artifact_type", artifact_type)),
            content=json.dumps(result_payload, sort_keys=True, default=str),
            provenance=ArtifactProvenance(
                request_id=request.request_id,
                operation=f"tool.capture.{request.operation}",
                source="local_tooling.adapter",
                timestamp=datetime.fromtimestamp(0, UTC),
            ),
            metadata=request.metadata,
        )
        registry_result = self._artifact_registry.register(artifact_request)
        if not registry_result.success or registry_result.manifest is None:
            return {
                "success": False,
                "error_code": str(registry_result.error_code) if registry_result.error_code else "",
                "error_message": registry_result.error_message,
            }
        return self._serialize_manifest(registry_result.manifest)

    def _log_audit_event(
        self,
        request: RequestEnvelope,
        operation: str,
        subject: str,
        success: bool,
        result_payload: dict[str, Any],
        artifact: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if self._audit_logger is None:
            return None
        audit_result = self._audit_logger.append(
            AuditLoggerRequest(
                request_id=request.request_id,
                action=f"tool.{operation}",
                subject=subject,
                status="ok" if success else "error",
                details={
                    "operation": operation,
                    "result": result_payload,
                    **({"artifact": artifact} if artifact is not None else {}),
                },
                metadata=request.metadata,
            )
        )
        if not audit_result.success or audit_result.record is None:
            return {
                "success": False,
                "error_code": str(audit_result.error_code) if audit_result.error_code else "",
                "error_message": audit_result.error_message,
            }
        return self._serialize_audit_record(audit_result.record)

    def _serialize_manifest(self, manifest: ArtifactManifest | None) -> dict[str, Any] | None:
        if manifest is None:
            return None
        return {
            "manifest_id": manifest.manifest_id,
            "artifact_id": manifest.artifact_id,
            "name": manifest.name,
            "location": manifest.location.as_posix(),
            "artifact_type": manifest.artifact_type,
            "content_checksum": manifest.content_checksum,
            "checksum_algorithm": manifest.checksum_algorithm,
            "provenance": {
                "request_id": manifest.provenance.request_id,
                "operation": manifest.provenance.operation,
                "source": manifest.provenance.source,
                "timestamp": manifest.provenance.timestamp.isoformat(),
                "metadata": manifest.provenance.metadata,
            },
            "created_at": manifest.created_at.isoformat(),
            "supersedes_manifest_id": manifest.supersedes_manifest_id,
            "archived": manifest.archived,
            "metadata": manifest.metadata,
        }

    def _serialize_audit_record(self, record: AuditRecord | None) -> dict[str, Any] | None:
        if record is None:
            return None
        return {
            "event_id": record.event_id,
            "sequence_number": record.sequence_number,
            "request_id": record.request_id,
            "timestamp": record.timestamp.isoformat(),
            "action": record.action,
            "subject": record.subject,
            "status": record.status,
            "details": record.details,
            "metadata": record.metadata,
        }

    def _serialize_file_read_result(self, result: FileReadResult) -> dict[str, Any]:
        return {
            "request_id": result.request_id,
            "path": result.path.as_posix(),
            "success": result.success,
            "content": result.content,
            "preview": result.preview,
            "digest": result.digest,
            "error_code": str(result.error_code) if result.error_code else "",
            "error_message": result.error_message,
            "metadata": result.metadata,
        }

    def _serialize_filesystem_operation_result(self, result: FileSystemOperationResult) -> dict[str, Any]:
        return {
            "request_id": getattr(result, "request_id", getattr(result, "operation_id", "")),
            "path": result.path.as_posix(),
            "exists": result.exists,
            "content": result.content,
            "metadata": result.metadata,
        }

    def _serialize_file_mutation_result(self, result: FileMutationResult) -> dict[str, Any]:
        return {
            "request_id": result.request_id,
            "path": result.path.as_posix(),
            "mutation_type": result.mutation_type.value,
            "success": result.success,
            "content": result.content,
            "previous_content": result.previous_content,
            "preflight": None
            if result.preflight is None
            else {
                "request_id": result.preflight.request_id,
                "path": result.preflight.path.as_posix(),
                "allowed": result.preflight.allowed,
                "error_code": result.preflight.error_code,
                "error_message": result.preflight.error_message,
                "metadata": result.preflight.metadata,
            },
            "metadata": result.metadata,
        }

    def _serialize_diff_result(self, result: DiffResult) -> dict[str, Any]:
        return {
            "request_id": result.request_id,
            "path": result.path.as_posix(),
            "has_changes": result.has_changes,
            "diff_text": result.diff_text,
            "metadata": result.metadata,
        }

    def _serialize_command_result(self, result: CommandRunResult) -> dict[str, Any]:
        payload = {
            "request_id": result.request_id,
            "path": result.path.as_posix(),
            "allowed": result.allowed,
            "error_code": str(result.error_code) if result.error_code else "",
            "error_message": result.error_message,
            "metadata": result.metadata,
        }
        if result.result is not None:
            payload["result"] = {
                "command": result.result.command,
                "exit_code": result.result.exit_code,
                "stdout": result.result.stdout,
                "stderr": result.result.stderr,
                "metadata": result.result.metadata,
            }
        return payload
